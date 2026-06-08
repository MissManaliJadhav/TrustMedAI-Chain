from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.models import TrustHistory, User
from app.db.session import get_db
from app.schemas import TrustPoint

router = APIRouter()


@router.get("/history", response_model=list[TrustPoint])
def trust_history(
    disease_key: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("trust:view")),
) -> list[TrustPoint]:
    query = db.query(TrustHistory).order_by(TrustHistory.created_at.asc())
    if disease_key:
        query = query.filter(TrustHistory.disease_key == disease_key)
    rows = query.limit(250).all()
    return [
        TrustPoint(
            timestamp=row.created_at,
            disease_key=row.disease_key,
            dtei=row.dtei,
            fidelity=row.fidelity,
            interpretability=row.interpretability,
            robustness=row.robustness,
            blockchain_integrity=row.blockchain_integrity,
            compliance=row.compliance,
        )
        for row in rows
    ]


@router.get("/weights")
def trust_weights() -> dict[str, float]:
    return {"alpha": 0.30, "beta": 0.20, "gamma": 0.20, "delta": 0.15, "lambda": 0.15}
