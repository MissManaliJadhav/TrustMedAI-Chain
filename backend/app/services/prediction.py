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
from app.services.notifications import (
    adversarial_security_thresholds,
    evaluate_adversarial_security_findings,
    is_high_risk,
    notify_adversarial_security_event,
    notify_doctors_for_diagnosis,
)
from app.services.patient_ids import ensure_user_public_patient_id, find_patient_user, public_patient_id_for_record
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


def _tabular_patient_attack(
    disease_key: str,
    features: dict[str, Any],
    *,
    prediction: str,
    confidence: float,
) -> dict[str, Any]:
    schema = get_feature_schema(disease_key)
    labels = _class_labels(disease_key, get_disease(disease_key).labels)
    perturbed = dict(features)
    affected: list[dict[str, Any]] = []
    for item in schema:
        if len(affected) >= 3:
            break
        if item.get("input_type") in {"boolean", "category"}:
            continue
        name = item["name"]
        original = float(features[name])
        minimum = item.get("minimum")
        maximum = item.get("maximum")
        if minimum is not None and maximum is not None and float(maximum) > float(minimum):
            delta = 0.05 * (float(maximum) - float(minimum))
        else:
            delta = max(abs(original) * 0.05, 0.05)
        attacked = original + delta
        if maximum is not None:
            attacked = min(attacked, float(maximum))
        if minimum is not None:
            attacked = max(attacked, float(minimum))
        if np.isclose(attacked, original):
            continue
        perturbed[name] = attacked
        difference = attacked - original
        affected.append(
            {
                "feature_name": name,
                "original_value": original,
                "adversarial_value": round(float(attacked), 6),
                "absolute_change": round(float(abs(difference)), 6),
                "signed_change": round(float(difference), 6),
                "relative_change": round(float(abs(difference) / max(abs(original), 1e-9)), 6),
                "perturbation_status": "Modified",
            }
        )

    if not affected:
        return {
            "modality": "tabular",
            "status": "Not Evaluated",
            "reason": "No mutable numeric features were available for deterministic feature perturbation.",
        }

    attacked_class, attacked_confidence, attacked_values = _tabular_prediction(perturbed, disease_key)
    attacked_prediction = labels[attacked_class] if 0 <= attacked_class < len(labels) else str(attacked_class)
    return {
        "modality": "tabular",
        "status": "Evaluated",
        "attack_type": "Feature Perturbation",
        "attack_parameters": {"feature_delta": "5 percent of feature range where available", "random_seed": 42},
        "affected_features_count": len(affected),
        "perturbation_rate": round(len(affected) / max(1, len(schema)), 4),
        "affected_features": affected,
        "original_values": features,
        "adversarial_values": attacked_values,
        "prediction_before_attack": prediction,
        "confidence_before_attack": confidence,
        "prediction_under_attack": attacked_prediction,
        "confidence_under_attack": round(attacked_confidence, 4),
        "prediction_changed": attacked_prediction != prediction,
    }


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


def _image_patient_attack(
    disease_key: str,
    image_bytes: bytes,
    *,
    prediction: str,
    confidence: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        import cv2

        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Uploaded image could not be decoded.")
        rng = np.random.default_rng(42)
        sigma = 0.03 * 255.0
        noise = rng.normal(0.0, sigma, size=image.shape)
        adversarial_image = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        difference = cv2.absdiff(adversarial_image, image)
        difference_gray = cv2.cvtColor(difference, cv2.COLOR_BGR2GRAY)
        difference_map = cv2.normalize(difference_gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        affected_mask = difference_gray > 5
        overlay = image.copy()
        red = np.zeros_like(image)
        red[:, :, 2] = 255
        overlay[affected_mask] = cv2.addWeighted(image[affected_mask], 0.55, red[affected_mask], 0.45, 0)

        ok_adv, adv_png = cv2.imencode(".png", adversarial_image)
        ok_diff, diff_png = cv2.imencode(".png", difference_map)
        ok_overlay, overlay_png = cv2.imencode(".png", overlay)
        if not (ok_adv and ok_diff and ok_overlay):
            raise ValueError("Could not encode adversarial visual artifacts.")

        attacked_class, attacked_confidence, _ = _image_prediction(adv_png.tobytes(), disease_key, "image/png")
        labels = _class_labels(disease_key, get_disease(disease_key).labels)
        attacked_prediction = labels[attacked_class] if 0 <= attacked_class < len(labels) else str(attacked_class)
        perturbation_magnitude = float(np.mean(difference_gray) / 255.0)
        affected_percent = float(np.mean(affected_mask))
        artifacts = [
            {
                "kind": "adversarial_image",
                "filename": "adversarial-perturbed-image.png",
                "content_type": "image/png",
                "content": adv_png.tobytes(),
            },
            {
                "kind": "perturbation_map",
                "filename": "attack-perturbation-map.png",
                "content_type": "image/png",
                "content": diff_png.tobytes(),
            },
            {
                "kind": "affected_region_overlay",
                "filename": "affected-region-overlay.png",
                "content_type": "image/png",
                "content": overlay_png.tobytes(),
            },
        ]
        return {
            "modality": "image",
            "status": "Evaluated",
            "attack_type": "Gaussian Noise",
            "attack_parameters": {"noise_stddev": 0.03, "random_seed": 42},
            "visual_artifact_kinds": ["input_image", "adversarial_image", "perturbation_map", "affected_region_overlay"],
            "perturbation_magnitude": round(perturbation_magnitude, 6),
            "percentage_pixels_affected": round(affected_percent, 6),
            "prediction_before_attack": prediction,
            "confidence_before_attack": confidence,
            "prediction_under_attack": attacked_prediction,
            "confidence_under_attack": round(attacked_confidence, 4),
            "prediction_changed": attacked_prediction != prediction,
            "note": "Attack perturbation map shows pixel-level input changes. It is separate from model explanation heatmaps.",
        }, artifacts
    except Exception as exc:
        return {
            "modality": "image",
            "status": "Not Evaluated",
        "reason": str(exc),
        }, []


def _image_explainability_artifacts(
    disease_key: str,
    image_bytes: bytes,
    content_type: str,
    *,
    model_class: int,
    confidence: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        import cv2

        encoded = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Uploaded image could not be decoded.")

        height, width = image.shape[:2]
        grid = 8
        saliency = np.zeros((grid, grid), dtype=np.float32)
        blurred = cv2.GaussianBlur(image, (31, 31), 0)

        for row in range(grid):
            y0 = int(row * height / grid)
            y1 = int((row + 1) * height / grid)
            for column in range(grid):
                x0 = int(column * width / grid)
                x1 = int((column + 1) * width / grid)
                occluded = image.copy()
                occluded[y0:y1, x0:x1] = blurred[y0:y1, x0:x1]
                ok, encoded_occluded = cv2.imencode(".png", occluded)
                if not ok:
                    continue
                occluded_class, occluded_confidence, _ = _image_prediction(
                    encoded_occluded.tobytes(),
                    disease_key,
                    "image/png",
                )
                if occluded_class != model_class:
                    saliency[row, column] = float(confidence)
                else:
                    saliency[row, column] = max(0.0, float(confidence) - float(occluded_confidence))

        heatmap = cv2.resize(saliency, (width, height), interpolation=cv2.INTER_CUBIC)
        max_value = float(heatmap.max())
        if max_value > 0:
            heatmap = heatmap / max_value
        heatmap_u8 = np.clip(heatmap * 255, 0, 255).astype(np.uint8)
        color_heatmap = cv2.applyColorMap(heatmap_u8, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(image, 0.55, color_heatmap, 0.45, 0)
        ok, overlay_png = cv2.imencode(".png", overlay)
        if not ok:
            raise ValueError("Could not encode the image explanation heatmap.")

        artifact = {
            "kind": "gradcam_heatmap",
            "filename": "gradcam-occlusion-heatmap.png",
            "content_type": "image/png",
            "content": overlay_png.tobytes(),
        }
        explanation = {
            "gradcam": {
                "available": True,
                "method": "Occlusion Sensitivity Heatmap",
                "gradcam_available": False,
                "artifact_kind": "gradcam_heatmap",
                "artifact_filename": artifact["filename"],
                "model_bound": True,
                "grid_size": grid,
                "target_class": model_class,
                "target_confidence": round(float(confidence), 4),
                "note": (
                    "This image model uses OpenCV/sklearn features, so CNN Grad-CAM is not available. "
                    "The displayed heatmap is a model-bound occlusion sensitivity fallback showing regions "
                    "where masking changed the selected prediction confidence."
                ),
            }
        }
        return explanation, [artifact]
    except Exception as exc:
        return {
            "gradcam": {
                "available": False,
                "method": "Grad-CAM",
                "reason": f"Image explanation heatmap could not be generated: {exc}",
            }
        }, []


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


def _metric(metrics: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = metrics.get(key)
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _performance_metrics(metrics: dict[str, Any]) -> dict[str, float | None]:
    return {
        "accuracy": _metric(metrics, "accuracy", "clean_accuracy"),
        "balanced_accuracy": _metric(metrics, "balanced_accuracy"),
        "precision": _metric(metrics, "precision"),
        "recall": _metric(metrics, "recall"),
        "f1_score": _metric(metrics, "f1_score", "f1"),
        "sensitivity": _metric(metrics, "sensitivity"),
        "specificity": _metric(metrics, "specificity"),
        "roc_auc": _metric(metrics, "roc_auc", "auc"),
    }


def _attack_accuracy(adversarial: dict[str, Any]) -> float | None:
    return _metric(adversarial, "after_attack_accuracy", "attack_accuracy", "under_attack_accuracy")


def _attack_type(adversarial: dict[str, Any], modality: str) -> str:
    if adversarial.get("attack_type"):
        return str(adversarial["attack_type"])
    if modality == "image":
        attacks = [name for name in ("fgsm_accuracy", "pgd_accuracy", "gaussian_noise_accuracy", "brightness_shift_accuracy") if adversarial.get(name) is not None]
        return " + ".join(name.replace("_accuracy", "").replace("_", " ").title() for name in attacks) or "Not Evaluated"
    attacks = [name for name in ("gaussian_noise_accuracy", "data_poisoning_accuracy") if adversarial.get(name) is not None]
    return " + ".join(name.replace("_accuracy", "").replace("_", " ").title() for name in attacks) or "Not Evaluated"


def _impact_level(degradation: float | None) -> str:
    if degradation is None:
        return "Not Evaluated"
    if degradation < 0.03:
        return "Low"
    if degradation < 0.10:
        return "Moderate"
    return "High"


def _robustness_status(robustness_score: float | None) -> str:
    if robustness_score is None:
        return "Not Evaluated"
    if robustness_score >= 0.85:
        return "Stable"
    if robustness_score >= 0.65:
        return "Degraded"
    return "Vulnerable"


def _defense_payload(metadata: dict[str, Any]) -> dict[str, Any]:
    defense = metadata.get("adversarial_defense") or metadata.get("defense_evaluation")
    if not isinstance(defense, dict) or not defense:
        return {
            "status": "Defense evaluation not available",
            "method": None,
            "defended_model_version": None,
            "after_defense_metrics": None,
            "comparison": None,
        }
    return {
        "status": defense.get("status", "Completed"),
        "method": defense.get("method"),
        "defended_model_version": defense.get("defended_model_version"),
        "after_defense_metrics": defense.get("after_defense_metrics"),
        "comparison": defense.get("comparison"),
    }


def _robustness_conclusion(defense: dict[str, Any], robustness_status: str) -> str:
    after = defense.get("after_defense_metrics") if isinstance(defense, dict) else None
    comparison = defense.get("comparison") if isinstance(defense, dict) else None
    if not isinstance(after, dict):
        return (
            f"The model robustness status is {robustness_status.lower()} under the evaluated attack conditions. "
            "Defense evaluation is not available for this model version."
        )
    clean_delta = _as_float((comparison or {}).get("clean_accuracy_delta"), 0.0)
    attack_delta = _as_float((comparison or {}).get("under_attack_accuracy_delta"), 0.0)
    if clean_delta >= 0 and attack_delta > 0:
        return "Model performance and adversarial resilience improved after the evaluated defense."
    if attack_delta > 0:
        return "Adversarial resilience improved after defense, with a measured trade-off in clean-data performance."
    return "The model remains vulnerable to the evaluated attack conditions and requires further robustness improvement."



def _aecs_status(score: float | None) -> str:
    if score is None:
        return "Not Available"
    if score >= 0.85:
        return "Highly Stable"
    if score >= 0.65:
        return "Moderately Stable"
    if score >= 0.40:
        return "Low Stability"
    return "Unstable"


def _aecs_from_vectors(
    before: list[float],
    after: list[float],
    *,
    modality: str,
    method: str,
    feature_names: list[str] | None = None,
) -> dict[str, Any]:
    if not before or not after:
        return {
            "available": False,
            "score": None,
            "reason": "Original and adversarial explanation vectors are required for AECS.",
            "original_explanation": "Not Available",
            "adversarial_explanation": "Not Available",
            "status": "Not Available",
            "method": method,
            "modality": modality,
        }
    if len(before) != len(after):
        return {
            "available": False,
            "score": None,
            "reason": "Original and adversarial explanation vectors have different dimensions.",
            "original_explanation": "Generated",
            "adversarial_explanation": "Generated",
            "status": "Not Available",
            "method": method,
            "modality": modality,
        }
    before_vector = np.asarray(before, dtype=np.float64)
    after_vector = np.asarray(after, dtype=np.float64)
    distance = float(np.linalg.norm(before_vector - after_vector))
    denominator = float(np.linalg.norm(before_vector)) + 1e-9
    similarity = float(np.clip(1.0 - (distance / denominator), 0.0, 1.0))
    return {
        "available": True,
        "score": round(similarity, 4),
        "score_percent": round(similarity * 100, 2),
        "similarity": round(similarity, 4),
        "similarity_percent": round(similarity * 100, 2),
        "distance": round(distance, 6),
        "original_explanation": "Generated",
        "adversarial_explanation": "Generated",
        "status": _aecs_status(similarity),
        "method": method,
        "formula": "AECS = max(0, min(100, (1 - ||E_before - E_after||2 / (||E_before||2 + epsilon)) * 100))",
        "epsilon": 1e-9,
        "modality": modality,
        "feature_names": feature_names or [],
    }


def _tabular_explanation_vector(
    disease_key: str,
    features: dict[str, Any],
    *,
    model_class: int,
    confidence: float,
) -> tuple[list[float], list[str]]:
    schema = get_feature_schema(disease_key)
    vector: list[float] = []
    names: list[str] = []
    for item in schema:
        if item.get("input_type") in {"boolean", "category"}:
            continue
        name = item["name"]
        if name not in features:
            continue
        original = float(features[name])
        minimum = item.get("minimum")
        maximum = item.get("maximum")
        if minimum is not None and maximum is not None and float(maximum) > float(minimum):
            delta = 0.01 * (float(maximum) - float(minimum))
        else:
            delta = max(abs(original) * 0.01, 0.01)
        trial = dict(features)
        attacked = original + delta
        if maximum is not None:
            attacked = min(attacked, float(maximum))
        if np.isclose(attacked, original):
            attacked = original - delta
            if minimum is not None:
                attacked = max(attacked, float(minimum))
        if np.isclose(attacked, original):
            continue
        trial[name] = attacked
        perturbed_class, perturbed_confidence, _ = _tabular_prediction(trial, disease_key)
        contribution = abs(float(confidence) - float(perturbed_confidence))
        if perturbed_class != model_class:
            contribution += 1.0
        vector.append(round(float(contribution), 8))
        names.append(name)
    return vector, names


def _calculate_tabular_aecs(
    disease_key: str,
    features: dict[str, Any],
    *,
    model_class: int,
    confidence: float,
    patient_attack: dict[str, Any] | None,
) -> dict[str, Any]:
    if not patient_attack or patient_attack.get("status") != "Evaluated":
        return {
            "available": False,
            "score": None,
            "reason": "Tabular adversarial values were not evaluated for this diagnosis.",
            "original_explanation": "Not Available",
            "adversarial_explanation": "Not Available",
            "status": "Not Available",
            "modality": "tabular",
        }
    adversarial_values = patient_attack.get("adversarial_values")
    if not isinstance(adversarial_values, dict):
        return {
            "available": False,
            "score": None,
            "reason": "Adversarial tabular feature values are missing.",
            "original_explanation": "Not Available",
            "adversarial_explanation": "Not Available",
            "status": "Not Available",
            "modality": "tabular",
        }
    before_vector, feature_names = _tabular_explanation_vector(
        disease_key,
        features,
        model_class=model_class,
        confidence=confidence,
    )
    adversarial_class, adversarial_confidence, normalized_adversarial = _tabular_prediction(
        adversarial_values,
        disease_key,
    )
    after_vector, _ = _tabular_explanation_vector(
        disease_key,
        normalized_adversarial,
        model_class=adversarial_class,
        confidence=adversarial_confidence,
    )
    return _aecs_from_vectors(
        before_vector,
        after_vector,
        modality="tabular",
        method="local_feature_sensitivity_l2",
        feature_names=feature_names,
    )


def _image_occlusion_vector(
    disease_key: str,
    image_bytes: bytes,
    *,
    model_class: int,
    confidence: float,
    grid: int = 4,
) -> list[float]:
    import cv2

    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Image could not be decoded for AECS.")
    height, width = image.shape[:2]
    blurred = cv2.GaussianBlur(image, (31, 31), 0)
    vector: list[float] = []
    for row in range(grid):
        y0 = int(row * height / grid)
        y1 = int((row + 1) * height / grid)
        for column in range(grid):
            x0 = int(column * width / grid)
            x1 = int((column + 1) * width / grid)
            occluded = image.copy()
            occluded[y0:y1, x0:x1] = blurred[y0:y1, x0:x1]
            ok, encoded_occluded = cv2.imencode(".png", occluded)
            if not ok:
                vector.append(0.0)
                continue
            occluded_class, occluded_confidence, _ = _image_prediction(
                encoded_occluded.tobytes(),
                disease_key,
                "image/png",
            )
            contribution = abs(float(confidence) - float(occluded_confidence))
            if occluded_class != model_class:
                contribution += 1.0
            vector.append(round(float(contribution), 8))
    return vector


def _calculate_image_aecs(
    disease_key: str,
    image_bytes: bytes,
    adversarial_image_bytes: bytes | None,
    *,
    model_class: int,
    confidence: float,
) -> dict[str, Any]:
    if not adversarial_image_bytes:
        return {
            "available": False,
            "score": None,
            "reason": "Adversarial image artifact was not generated for this diagnosis.",
            "original_explanation": "Not Available",
            "adversarial_explanation": "Not Available",
            "status": "Not Available",
            "modality": "image",
        }
    try:
        before_vector = _image_occlusion_vector(
            disease_key,
            image_bytes,
            model_class=model_class,
            confidence=confidence,
        )
        adversarial_class, adversarial_confidence, _ = _image_prediction(
            adversarial_image_bytes,
            disease_key,
            "image/png",
        )
        after_vector = _image_occlusion_vector(
            disease_key,
            adversarial_image_bytes,
            model_class=adversarial_class,
            confidence=adversarial_confidence,
        )
        return _aecs_from_vectors(
            before_vector,
            after_vector,
            modality="image",
            method="occlusion_saliency_l2",
            feature_names=[f"grid_cell_{index + 1}" for index in range(len(before_vector))],
        )
    except Exception as exc:
        return {
            "available": False,
            "score": None,
            "reason": str(exc),
            "original_explanation": "Not Available",
            "adversarial_explanation": "Not Available",
            "status": "Not Available",
            "modality": "image",
        }

def _build_adversarial_report(
    *,
    disease_key: str,
    modality: str,
    metadata: dict[str, Any],
    metrics: dict[str, Any],
    adversarial: dict[str, Any],
    patient_attack: dict[str, Any] | None,
) -> dict[str, Any]:
    clean = _performance_metrics(metrics)
    under_attack_accuracy = _attack_accuracy(adversarial)
    under_attack = {key: None for key in clean}
    under_attack["accuracy"] = under_attack_accuracy
    under_attack["robustness_score"] = _metric(adversarial, "robustness_score")
    clean["robustness_score"] = 1.0
    before_accuracy = clean.get("accuracy")
    degradation = (
        round(before_accuracy - under_attack_accuracy, 4)
        if before_accuracy is not None and under_attack_accuracy is not None
        else None
    )
    robustness_score = _metric(adversarial, "robustness_score")
    robustness_status = _robustness_status(robustness_score)
    defense = _defense_payload(metadata)
    return {
        **adversarial,
        "workflow_available": True,
        "model_id": f"{disease_key}:{metadata.get('selected_model', 'unknown')}:v{metadata.get('artifact_version', 'unknown')}",
        "model_name": metadata.get("selected_model"),
        "model_version": metadata.get("artifact_version"),
        "disease_key": disease_key,
        "input_modality": modality,
        "evaluation_dataset": metadata.get("kaggle_slug") or metadata.get("source") or "Stored test split",
        "evaluation_dataset_version": metadata.get("blockchain_audit", {}).get("dataset_fingerprint"),
        "timestamp": metadata.get("trained_at") or metadata.get("blockchain_audit", {}).get("timestamp"),
        "random_seed": 42,
        "attack_type": _attack_type(adversarial, modality),
        "attack_parameters": {
            "tabular_noise_scale": "0.05 * train feature std" if modality == "tabular" else None,
            "image_epsilon": 0.03 if modality == "image" else None,
            "poisoned_label_fraction": adversarial.get("poisoned_label_fraction"),
        },
        "before_attack_metrics": clean,
        "under_attack_metrics": under_attack,
        "attack_impact": {
            "accuracy_degradation": degradation,
            "prediction_change_rate": 0.0 if patient_attack and patient_attack.get("prediction_changed") is False else None,
            "impact_level": _impact_level(degradation),
            "robustness_status": robustness_status,
        },
        "patient_attack": patient_attack or {"status": "Not Evaluated"},
        "defense": defense,
        "conclusion": _robustness_conclusion(defense, robustness_status),
    }


def _build_attack_trust_evolution(components: Any, trust_score: float) -> dict[str, Any]:
    after_components = components.as_dict()
    before_components = {**after_components, "robustness": 1.0}
    before_score = round(
        sum(float(before_components.get(key, 0.0)) * float(weight) for key, weight in DTEI_WEIGHTS.items()),
        4,
    )
    after_score = round(float(trust_score), 4)
    return {
        "basis": "Before-attack DTEI uses the same diagnosis components with clean robustness set to 1.0; after-attack DTEI uses the evaluated adversarial robustness component.",
        "before_components": before_components,
        "after_components": after_components,
        "weights": DTEI_WEIGHTS,
        "before_score": before_score,
        "after_score": after_score,
        "trust_change": round(after_score - before_score, 4),
        "before_status": dtei_status(before_score),
        "after_status": dtei_status(after_score),
    }


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
    patient_attack: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], float, float, Any]:
    metadata = load_model_metadata(disease_key)
    explanation = _merge_metadata_explanations(disease_key, features, confidence, metadata)
    trained_adversarial = metadata.get("adversarial_robustness")
    adversarial = trained_adversarial if isinstance(trained_adversarial, dict) else evaluate_attacks(confidence)
    # Compute AECS dynamically from per-case explanations when possible. If
    # unavailable, do not silently fall back to stored metadata AECS.
    try:
        aecs_value, aecs_reason, aecs_distance = calculate_aecs(
            confidence, explanation=explanation, adversarial=adversarial, patient_attack=patient_attack
        )
    except TypeError:
        # Backwards compatibility: older calculate_aecs implementations accepted
        # only confidence and returned a float. Fall back to that behavior.
        aecs_value, aecs_reason, aecs_distance = (calculate_aecs(confidence), None, None)

    if aecs_value is None:
        # Indicate unavailability in the adversarial report for presentation;
        # store a conservative default (0.0) to satisfy DB schema while
        # ensuring the UI/report shows the explanatory reason.
        aecs = 0.0
        adversarial["aecs_available"] = False
        adversarial["aecs_reason"] = aecs_reason or "AECS not computed for this diagnosis."
    else:
        aecs = float(aecs_value)
        adversarial["aecs_available"] = True
        adversarial.pop("aecs_reason", None)
    if aecs_distance is not None:
        adversarial["explanation_distance"] = float(aecs_distance)
        adversarial["explanation_similarity"] = float(aecs if isinstance(aecs, float) else 0.0)

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
    patient_attack_analysis: dict[str, Any] | None = None,
    extra_explanation: dict[str, Any] | None = None,
    aecs_analysis: dict[str, Any] | None = None,
) -> PredictionResponse:
    disease = get_disease(disease_key)
    if len(patient_name.strip()) < 2:
        raise PredictionInputError("Enter the patient's full name.")
    labels = _class_labels(disease.key, disease.labels)
    prediction = labels[model_class] if 0 <= model_class < len(labels) else str(model_class)
    confidence = round(confidence, 3)
    if actor.role == Role.PATIENT.value:
        ensure_user_public_patient_id(db, actor)
        patient_id = actor.id
        patient_email = actor.email
    else:
        patient = find_patient_user(db, patient_id, patient_email)
        if patient:
            ensure_user_public_patient_id(db, patient)
            patient_id = patient.id
            patient_email = patient.email
    metadata = load_model_metadata(disease.key)
    metrics = load_metrics(disease.key)
    explanation, adversarial, aecs, trust_score, components = _runtime_trust_bundle(
        disease.key,
        features,
        confidence,
        patient_attack=patient_attack_analysis,
    )
    for key, value in (extra_explanation or {}).items():
        if isinstance(value, dict) and isinstance(explanation.get(key), dict):
            explanation[key] = {**explanation[key], **value}
        else:
            explanation[key] = value
    adversarial = _build_adversarial_report(
        disease_key=disease.key,
        modality=input_modality,
        metadata=metadata,
        metrics=metrics,
        adversarial=adversarial,
        patient_attack=patient_attack_analysis,
    )
    if aecs_analysis is None and input_modality == "tabular":
        aecs_analysis = _calculate_tabular_aecs(
            disease.key,
            features,
            model_class=model_class,
            confidence=confidence,
            patient_attack=patient_attack_analysis,
        )
    if aecs_analysis is None:
        aecs_analysis = {
            "available": False,
            "score": None,
            "reason": "Dynamic AECS explanation vectors were not generated for this diagnosis.",
            "original_explanation": "Not Available",
            "adversarial_explanation": "Not Available",
            "status": "Not Available",
            "modality": input_modality,
        }
    aecs = _as_float(aecs_analysis.get("score"), 0.0) if aecs_analysis.get("available") else 0.0
    explanation["aecs"] = aecs_analysis
    adversarial["aecs"] = aecs_analysis
    metadata = load_model_metadata(disease.key)
    compliance = 1.0 if metadata.get("deployment_status") == "ready_for_research" else 0.5
    trust_score, components = calculate_dtei(
        confidence=confidence,
        explanation_stability=aecs,
        robustness_score=_as_float(adversarial.get("robustness_score"), 0.0),
        blockchain_integrity=1.0,
        compliance=compliance,
    )
    trust_evolution = _build_attack_trust_evolution(components, trust_score)
    adversarial["trust_evolution"] = trust_evolution
    security_findings = evaluate_adversarial_security_findings(adversarial)
    adversarial["security_event"] = {
        "generated": bool(security_findings),
        "findings": security_findings,
        "thresholds": adversarial_security_thresholds(),
    }
    metrics = {
        **metrics,
        "adversarial": adversarial,
        "dtei": {
            "formula": "DTEI = alpha*F + beta*I + gamma*R + delta*B + lambda*C",
            "weights": DTEI_WEIGHTS,
            "components": components.as_dict(),
            "attack_comparison": trust_evolution,
            "score": trust_score,
            "status": dtei_status(trust_score),
            "normalization": "All components are normalized to 0-1 before applying weights.",
        },
    }
    record = DiagnosisRecord(
        patient_id=patient_id,
        patient_name=patient_name.strip(),
        patient_email=patient_email.strip().lower(),
        doctor_id=actor.id if actor.role == Role.DOCTOR.value else None,
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
    notify_adversarial_security_event(db, record, adversarial, security_findings)
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
        patient_public_id=public_patient_id_for_record(db, record),
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
    labels = _class_labels(disease.key, disease.labels)
    prediction = labels[model_class] if 0 <= model_class < len(labels) else str(model_class)
    patient_attack = _tabular_patient_attack(
        disease.key,
        normalized,
        prediction=prediction,
        confidence=round(confidence, 3),
    )
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
        patient_attack_analysis=patient_attack,
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
    disease = get_disease(disease_key)
    labels = _class_labels(disease.key, disease.labels)
    prediction = labels[model_class] if 0 <= model_class < len(labels) else str(model_class)
    patient_attack, attack_artifacts = _image_patient_attack(
        disease_key,
        image_bytes,
        prediction=prediction,
        confidence=round(confidence, 3),
    )
    image_explanation, explanation_artifacts = _image_explainability_artifacts(
        disease_key,
        image_bytes,
        content_type,
        model_class=model_class,
        confidence=round(confidence, 3),
    )
    adversarial_image_bytes = next(
        (item.get("content") for item in attack_artifacts if item.get("kind") == "adversarial_image"),
        None,
    )
    aecs_analysis = _calculate_image_aecs(
        disease_key,
        image_bytes,
        adversarial_image_bytes,
        model_class=model_class,
        confidence=round(confidence, 3),
    )
    artifacts = [
        {
            "kind": "input_image",
            "filename": filename,
            "content_type": content_type or "application/octet-stream",
            "content": image_bytes,
        }
    ] + explanation_artifacts + attack_artifacts
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
        patient_attack_analysis=patient_attack,
        extra_explanation=image_explanation,
        aecs_analysis=aecs_analysis,
    )


# Backwards-compatible alias expected by other modules
def make_prediction(db: Session, payload: PredictionRequest, actor: User) -> PredictionResponse:
    """Compatibility wrapper for older callers importing `make_prediction`.

    Delegates to `run_diagnosis` which implements the current prediction workflow.
    """
    return run_diagnosis(db=db, payload=payload, actor=actor)
