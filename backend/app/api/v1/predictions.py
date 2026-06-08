from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.models import User
from app.db.session import get_db
from app.schemas import PredictionRequest, PredictionResponse
from app.services.prediction import run_diagnosis

router = APIRouter()


@router.post("", response_model=PredictionResponse)
def predict(
    payload: PredictionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("diagnosis:create")),
) -> PredictionResponse:
    return run_diagnosis(db=db, payload=payload, actor=user)
