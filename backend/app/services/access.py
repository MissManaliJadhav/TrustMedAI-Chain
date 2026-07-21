from sqlalchemy.orm import Session

from app.core.rbac import Role
from app.db.models import DiagnosisRecord, User


def can_access_diagnosis(db: Session, user: User, record: DiagnosisRecord) -> bool:
    role = Role(user.role)
    if role == Role.SUPER_ADMIN:
        return False
    if role == Role.DOCTOR:
        return record.doctor_id in {None, user.id}
    if role == Role.PATIENT:
        return record.patient_id == user.id or (
            bool(record.patient_email) and record.patient_email.lower() == user.email.lower()
        )
    if role == Role.HOSPITAL_ADMIN and user.hospital_id:
        return False
    return False
