import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.rbac import Role
from app.db.models import DiagnosisRecord, User
from app.db.session import get_db
from app.schemas import DiagnosisRecordResponse, PredictionRequest, PredictionResponse
from app.services.prediction import PredictionInputError, run_diagnosis, run_image_diagnosis

router = APIRouter()


@router.post("", response_model=PredictionResponse)
def predict(
    payload: PredictionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("diagnosis:create")),
) -> PredictionResponse:
    try:
        return run_diagnosis(db=db, payload=payload, actor=user)
    except PredictionInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/tabular", response_model=PredictionResponse)
async def predict_tabular_with_files(
    disease_key: str = Form(...),
    patient_name: str = Form(...),
    patient_email: str = Form(...),
    features_json: str = Form(...),
    patient_id: str | None = Form(None),
    doctor_notes: str = Form(""),
    supporting_pdf: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("diagnosis:create")),
) -> PredictionResponse:
    try:
        features = json.loads(features_json)
        if not isinstance(features, dict):
            raise ValueError
        payload = PredictionRequest(
            disease_key=disease_key,
            patient_name=patient_name,
            patient_email=patient_email,
            patient_id=patient_id,
            features=features,
            doctor_notes=doctor_notes,
        )
        pdf_bytes = await supporting_pdf.read() if supporting_pdf else None
        return run_diagnosis(
            db=db,
            payload=payload,
            actor=user,
            supporting_pdf_bytes=pdf_bytes,
            supporting_pdf_filename=supporting_pdf.filename if supporting_pdf else None,
            supporting_pdf_content_type=supporting_pdf.content_type if supporting_pdf else None,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="features_json must be a JSON object.") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except PredictionInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/image", response_model=PredictionResponse)
async def predict_image(
    disease_key: str = Form(...),
    patient_name: str = Form(...),
    patient_email: str = Form(...),
    image: UploadFile = File(...),
    supporting_pdf: UploadFile | None = File(None),
    patient_id: str | None = Form(None),
    doctor_notes: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("diagnosis:create")),
) -> PredictionResponse:
    try:
        validated_email = str(TypeAdapter(EmailStr).validate_python(patient_email))
        image_bytes = await image.read()
        pdf_bytes = await supporting_pdf.read() if supporting_pdf else None
        return run_image_diagnosis(
            db=db,
            disease_key=disease_key,
            image_bytes=image_bytes,
            filename=image.filename or "uploaded-image",
            content_type=image.content_type or "",
            patient_name=patient_name,
            patient_email=validated_email,
            patient_id=patient_id,
            doctor_notes=doctor_notes,
            actor=user,
            supporting_pdf_bytes=pdf_bytes,
            supporting_pdf_filename=supporting_pdf.filename if supporting_pdf else None,
            supporting_pdf_content_type=supporting_pdf.content_type if supporting_pdf else None,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Enter a valid patient email address.") from exc
    except PredictionInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[DiagnosisRecordResponse])
def list_predictions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DiagnosisRecordResponse]:
    """
    List diagnosis records based on user role:
    - SUPER_ADMIN: all records
    - HOSPITAL_ADMIN: records from their hospital
    - DOCTOR: records they created or patients in their hospital
    - PATIENT: only their own records
    - RESEARCHER: anonymized records
    """
    query = db.query(DiagnosisRecord)
    user_role = Role(user.role)
    
    if user_role == Role.SUPER_ADMIN:
        # Super admin sees all records
        pass
    elif user_role == Role.HOSPITAL_ADMIN:
        # Hospital admin sees records from their hospital
        hospital_user_ids = db.query(User.id).filter(User.hospital_id == user.hospital_id)
        query = query.filter(
            or_(
                DiagnosisRecord.doctor_id.in_(hospital_user_ids),
                DiagnosisRecord.patient_id.in_(hospital_user_ids),
            )
        )
    elif user_role == Role.DOCTOR:
        # Doctor sees records they created
        query = query.filter(DiagnosisRecord.doctor_id == user.id)
    elif user_role == Role.PATIENT:
        # Patient sees only their own records
        query = query.filter(
            or_(
                DiagnosisRecord.patient_id == user.id,
                DiagnosisRecord.patient_email == user.email.lower(),
            )
        )
    elif user_role == Role.RESEARCHER:
        # Researcher sees all records but we could add anonymization here
        pass
    
    records = query.order_by(DiagnosisRecord.created_at.desc()).limit(100).all()
    hide_patient_identity = user_role == Role.RESEARCHER
    return [
        DiagnosisRecordResponse(
            diagnosis_id=record.id,
            patient_id=None if hide_patient_identity else record.patient_id,
            patient_name=None if hide_patient_identity else record.patient_name,
            patient_email=None if hide_patient_identity else record.patient_email,
            doctor_id=record.doctor_id,
            disease_key=record.disease_key,
            prediction=record.prediction,
            confidence=record.confidence,
            input_modality=record.input_modality or "tabular",
            artifacts=[] if hide_patient_identity else list(record.artifacts),
            trust_score=record.trust_score,
            blockchain_hash=record.blockchain_hash,
            ethereum_tx_hash=record.ethereum_tx_hash,
            fabric_tx_id=record.fabric_tx_id,
            doctor_notes=record.doctor_notes,
            created_at=record.created_at,
        )
        for record in records
    ]
