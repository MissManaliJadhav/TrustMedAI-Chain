from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.db.models import User
from app.services.federated import federated_dashboard, synchronize_trust

router = APIRouter()


@router.get("/dashboard")
def dashboard(_: User = Depends(require_permission("trust:view"))) -> dict:
    return federated_dashboard()


@router.post("/synchronize")
def synchronize(_: User = Depends(require_permission("experiments:run"))) -> dict:
    return synchronize_trust()
