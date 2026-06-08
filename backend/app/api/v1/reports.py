from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.models import DiagnosisRecord, User
from app.db.session import get_db
from app.services.reports import build_pdf_report

router = APIRouter()


@router.get("/{diagnosis_id}.pdf")
def report(
    diagnosis_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("reports:download")),
) -> Response:
    record = db.query(DiagnosisRecord).filter(DiagnosisRecord.id == diagnosis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    pdf = build_pdf_report(record)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=trustmedai-{diagnosis_id}.pdf"},
    )
