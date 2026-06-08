from fastapi import APIRouter

from app.services.catalog import DISEASE_CATALOG, dataset_manifest

router = APIRouter()


@router.get("/diseases")
def diseases() -> list[dict]:
    return [item.model_dump() for item in DISEASE_CATALOG]


@router.get("/manifest")
def manifest() -> dict:
    return dataset_manifest()
