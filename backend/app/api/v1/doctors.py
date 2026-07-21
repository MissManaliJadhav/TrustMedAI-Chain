from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rbac import Role
from app.db.models import AuditEvent, DiagnosisRecord, Notification, User
from app.db.session import get_db
from app.schemas import (
    DiagnosisRecordResponse,
    DoctorNoteRequest,
    DoctorPatientSummary,
    DoctorProfileResponse,
    DoctorProfileUpdate,
    DoctorProtectedProfileUpdate,
    DoctorReviewRequest,
    DoctorSummaryResponse,
    NotificationResponse,
)
from app.services.access import can_access_diagnosis
from app.services.audit import record_audit_event
from app.services.blockchain import verify_diagnosis
from app.services.notifications import is_high_risk, mark_notification_read, notify_user
from app.services.patient_ids import find_patient_user, public_patient_id_for_record
from app.services.reports import refresh_stored_pdf_report
from app.services.storage import read_object, store_object

router = APIRouter()

PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
DOCTOR_EDITABLE_FIELDS = {
    "specialization",
    "qualifications",
    "experience",
    "hospital_organization",
    "phone_number",
    "contact_information",
    "availability",
}


def _doctor_required(user: User) -> None:
    if Role(user.role) != Role.DOCTOR:
        raise HTTPException(status_code=403, detail="Doctor workspace access is required.")


def _doctor_records(db: Session, user: User) -> list[DiagnosisRecord]:
    role = Role(user.role)
    query = db.query(DiagnosisRecord)
    if role == Role.DOCTOR:
        query = query.filter(or_(DiagnosisRecord.doctor_id == user.id, DiagnosisRecord.doctor_id.is_(None)))
    else:
        query = query.filter(False)
    return query.order_by(DiagnosisRecord.created_at.desc()).all()


def _record_response(db: Session, record: DiagnosisRecord) -> DiagnosisRecordResponse:
    return DiagnosisRecordResponse(
        diagnosis_id=record.id,
        patient_id=record.patient_id,
        patient_public_id=public_patient_id_for_record(db, record),
        patient_name=record.patient_name,
        patient_email=record.patient_email,
        doctor_id=record.doctor_id,
        disease_key=record.disease_key,
        prediction=record.prediction,
        confidence=record.confidence,
        input_modality=record.input_modality or "tabular",
        artifacts=list(record.artifacts),
        trust_score=record.trust_score,
        blockchain_hash=record.blockchain_hash,
        ethereum_tx_hash=record.ethereum_tx_hash,
        fabric_tx_id=record.fabric_tx_id,
        doctor_notes=record.doctor_notes,
        review_status=record.review_status,
        doctor_decision=record.doctor_decision,
        final_clinical_decision=record.final_clinical_decision,
        review_notes=record.review_notes,
        reviewed_by_id=record.reviewed_by_id,
        reviewed_at=record.reviewed_at,
        priority=record.priority,
        created_at=record.created_at,
    )


def _profile_response(user: User) -> DoctorProfileResponse:
    profile = dict(user.profile or {})
    return DoctorProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        doctor_id=user.id,
        role=user.role,
        profile_photo_url="/doctors/profile/photo" if user.profile_photo_object_path else None,
        profile_photo_available=bool(user.profile_photo_object_path),
        medical_registration_number=profile.get("medical_registration_number"),
        specialization=profile.get("specialization"),
        qualifications=profile.get("qualifications"),
        experience=profile.get("experience"),
        hospital_organization=profile.get("hospital_organization") or (user.hospital.name if user.hospital else None),
        contact_information=profile.get("contact_information"),
        phone_number=profile.get("phone_number"),
        account_status="Active" if user.is_active else "Inactive",
        last_login=user.last_login_at,
        profile_verification_status=profile.get("profile_verification_status") or ("Verified" if user.is_verified else "Pending Verification"),
        created_at=user.created_at,
        profile_updated_at=user.profile_updated_at,
    )


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@router.get("/profile", response_model=DoctorProfileResponse)
def get_doctor_profile(user: User = Depends(get_current_user)) -> DoctorProfileResponse:
    _doctor_required(user)
    return _profile_response(user)


@router.put("/profile", response_model=DoctorProfileResponse)
def update_doctor_profile(
    payload: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DoctorProfileResponse:
    _doctor_required(user)
    profile = dict(user.profile or {})
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("full_name"):
        user.full_name = updates["full_name"].strip()
    for field in DOCTOR_EDITABLE_FIELDS:
        if field not in updates:
            continue
        cleaned = _clean(updates[field])
        if cleaned is None:
            profile.pop(field, None)
        else:
            profile[field] = cleaned
    user.profile = profile
    user.profile_updated_at = datetime.utcnow()
    record_audit_event(db, actor=user, action="doctor.profile.updated", resource_type="doctor", resource_id=user.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _profile_response(user)


@router.put("/profile/protected", response_model=DoctorProfileResponse)
def update_protected_doctor_profile(
    payload: DoctorProtectedProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DoctorProfileResponse:
    if Role(user.role) not in {Role.SUPER_ADMIN, Role.HOSPITAL_ADMIN}:
        raise HTTPException(status_code=403, detail="Protected professional identity fields require admin authorization.")
    doctor = db.query(User).filter(User.id == payload.doctor_id, User.role == Role.DOCTOR.value).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    profile = dict(doctor.profile or {})
    for field in ("medical_registration_number", "profile_verification_status", "account_status"):
        value = _clean(getattr(payload, field))
        if value is not None:
            profile[field] = value
    if payload.account_status:
        doctor.is_active = payload.account_status.strip().lower() == "active"
    if payload.profile_verification_status:
        doctor.is_verified = payload.profile_verification_status.strip().lower() == "verified"
    doctor.profile = profile
    doctor.profile_updated_at = datetime.utcnow()
    record_audit_event(db, actor=user, action="doctor.protected_identity.updated", resource_type="doctor", resource_id=doctor.id)
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return _profile_response(doctor)


@router.post("/profile/photo", response_model=DoctorProfileResponse)
async def upload_doctor_photo(
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DoctorProfileResponse:
    _doctor_required(user)
    if (photo.content_type or "") not in PHOTO_TYPES:
        raise HTTPException(status_code=422, detail="Upload a JPEG, PNG, or WebP profile photo.")
    content = await photo.read()
    if not content or len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="The profile photo must be between 1 byte and 5 MB.")
    suffix = Path(photo.filename or "doctor-photo").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg" if photo.content_type == "image/jpeg" else ".png"
    stored = store_object(f"doctors/{user.id}/photo-{uuid4().hex}{suffix}", content, photo.content_type or "image/jpeg")
    user.profile_photo_object_path = stored.object_path
    user.profile_photo_content_type = photo.content_type or "image/jpeg"
    user.profile_updated_at = datetime.utcnow()
    record_audit_event(db, actor=user, action="doctor.profile_photo.updated", resource_type="doctor", resource_id=user.id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _profile_response(user)


@router.get("/profile/photo")
def doctor_photo(user: User = Depends(get_current_user)) -> Response:
    _doctor_required(user)
    if not user.profile_photo_object_path:
        raise HTTPException(status_code=404, detail="No profile photo has been uploaded.")
    return Response(content=read_object(user.profile_photo_object_path), media_type=user.profile_photo_content_type or "image/jpeg")


@router.get("/dashboard", response_model=DoctorSummaryResponse)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DoctorSummaryResponse:
    _doctor_required(user)
    records = _doctor_records(db, user)
    today = datetime.utcnow().date()
    patient_keys = {(record.patient_id or record.patient_email or record.patient_name) for record in records if record.patient_id or record.patient_email or record.patient_name}
    reviewed = [record for record in records if (record.review_status or "pending") != "pending"]
    unread = db.query(func.count(Notification.id)).filter(Notification.user_id == user.id, Notification.is_read.is_(False)).scalar() or 0
    return DoctorSummaryResponse(
        total_assigned_patients=len(patient_keys),
        pending_diagnosis_reviews=sum(1 for record in records if (record.review_status or "pending") == "pending"),
        high_risk_cases=sum(1 for record in records if is_high_risk(record)),
        reviewed_diagnoses=len(reviewed),
        todays_new_cases=sum(1 for record in records if record.created_at and record.created_at.date() == today),
        average_ai_trust_score=round(sum(record.trust_score for record in records) / len(records), 3) if records else 0.0,
        blockchain_verified_records=sum(1 for record in records if record.ethereum_anchor_verified or record.fabric_anchor_verified),
        unread_notifications=int(unread),
    )


@router.get("/patients", response_model=list[DoctorPatientSummary])
def my_patients(
    search: str = "",
    filter: str = "all",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DoctorPatientSummary]:
    _doctor_required(user)
    grouped: dict[str, list[DiagnosisRecord]] = defaultdict(list)
    for record in _doctor_records(db, user):
        key = record.patient_id or record.patient_email or record.patient_name or record.id
        grouped[key].append(record)
    query = search.strip().lower()
    patients: list[DoctorPatientSummary] = []
    for records in grouped.values():
        latest = max(records, key=lambda item: item.created_at or datetime.min)
        if filter == "high-risk" and not any(is_high_risk(record) for record in records):
            continue
        haystack = " ".join([latest.patient_name or "", latest.patient_email or "", latest.patient_id or ""]).lower()
        if query and query not in haystack:
            continue
        patients.append(
            DoctorPatientSummary(
                patient_id=latest.patient_id,
                patient_public_id=public_patient_id_for_record(db, latest),
                patient_name=latest.patient_name,
                patient_email=latest.patient_email,
                total_diagnoses=len(records),
                active_cases=sum(1 for record in records if (record.review_status or "pending") == "pending"),
                latest_diagnosis_at=latest.created_at,
                average_trust_score=round(sum(record.trust_score for record in records) / len(records), 3),
            )
        )
    return sorted(patients, key=lambda item: item.latest_diagnosis_at or datetime.min, reverse=True)


@router.get("/patients/{patient_key}/history", response_model=list[DiagnosisRecordResponse])
def patient_history(
    patient_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DiagnosisRecordResponse]:
    _doctor_required(user)
    records = [
        record
        for record in _doctor_records(db, user)
        if patient_key in {record.patient_id, record.patient_email, record.patient_name}
    ]
    for record in records:
        record_audit_event(db, actor=user, action="patient_record.accessed", resource_type="patient", resource_id=patient_key, metadata={"diagnosis_id": record.id})
    db.commit()
    return [_record_response(db, record) for record in sorted(records, key=lambda item: item.created_at or datetime.min)]


@router.get("/reviews", response_model=list[DiagnosisRecordResponse])
def diagnosis_reviews(
    status: str = "all",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DiagnosisRecordResponse]:
    _doctor_required(user)
    records = _doctor_records(db, user)
    if status != "all":
        records = [record for record in records if (record.review_status or "pending") == status]
    return [_record_response(db, record) for record in records]


@router.get("/high-risk", response_model=list[DiagnosisRecordResponse])
def high_risk_cases(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[DiagnosisRecordResponse]:
    _doctor_required(user)
    return [_record_response(db, record) for record in _doctor_records(db, user) if is_high_risk(record)]


@router.post("/diagnoses/{diagnosis_id}/view", response_model=DiagnosisRecordResponse)
def view_diagnosis(
    diagnosis_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DiagnosisRecordResponse:
    _doctor_required(user)
    record = db.query(DiagnosisRecord).filter(DiagnosisRecord.id == diagnosis_id).first()
    if not record or not can_access_diagnosis(db, user, record):
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    record_audit_event(db, actor=user, action="diagnosis.viewed", resource_type="diagnosis", resource_id=record.id, request=request)
    db.commit()
    return _record_response(db, record)


@router.post("/diagnoses/{diagnosis_id}/note", response_model=DiagnosisRecordResponse)
def add_doctor_note(
    diagnosis_id: str,
    payload: DoctorNoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DiagnosisRecordResponse:
    _doctor_required(user)
    record = db.query(DiagnosisRecord).filter(DiagnosisRecord.id == diagnosis_id).first()
    if not record or not can_access_diagnosis(db, user, record):
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    existing = record.doctor_notes or ""
    record.doctor_notes = f"{existing}\n\n{payload.note}".strip()
    record_audit_event(db, actor=user, action="doctor_note.added", resource_type="diagnosis", resource_id=record.id, request=request)
    db.add(record)
    db.commit()
    db.refresh(record)
    return _record_response(db, record)


@router.post("/diagnoses/{diagnosis_id}/finalize", response_model=DiagnosisRecordResponse)
def finalize_review(
    diagnosis_id: str,
    payload: DoctorReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DiagnosisRecordResponse:
    _doctor_required(user)
    record = db.query(DiagnosisRecord).filter(DiagnosisRecord.id == diagnosis_id).first()
    if not record or not can_access_diagnosis(db, user, record):
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    decision = payload.doctor_decision.strip().lower()
    action = {
        "confirmed": "diagnosis.confirmed",
        "rejected": "diagnosis.rejected",
        "overridden": "diagnosis.overridden",
    }.get(decision, "diagnosis.reviewed")
    record.doctor_decision = payload.doctor_decision.strip()
    record.final_clinical_decision = payload.final_clinical_decision.strip()
    record.review_notes = payload.review_notes.strip()
    record.review_status = payload.review_status.strip() or "reviewed"
    record.reviewed_by_id = user.id
    record.reviewed_at = datetime.utcnow()
    record_audit_event(
        db,
        actor=user,
        action=action,
        resource_type="diagnosis",
        resource_id=record.id,
        metadata={
            "original_ai_prediction": record.prediction,
            "original_ai_confidence": record.confidence,
            "doctor_decision": record.doctor_decision,
            "final_clinical_decision": record.final_clinical_decision,
        },
        request=request,
    )
    if record.patient_id:
        notify_user(
            db,
            user_id=record.patient_id,
            notification_type="patient_report_update",
            title="Diagnosis review completed",
            message=f"Your {record.disease_key} diagnosis has a final clinical review.",
            diagnosis_id=record.id,
            severity="info",
        )
    patient_user = find_patient_user(db, record.patient_id, record.patient_email)
    refresh_stored_pdf_report(record, patient_user)
    db.add(record)
    db.commit()
    db.refresh(record)
    return _record_response(db, record)


@router.get("/notifications", response_model=list[NotificationResponse])
def notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Notification]:
    _doctor_required(user)
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc()).limit(100).all()


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def read_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Notification:
    _doctor_required(user)
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    mark_notification_read(notification)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/blockchain/verify/{diagnosis_id}")
def verify_blockchain_for_doctor(
    diagnosis_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _doctor_required(user)
    record = db.query(DiagnosisRecord).filter(DiagnosisRecord.id == diagnosis_id).first()
    if not record or not can_access_diagnosis(db, user, record):
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    result = verify_diagnosis(record, user)
    if not result.get("local_hash_match"):
        notify_user(
            db,
            user_id=user.id,
            notification_type="blockchain_verification_failure",
            title="Blockchain verification failure",
            message=f"Diagnosis {diagnosis_id} failed local blockchain hash verification.",
            diagnosis_id=diagnosis_id,
            severity="critical",
        )
    record_audit_event(db, actor=user, action="blockchain_record.verified", resource_type="diagnosis", resource_id=record.id, metadata=result, request=request)
    db.commit()
    return result


@router.get("/audit")
def doctor_audit_trail(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    _doctor_required(user)
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.actor_id == user.id)
        .order_by(AuditEvent.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": event.id,
            "doctor_id": event.actor_id,
            "action": event.action,
            "diagnosis_id": event.resource_id if event.resource_type == "diagnosis" else event.metadata_json.get("diagnosis_id"),
            "timestamp": event.created_at,
            "ip": event.metadata_json.get("ip"),
            "device": event.metadata_json.get("user_agent"),
            "metadata": event.metadata_json,
        }
        for event in events
    ]
