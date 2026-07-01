from sqlalchemy.orm import Session

from app.core.rbac import Role
from app.db.models import DiagnosisRecord, User


def can_access_diagnosis(db: Session, user: User, record: DiagnosisRecord) -> bool:
    role = Role(user.role)
    if role == Role.SUPER_ADMIN:
        return True
    if role == Role.DOCTOR:
        return record.doctor_id == user.id
    if role == Role.PATIENT:
        return record.patient_id == user.id or (
            bool(record.patient_email) and record.patient_email.lower() == user.email.lower()
        )
    if role == Role.HOSPITAL_ADMIN and user.hospital_id:
        hospital_user_ids = {
            row[0]
            for row in db.query(User.id).filter(User.hospital_id == user.hospital_id).all()
        }
        return record.doctor_id in hospital_user_ids or record.patient_id in hospital_user_ids
    return False
