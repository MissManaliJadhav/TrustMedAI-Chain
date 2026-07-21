from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.models import DiagnosisArtifact, DiagnosisRecord, User
from app.db.session import get_db
from app.schemas import DiagnosisArtifactResponse
from app.services.access import can_access_diagnosis
from app.services.audit import record_audit_event
from app.services.patient_ids import ensure_user_public_patient_id
from app.services.reports import build_pdf_report
from app.services.storage import read_object

router = APIRouter()


def _authorized_record(db: Session, user: User, diagnosis_id: str) -> DiagnosisRecord:
    record = db.query(DiagnosisRecord).filter(DiagnosisRecord.id == diagnosis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    if not can_access_diagnosis(db, user, record):
        raise HTTPException(status_code=403, detail="You cannot access this diagnosis")
    return record


@router.get("/{diagnosis_id}/artifacts", response_model=list[DiagnosisArtifactResponse])
def list_artifacts(
    diagnosis_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports:download")),
) -> list[DiagnosisArtifact]:
    record = _authorized_record(db, user, diagnosis_id)
    return list(record.artifacts)


@router.get("/{diagnosis_id}/artifacts/{artifact_id}")
def download_artifact(
    diagnosis_id: str,
    artifact_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports:download")),
) -> Response:
    record = _authorized_record(db, user, diagnosis_id)
    artifact = (
        db.query(DiagnosisArtifact)
        .filter(
            DiagnosisArtifact.id == artifact_id,
            DiagnosisArtifact.diagnosis_id == record.id,
        )
        .first()
    )
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    content = read_object(artifact.object_path)
    record_audit_event(
        db,
        actor=user,
        action="report.downloaded",
        resource_type="diagnosis",
        resource_id=record.id,
        metadata={"artifact_id": artifact.id, "kind": artifact.kind},
        request=request,
    )
    db.commit()
    return Response(
        content=content,
        media_type=artifact.content_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.original_filename}"'},
    )


@router.get("/{diagnosis_id}.pdf")
def report(
    diagnosis_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports:download")),
) -> Response:
    record = _authorized_record(db, user, diagnosis_id)
    patient_user = None
    if record.patient_id:
        patient_user = db.query(User).filter(User.id == record.patient_id).first()
    if patient_user is None and record.patient_email:
        patient_user = db.query(User).filter(User.email == record.patient_email.lower()).first()
    if patient_user:
        ensure_user_public_patient_id(db, patient_user)
    pdf = build_pdf_report(record, patient_user)
    record_audit_event(
        db,
        actor=user,
        action="report.generated",
        resource_type="diagnosis",
        resource_id=record.id,
        metadata={"format": "pdf"},
        request=request,
    )
    record_audit_event(
        db,
        actor=user,
        action="report.downloaded",
        resource_type="diagnosis",
        resource_id=record.id,
        metadata={"format": "pdf"},
        request=request,
    )
    db.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=trustmedai-{diagnosis_id}.pdf"},
    )
