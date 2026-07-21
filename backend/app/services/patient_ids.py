from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.rbac import Role
from app.db.models import DiagnosisRecord, User

PATIENT_ID_PREFIX = "PAT-"
PATIENT_ID_WIDTH = 6


def _sequence(public_patient_id: str | None) -> int:
    if not public_patient_id or not public_patient_id.startswith(PATIENT_ID_PREFIX):
        return 0
    try:
        return int(public_patient_id.removeprefix(PATIENT_ID_PREFIX))
    except ValueError:
        return 0


def format_public_patient_id(sequence: int) -> str:
    return f"{PATIENT_ID_PREFIX}{sequence:0{PATIENT_ID_WIDTH}d}"


def next_public_patient_id(db: Session) -> str:
    existing = db.query(User.public_patient_id).filter(User.public_patient_id.isnot(None)).all()
    next_sequence = max((_sequence(value) for (value,) in existing), default=0) + 1
    while db.query(User).filter(User.public_patient_id == format_public_patient_id(next_sequence)).first():
        next_sequence += 1
    return format_public_patient_id(next_sequence)


def ensure_user_public_patient_id(db: Session, user: User) -> str | None:
    if user.role != Role.PATIENT.value:
        return None
    if not user.public_patient_id:
        user.public_patient_id = next_public_patient_id(db)
        db.add(user)
        db.flush()
    return user.public_patient_id


def assign_missing_public_patient_ids(db: Session) -> None:
    patients = (
        db.query(User)
        .filter(User.role == Role.PATIENT.value, User.public_patient_id.is_(None))
        .order_by(User.created_at.asc(), User.id.asc())
        .all()
    )
    for patient in patients:
        ensure_user_public_patient_id(db, patient)
    if patients:
        db.commit()


def find_patient_user(db: Session, identifier: str | None = None, email: str | None = None) -> User | None:
    value = (identifier or "").strip()
    query = db.query(User).filter(User.role == Role.PATIENT.value)
    if value:
        user = query.filter((User.id == value) | (User.public_patient_id == value)).first()
        if user:
            return user
    if email:
        return query.filter(User.email == email.strip().lower()).first()
    return None


def public_patient_id_for_record(db: Session, record: DiagnosisRecord) -> str | None:
    patient = find_patient_user(db, record.patient_id, record.patient_email)
    return patient.public_patient_id if patient else None
