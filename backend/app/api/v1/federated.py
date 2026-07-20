from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.db.models import User
from app.schemas import FederatedClientUpdateRequest, FederatedRoundCreateRequest, FederatedSimulationRequest
from app.services.federated import (
    aggregate_round,
    create_round,
    federated_dashboard,
    run_demo_round,
    submit_update,
    synchronize_trust,
)

router = APIRouter()


@router.get("/dashboard")
def dashboard(
    _: User = Depends(require_permission("trust:view")),
    db: Session = Depends(get_db),
) -> dict:
    return federated_dashboard(db)


@router.post("/rounds")
def start_round(
    payload: FederatedRoundCreateRequest,
    user: User = Depends(require_permission("federated:manage")),
    db: Session = Depends(get_db),
) -> dict:
    round_row = create_round(db, payload, user)
    return federated_dashboard(db) | {"created_round_id": round_row.id}


@router.post("/rounds/{round_id}/updates")
def submit_hospital_update(
    round_id: str,
    payload: FederatedClientUpdateRequest,
    user: User = Depends(require_permission("federated:manage")),
    db: Session = Depends(get_db),
) -> dict:
    update = submit_update(db, round_id, payload, user)
    return {
        "status": "accepted",
        "update_id": update.id,
        "payload_hash": update.payload_hash,
        "raw_data_shared": False,
        "dashboard": federated_dashboard(db),
    }


@router.post("/rounds/{round_id}/aggregate")
def aggregate(
    round_id: str,
    user: User = Depends(require_permission("federated:manage")),
    db: Session = Depends(get_db),
) -> dict:
    round_row = aggregate_round(db, round_id, user)
    return {
        "status": "aggregated",
        "round_id": round_row.id,
        "aggregate_hash": round_row.update_hash,
        "dashboard": federated_dashboard(db),
    }


@router.post("/demo-round")
def demo_round(
    payload: FederatedSimulationRequest,
    user: User = Depends(require_permission("federated:manage")),
    db: Session = Depends(get_db),
) -> dict:
    round_row = run_demo_round(db, payload, user)
    return {
        "status": "demo_round_completed",
        "round_id": round_row.id,
        "aggregate_hash": round_row.update_hash,
        "dashboard": federated_dashboard(db),
    }


@router.post("/synchronize")
def synchronize(
    user: User = Depends(require_permission("federated:manage")),
    db: Session = Depends(get_db),
) -> dict:
    return synchronize_trust(db, user)
