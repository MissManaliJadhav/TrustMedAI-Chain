from fastapi import APIRouter, HTTPException

from app.services.catalog import DISEASE_CATALOG, dataset_manifest, get_disease
from app.services.prediction import get_feature_schema, load_model, load_model_metadata

router = APIRouter()


@router.get("/diseases")
def diseases() -> list[dict]:
    return [item.model_dump() for item in DISEASE_CATALOG]


@router.get("/diseases/{disease_key}/features")
def disease_features(disease_key: str) -> dict:
    try:
        disease = get_disease(disease_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    features = get_feature_schema(disease_key)
    model_info = load_model_metadata(disease_key)
    is_blocked = model_info.get("deployment_status") == "blocked_low_quality"
    return {
        **disease.model_dump(),
        "input_mode": "image" if disease.modality == "image" else "features",
        "model_available": (
            bool(features) and not is_blocked
            if disease.modality != "image"
            else load_model(disease_key) is not None
        ),
        "features": features,
        "model_info": model_info,
    }


@router.get("/manifest")
def manifest() -> dict:
    return dataset_manifest()
