from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.rbac import Role
from app.db.models import AuditEvent, DiagnosisArtifact, DiagnosisRecord, TrustHistory, User
from app.schemas import ExplanationBundle, PredictionRequest, PredictionResponse
from app.services.adversarial import calculate_aecs, evaluate_attacks
from app.services.blockchain import anchor_diagnosis, build_diagnosis_anchor_payload, hash_payload
from app.services.catalog import get_disease
from app.services.notifications import is_high_risk, notify_doctors_for_diagnosis
from app.services.reports import build_pdf_report
from app.services.storage import store_object
from app.services.trust import DTEI_WEIGHTS, calculate_dtei, dtei_status
from app.services.xai import build_explanations

try:
    from skimage.feature import hog
except ImportError:  # pragma: no cover - optional image feature dependency.
    hog = None  # type: ignore

# Load trained models from artifacts
MODELS_DIR = Path(__file__).parent.parent / "ai" / "artifacts"
_MODEL_CACHE: dict[str, Any] = {}
MODEL_CLASS_LABELS: dict[str, list[str]] = {
    "heart": ["low_risk", "high_risk"],
    "diabetes": ["negative", "positive"],
    # These follow the exact target encoding used by the current trained artifacts.
    "asthma": ["risk", "controlled"],
    "liver": ["disease", "normal"],
    "parkinson": ["healthy", "parkinson"],
}


class PredictionInputError(ValueError):
    """A user-correctable prediction input problem."""


def load_model(disease_key: str) -> Any:
    """Load a trained model from artifacts."""
    if disease_key in _MODEL_CACHE:
        return _MODEL_CACHE[disease_key]

    metadata = load_model_metadata(disease_key)
    keras_path = MODELS_DIR / f"{disease_key}_model.keras"
    if metadata.get("modality") == "image" and keras_path.exists():
        try:
            import tensorflow as tf

            model = tf.keras.models.load_model(keras_path)
            _MODEL_CACHE[disease_key] = model
            return model
        except Exception as e:
            print(f"Error loading Keras model {disease_key}: {e}")

    import pickle
    model_path = MODELS_DIR / f"{disease_key}_model.pkl"
    if model_path.exists():
        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)
            _MODEL_CACHE[disease_key] = model
            return model
        except Exception as e:
            print(f"Error loading model {disease_key}: {e}")
    return None


def load_metrics(disease_key: str) -> dict[str, float]:
    """Load metrics from JSON artifacts."""
    # Try CSV metrics first
    metrics_path = MODELS_DIR / f"{disease_key}_csv_metrics.json"
    if not metrics_path.exists():
        # Try image metrics
        metrics_path = MODELS_DIR / f"{disease_key}_images_metrics.json"
    
    if metrics_path.exists():
        try:
            with open(metrics_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metrics {disease_key}: {e}")
    
    return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1_score": 0.0, "auc": 0.0}


@lru_cache(maxsize=32)
def get_feature_schema(disease_key: str) -> list[dict[str, Any]]:
    """Return the exact ordered inputs expected by a trained tabular model."""
    metadata_path = MODELS_DIR / f"{disease_key}_model_metadata.json"
    if metadata_path.exists():
        try:
            schema = json.loads(metadata_path.read_text(encoding="utf-8")).get("input_schema")
            if isinstance(schema, list) and schema:
                return schema
        except (OSError, ValueError):
            pass

    model = load_model(disease_key)
    names = [str(name) for name in getattr(model, "feature_names_in_", [])] if model is not None else []
    if not names:
        return []

    project_root = Path(__file__).resolve().parents[3]
    split_path = project_root / "data" / "train" / disease_key / "data.csv"
    sample = pd.DataFrame()
    if split_path.exists():
        try:
            sample = pd.read_csv(split_path, usecols=lambda column: column in names, nrows=5000)
        except Exception:
            sample = pd.DataFrame()

    schema: list[dict[str, Any]] = []
    for name in names:
        series = pd.to_numeric(sample[name], errors="coerce").dropna() if name in sample else pd.Series(dtype=float)
        unique_values = set(float(value) for value in series.unique()[:10])
        is_boolean = bool(unique_values) and unique_values.issubset({0.0, 1.0})
        minimum = float(series.min()) if not series.empty else None
        maximum = float(series.max()) if not series.empty else None
        default = float(series.median()) if not series.empty else (0.0 if is_boolean else None)
        schema.append(
            {
                "name": name,
                "label": name.replace("_", " ").replace(":", " ").strip(),
                "input_type": "boolean" if is_boolean else "number",
                "required": True,
                "minimum": minimum,
                "maximum": maximum,
                "default": default,
            }
        )
    return schema


def _tabular_prediction(features: dict[str, Any], disease_key: str) -> tuple[int, float, dict[str, Any]]:
    model = load_model(disease_key)
    if model is None:
        raise PredictionInputError(f"No trained tabular model is available for {disease_key}.")

    schema = get_feature_schema(disease_key)
    required = [item["name"] for item in schema]
    if not required:
        raise PredictionInputError(f"The trained model for {disease_key} does not expose its feature schema.")
    missing = [name for name in required if name not in features or features[name] in ("", None)]
    unexpected = [name for name in features if name not in required]
    if missing:
        raise PredictionInputError(f"Missing required features: {', '.join(missing)}")
    if unexpected:
        raise PredictionInputError(f"Unexpected features: {', '.join(unexpected)}")

    normalized: dict[str, Any] = {}
    for item in schema:
        name = item["name"]
        raw_value = features[name]
        if item["input_type"] == "category":
            choices = item.get("choices") or []
            if raw_value not in choices:
                # Form values arrive as strings; recover an exact numeric category when needed.
                matched = next((choice for choice in choices if str(choice) == str(raw_value)), None)
                if matched is None:
                    raise PredictionInputError(
                        f"{name} must be one of: {', '.join(map(str, choices))}."
                    )
                raw_value = matched
            normalized[name] = raw_value
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise PredictionInputError(f"{item['label']} must be a valid number.") from exc
        if not np.isfinite(value):
            raise PredictionInputError(f"{item['label']} must be a finite number.")
        if item["input_type"] == "boolean" and value not in {0.0, 1.0}:
            raise PredictionInputError(f"{item['label']} must be either 0 (No) or 1 (Yes).")
        if item["minimum"] is not None and value < item["minimum"]:
            raise PredictionInputError(f"{item['label']} must be at least {item['minimum']}.")
        if item["maximum"] is not None and value > item["maximum"]:
            raise PredictionInputError(f"{item['label']} must be at most {item['maximum']}.")
        normalized[name] = value

    try:
        probabilities = model.predict_proba(pd.DataFrame([normalized], columns=required))[0]
        threshold = 0.5
        metadata_path = MODELS_DIR / f"{disease_key}_model_metadata.json"
        if metadata_path.exists():
            threshold = float(
                json.loads(metadata_path.read_text(encoding="utf-8")).get("decision_threshold", 0.5)
            )
        best_index = (
            int(probabilities[1] >= threshold)
            if len(probabilities) == 2
            else int(np.argmax(probabilities))
        )
        model_class = int(model.classes_[best_index])
        confidence = float(probabilities[best_index])
    except Exception as exc:
        raise PredictionInputError(f"The {disease_key} model could not process these feature values: {exc}") from exc
    return model_class, float(np.clip(confidence, 0.0, 1.0)), normalized


def _image_prediction(
    image_bytes: bytes, disease_key: str, content_type: str
) -> tuple[int, float, dict[str, Any]]:
    disease = get_disease(disease_key)
    if disease.modality != "image":
        raise PredictionInputError(f"{disease.name} requires tabular clinical features, not an image.")
    if not image_bytes:
        raise PredictionInputError("Choose an image before running the diagnosis.")
    if len(image_bytes) > 10 * 1024 * 1024:
        raise PredictionInputError("The image must be 10 MB or smaller.")
    if content_type and content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise PredictionInputError("Upload a JPEG, PNG, or WebP medical image.")

    model = load_model(disease_key)
    if model is None:
        raise PredictionInputError(f"No trained image model is available for {disease.name}.")
    try:
        import cv2

        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if image is None:
            raise PredictionInputError("The uploaded file is not a readable image.")
        metadata = load_model_metadata(disease_key)
        if metadata.get("feature_extractor") == "opencv_hog_histogram_v1" and hasattr(model, "predict_proba"):
            image_size = metadata.get("image_size", [96, 96])
            features = _opencv_hog_histogram_features(
                image, (int(image_size[0]), int(image_size[1]))
            ).reshape(1, -1)
            probabilities = model.predict_proba(features)[0]
            best_index = int(np.argmax(probabilities))
            model_class = int(getattr(model, "classes_", np.arange(len(probabilities)))[best_index])
            confidence = float(probabilities[best_index])
        elif hasattr(model, "predict_proba"):
            grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            features = cv2.resize(grayscale, (64, 64)).astype(np.float32).reshape(1, -1) / 255.0
            probabilities = model.predict_proba(features)[0]
            best_index = int(np.argmax(probabilities))
            model_class = int(model.classes_[best_index])
            confidence = float(probabilities[best_index])
        else:
            image_size = metadata.get("image_size", [224, 224])
            resized = cv2.resize(image, (int(image_size[1]), int(image_size[0])))
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            probabilities = np.asarray(model.predict(np.expand_dims(rgb, axis=0), verbose=0))[0]
            if probabilities.ndim == 0 or probabilities.shape[0] == 1:
                positive = float(np.ravel(probabilities)[0])
                probabilities = np.asarray([1.0 - positive, positive])
            best_index = int(np.argmax(probabilities))
            model_class = best_index
            confidence = float(probabilities[best_index])
    except PredictionInputError:
        raise
    except Exception as exc:
        raise PredictionInputError(f"The {disease.name} image model could not process this image: {exc}") from exc
    return model_class, float(np.clip(confidence, 0.0, 1.0)), {
        "image_width": int(image.shape[1]),
        "image_height": int(image.shape[0]),
    }


def _opencv_hog_histogram_features(image: np.ndarray, image_size: tuple[int, int]) -> np.ndarray:
    import cv2

    resized = cv2.resize(image, image_size)
    denoised = cv2.GaussianBlur(resized, (3, 3), 0)
    gray = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    gray_float = gray.astype(np.float32) / 255.0
    thumbnail = cv2.resize(gray_float, (32, 32)).reshape(-1)
    hsv = cv2.cvtColor(denoised, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 4, 4], [0, 180, 0, 256, 0, 256])
    hist = cv2.normalize(hist, hist).flatten().astype(np.float32)
    if hog is not None:
        hog_features = hog(
            gray_float,
            orientations=9,
            pixels_per_cell=(12, 12),
            cells_per_block=(2, 2),
            block_norm="L2-Hys",
            feature_vector=True,
        ).astype(np.float32)
    else:
        hog_features = np.array([], dtype=np.float32)
    stats = np.array(
        [
            float(gray_float.mean()),
            float(gray_float.std()),
            float(np.percentile(gray_float, 25)),
            float(np.percentile(gray_float, 75)),
        ],
        dtype=np.float32,
    )
    return np.concatenate([thumbnail.astype(np.float32), hist, hog_features, stats])


def _class_labels(disease_key: str, fallback: list[str]) -> list[str]:
    metadata_path = MODELS_DIR / f"{disease_key}_model_metadata.json"
    if metadata_path.exists():
        try:
            labels = json.loads(metadata_path.read_text(encoding="utf-8")).get("class_labels")
            if isinstance(labels, list) and labels:
                return [str(label) for label in labels]
        except (OSError, ValueError):
            pass
    return MODEL_CLASS_LABELS.get(disease_key, fallback)


def load_model_metadata(disease_key: str) -> dict[str, Any]:
    """Return safe model-card fields for the UI and API."""
    metadata_path = MODELS_DIR / f"{disease_key}_model_metadata.json"
    if not metadata_path.exists():
        return {}
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    safe = {
        key: metadata[key]
        for key in (
            "artifact_version",
            "trained_at",
            "modality",
            "selected_model",
            "deployment_status",
            "test_metrics",
            "data_quality",
            "image_size",
            "feature_extractor",
            "adversarial_robustness",
            "aecs",
            "dtei",
            "blockchain_audit",
            "explainability",
            "feature_importance",
            "report_artifacts",
            "validation_comparison",
            "limitations",
        )
        if key in metadata
    }
    if "test_metrics" not in safe:
        safe["test_metrics"] = load_metrics(disease_key)
    if "deployment_status" not in safe:
        safe["deployment_status"] = "baseline_only" if metadata.get("modality") == "image" else "unknown"
    return safe


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _merge_metadata_explanations(
    disease_key: str,
    features: dict[str, Any],
    confidence: float,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    explanation = build_explanations(disease_key, features, confidence)
    trained_explanation = metadata.get("explainability")
    if not isinstance(trained_explanation, dict):
        return explanation

    for key in ("shap", "lime", "integrated_gradients"):
        value = trained_explanation.get(key)
        if isinstance(value, dict):
            explanation[key] = value

    grad_cam = trained_explanation.get("grad_cam") or trained_explanation.get("gradcam")
    if isinstance(grad_cam, dict):
        explanation["gradcam"] = grad_cam

    feature_importance = trained_explanation.get("feature_importance") or metadata.get("feature_importance")
    if isinstance(feature_importance, list) and feature_importance:
        explanation["shap"] = {
            **explanation.get("shap", {}),
            "feature_importance": feature_importance,
        }
    return explanation


def _runtime_trust_bundle(
    disease_key: str,
    features: dict[str, Any],
    confidence: float,
) -> tuple[dict[str, Any], dict[str, Any], float, float, Any]:
    metadata = load_model_metadata(disease_key)
    explanation = _merge_metadata_explanations(disease_key, features, confidence, metadata)
    trained_adversarial = metadata.get("adversarial_robustness")
    adversarial = trained_adversarial if isinstance(trained_adversarial, dict) else evaluate_attacks(confidence)
    aecs = _as_float(metadata.get("aecs"), calculate_aecs(confidence))
    explanation_stability = _as_float(adversarial.get("explanation_stability"), aecs)
    robustness_score = _as_float(adversarial.get("robustness_score"), 0.0)
    compliance = 1.0 if metadata.get("deployment_status") == "ready_for_research" else 0.5
    trust_score, components = calculate_dtei(
        confidence=confidence,
        explanation_stability=explanation_stability,
        robustness_score=robustness_score,
        blockchain_integrity=1.0,
        compliance=compliance,
    )
    return explanation, adversarial, aecs, trust_score, components


def _validate_supporting_pdf(content: bytes | None, content_type: str | None) -> None:
    if content is None:
        return
    if not content or len(content) > 15 * 1024 * 1024:
        raise PredictionInputError("The supporting PDF must be between 1 byte and 15 MB.")
    if content_type and content_type != "application/pdf":
        raise PredictionInputError("The supporting document must be a PDF.")
    if not content.startswith(b"%PDF-"):
        raise PredictionInputError("The supporting document is not a valid PDF file.")


def _persist_artifact(
    db: Session,
    record: DiagnosisRecord,
    *,
    kind: str,
    filename: str,
    content_type: str,
    content: bytes,
) -> DiagnosisArtifact:
    safe_filename = Path(filename).name or f"{kind}.bin"
    suffix = Path(safe_filename).suffix.lower()
    object_name = f"diagnoses/{record.id}/{kind}-{uuid4().hex}{suffix}"
    stored = store_object(object_name, content, content_type)
    artifact = DiagnosisArtifact(
        diagnosis_id=record.id,
        kind=kind,
        object_path=stored.object_path,
        original_filename=safe_filename,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
    )
    db.add(artifact)
    record.artifacts.append(artifact)
    return artifact


def _save_diagnosis(
    db: Session,
    *,
    disease_key: str,
    model_class: int,
    confidence: float,
    features: dict[str, Any],
    patient_name: str,
    patient_email: str,
    patient_id: str | None,
    doctor_notes: str,
    actor: User,
    input_modality: str,
    input_artifacts: list[dict[str, Any]] | None = None,
) -> PredictionResponse:
    disease = get_disease(disease_key)
    if len(patient_name.strip()) < 2:
        raise PredictionInputError("Enter the patient's full name.")
    labels = _class_labels(disease.key, disease.labels)
    prediction = labels[model_class] if 0 <= model_class < len(labels) else str(model_class)
    confidence = round(confidence, 3)
    if actor.role == Role.PATIENT.value:
        patient_id = actor.id
        patient_email = actor.email
    metrics = load_metrics(disease.key)
    explanation, adversarial, aecs, trust_score, components = _runtime_trust_bundle(
        disease.key,
        features,
        confidence,
    )
    metrics = {
        **metrics,
        "dtei": {
            "formula": "DTEI = alpha*F + beta*I + gamma*R + delta*B + lambda*C",
            "weights": DTEI_WEIGHTS,
            "components": components.as_dict(),
            "score": trust_score,
            "status": dtei_status(trust_score),
            "normalization": "All components are normalized to 0-1 before applying weights.",
        },
    }
    record = DiagnosisRecord(
        patient_id=patient_id,
        patient_name=patient_name.strip(),
        patient_email=patient_email.strip().lower(),
        doctor_id=actor.id,
        disease_key=disease.key,
        prediction=prediction,
        confidence=confidence,
        input_modality=input_modality,
        input_features=features,
        metrics=metrics,
        explanation=explanation,
        trust_score=trust_score,
        aecs=aecs,
        blockchain_hash="",
        doctor_notes=doctor_notes,
        review_status="pending",
        priority="urgent" if confidence >= 0.85 else "routine",
    )
    db.add(record)
    db.flush()
    if is_high_risk(record):
        record.priority = "urgent"
    notify_doctors_for_diagnosis(db, record)
    for artifact in input_artifacts or []:
        _persist_artifact(db, record, **artifact)
    db.flush()
    record.blockchain_hash = hash_payload(build_diagnosis_anchor_payload(record, actor))
    db.add(
        TrustHistory(
            diagnosis_id=record.id,
            disease_key=disease.key,
            fidelity=components.fidelity,
            interpretability=components.interpretability,
            robustness=components.robustness,
            blockchain_integrity=components.blockchain_integrity,
            compliance=components.compliance,
            dtei=trust_score,
        )
    )
    audit_event = AuditEvent(
        actor_id=actor.id,
        action="diagnosis.created",
        resource_type="diagnosis",
        resource_id=record.id,
        payload_hash=hash_payload({"record_id": record.id, "blockchain_hash": record.blockchain_hash}),
        metadata_json={
            "disease_key": disease.key,
            "trust_score": trust_score,
            "blockchain": {"status": "pending"},
        },
    )
    db.add(audit_event)
    # Persist the clinical record before making external blockchain calls.
    db.commit()
    db.refresh(record)

    anchor_result = anchor_diagnosis(record, actor)
    record.blockchain_status = anchor_result
    audit_event.metadata_json = {
        **audit_event.metadata_json,
        "blockchain": anchor_result,
    }
    db.commit()
    db.refresh(record)

    patient_user = None
    if record.patient_id:
        patient_user = db.query(User).filter(User.id == record.patient_id).first()
    if patient_user is None and record.patient_email:
        patient_user = db.query(User).filter(User.email == record.patient_email.lower()).first()
    report_content = build_pdf_report(record, patient_user)
    report_artifact = _persist_artifact(
        db,
        record,
        kind="generated_report",
        filename=f"trustmedai-{record.id}.pdf",
        content_type="application/pdf",
        content=report_content,
    )
    record.report_object_path = report_artifact.object_path
    db.commit()
    db.refresh(record)

    return PredictionResponse(
        diagnosis_id=record.id,
        disease_key=disease.key,
        prediction=prediction,
        confidence=confidence,
        metrics=metrics,
        explanation=ExplanationBundle(**explanation),
        adversarial=adversarial,
        aecs=aecs,
        trust_score=trust_score,
        dtei_components=components.as_dict(),
        blockchain_hash=record.blockchain_hash,
        blockchain_status=record.blockchain_status,
        input_modality=record.input_modality,
        artifacts=list(record.artifacts),
        ethereum_tx_hash=record.ethereum_tx_hash,
        fabric_tx_id=record.fabric_tx_id,
        created_at=record.created_at or datetime.now(timezone.utc),
    )


def run_diagnosis(
    db: Session,
    payload: PredictionRequest,
    actor: User,
    *,
    supporting_pdf_bytes: bytes | None = None,
    supporting_pdf_filename: str | None = None,
    supporting_pdf_content_type: str | None = None,
) -> PredictionResponse:
    disease = get_disease(payload.disease_key)
    if disease.modality == "image":
        raise PredictionInputError(f"{disease.name} requires an uploaded medical image.")
    _validate_supporting_pdf(supporting_pdf_bytes, supporting_pdf_content_type)
    model_class, confidence, normalized = _tabular_prediction(payload.features, disease.key)
    artifacts: list[dict[str, Any]] = []
    if supporting_pdf_bytes is not None:
        artifacts.append(
            {
                "kind": "supporting_pdf",
                "filename": supporting_pdf_filename or "supporting-report.pdf",
                "content_type": supporting_pdf_content_type or "application/pdf",
                "content": supporting_pdf_bytes,
            }
        )
    return _save_diagnosis(
        db,
        disease_key=disease.key,
        model_class=model_class,
        confidence=confidence,
        features=normalized,
        patient_name=payload.patient_name,
        patient_email=str(payload.patient_email),
        patient_id=payload.patient_id,
        doctor_notes=payload.doctor_notes,
        actor=actor,
        input_modality="tabular",
        input_artifacts=artifacts,
    )


def run_image_diagnosis(
    db: Session,
    *,
    disease_key: str,
    image_bytes: bytes,
    filename: str,
    content_type: str,
    patient_name: str,
    patient_email: str,
    patient_id: str | None,
    doctor_notes: str,
    actor: User,
    supporting_pdf_bytes: bytes | None = None,
    supporting_pdf_filename: str | None = None,
    supporting_pdf_content_type: str | None = None,
) -> PredictionResponse:
    _validate_supporting_pdf(supporting_pdf_bytes, supporting_pdf_content_type)
    model_class, confidence, image_details = _image_prediction(image_bytes, disease_key, content_type)
    artifacts = [
        {
            "kind": "input_image",
            "filename": filename,
            "content_type": content_type or "application/octet-stream",
            "content": image_bytes,
        }
    ]
    if supporting_pdf_bytes is not None:
        artifacts.append(
            {
                "kind": "supporting_pdf",
                "filename": supporting_pdf_filename or "supporting-report.pdf",
                "content_type": supporting_pdf_content_type or "application/pdf",
                "content": supporting_pdf_bytes,
            }
        )
    return _save_diagnosis(
        db,
        disease_key=disease_key,
        model_class=model_class,
        confidence=confidence,
        features={"image_filename": Path(filename).name, **image_details},
        patient_name=patient_name,
        patient_email=patient_email,
        patient_id=patient_id,
        doctor_notes=doctor_notes,
        actor=actor,
        input_modality="image",
        input_artifacts=artifacts,
    )


# Backwards-compatible alias expected by other modules
def make_prediction(db: Session, payload: PredictionRequest, actor: User) -> PredictionResponse:
    """Compatibility wrapper for older callers importing `make_prediction`.

    Delegates to `run_diagnosis` which implements the current prediction workflow.
    """
    return run_diagnosis(db=db, payload=payload, actor=actor)
