from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.rbac import Role
from app.db.models import DiagnosisRecord, Notification, User


def is_high_risk(record: DiagnosisRecord) -> bool:
    prediction = (record.prediction or "").lower()
    return (
        record.confidence >= 0.85
        and not any(token in prediction for token in ("normal", "negative", "healthy", "controlled", "no_tumor"))
    ) or record.trust_score < 0.55 or "high" in prediction or "risk" in prediction


def review_status(record: DiagnosisRecord) -> str:
    return record.review_status or "pending"


def notify_user(
    db: Session,
    *,
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    diagnosis_id: str | None = None,
    severity: str = "info",
    metadata: dict[str, Any] | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        diagnosis_id=diagnosis_id,
        severity=severity,
        metadata_json=metadata or {},
    )
    db.add(notification)
    return notification


def notify_doctors_for_diagnosis(db: Session, record: DiagnosisRecord) -> None:
    doctors = db.query(User).filter(User.role == Role.DOCTOR.value, User.is_active.is_(True)).all()
    if record.doctor_id:
        assigned = db.query(User).filter(User.id == record.doctor_id, User.is_active.is_(True)).first()
        if assigned and assigned not in doctors:
            doctors.append(assigned)
    severity = "critical" if is_high_risk(record) else "info"
    for doctor in doctors:
        notify_user(
            db,
            user_id=doctor.id,
            notification_type="high_risk_case" if severity == "critical" else "new_diagnosis_review",
            title="High-risk case requires review" if severity == "critical" else "New diagnosis requires review",
            message=f"{record.patient_name or 'A patient'} has a {record.disease_key} diagnosis awaiting clinical review.",
            diagnosis_id=record.id,
            severity=severity,
            metadata={"confidence": record.confidence, "trust_score": record.trust_score},
        )


def mark_notification_read(notification: Notification) -> None:
    notification.is_read = True
    notification.read_at = datetime.utcnow()
