from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.models import DiagnosisRecord, User
from app.db.session import get_db
from app.services.access import can_access_diagnosis
from app.services.blockchain import explorer_snapshot, verify_diagnosis

router = APIRouter()


@router.get("/explorer")
def explorer(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit:view")),
) -> dict:
    return explorer_snapshot(db)


@router.get("/nodes")
def nodes(_: User = Depends(require_permission("blockchain:manage"))) -> dict:
    return {
        "fabric": [
            {"name": "fabric-peer-0", "status": "gateway-configured"},
            {"name": "fabric-orderer-0", "status": "network-profile-required"},
        ],
        "ethereum": [{"name": "trust-ledger-contract", "status": "configured-for-real-transactions"}],
    }


@router.get("/verify/{diagnosis_id}")
def verify_anchor(
    diagnosis_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("audit:view")),
) -> dict:
    record = db.query(DiagnosisRecord).filter(DiagnosisRecord.id == diagnosis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    if not can_access_diagnosis(db, user, record):
        raise HTTPException(status_code=403, detail="You cannot access this diagnosis")
    actor = db.query(User).filter(User.id == record.doctor_id).first() if record.doctor_id else None
    return verify_diagnosis(record, actor)
