from datetime import datetime
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, DiagnosisArtifact, DiagnosisRecord, TrustHistory, User
from app.schemas import ExplanationBundle, PredictionRequest, PredictionResponse
from app.services.adversarial import calculate_aecs, evaluate_attacks
from app.services.blockchain import anchor_diagnosis, build_diagnosis_anchor_payload, hash_payload
from app.services.catalog import get_disease
from app.services.reports import build_pdf_report
from app.services.storage import store_object
from app.services.trust import calculate_dtei
from app.services.xai import build_explanations

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
                        f"{item['label']} must be one of: {', '.join(map(str, choices))}."
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
        image = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise PredictionInputError("The uploaded file is not a readable image.")
        features = cv2.resize(image, (64, 64)).astype(np.float32).reshape(1, -1) / 255.0
        probabilities = model.predict_proba(features)[0]
        best_index = int(np.argmax(probabilities))
        model_class = int(model.classes_[best_index])
        confidence = float(probabilities[best_index])
    except PredictionInputError:
        raise
    except Exception as exc:
        raise PredictionInputError(f"The {disease.name} image model could not process this image: {exc}") from exc
    return model_class, float(np.clip(confidence, 0.0, 1.0)), {
        "image_width": int(image.shape[1]),
        "image_height": int(image.shape[0]),
    }


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
            "selected_model",
            "deployment_status",
            "test_metrics",
            "data_quality",
            "limitations",
        )
        if key in metadata
    }
    if "test_metrics" not in safe:
        safe["test_metrics"] = load_metrics(disease_key)
    if "deployment_status" not in safe:
        safe["deployment_status"] = "baseline_only" if metadata.get("modality") == "image" else "unknown"
    return safe


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
    metrics = load_metrics(disease.key)
    explanation = build_explanations(disease.key, features, confidence)
    adversarial = evaluate_attacks(confidence)
    aecs = calculate_aecs(confidence)
    trust_score, components = calculate_dtei(
        confidence=confidence,
        explanation_stability=adversarial["explanation_stability"],
        robustness_score=adversarial["robustness_score"],
        blockchain_integrity=0.5,
    )
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
    )
    db.add(record)
    db.flush()
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

    report_content = build_pdf_report(record)
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
        created_at=record.created_at or datetime.utcnow(),
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
