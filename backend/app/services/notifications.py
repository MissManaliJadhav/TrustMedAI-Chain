from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rbac import Role
from app.db.models import AuditEvent, DiagnosisRecord, Notification, User


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


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def adversarial_security_thresholds() -> dict[str, float]:
    return {
        "accuracy_degradation": settings.adversarial_accuracy_degradation_threshold,
        "high_impact_degradation": settings.adversarial_high_impact_degradation_threshold,
        "robustness_minimum": settings.adversarial_robustness_threshold,
        "trust_drop": settings.adversarial_trust_drop_threshold,
        "explanation_stability_minimum": settings.adversarial_explanation_stability_threshold,
        "input_perturbation": settings.adversarial_input_perturbation_threshold,
    }


def evaluate_adversarial_security_findings(adversarial: dict[str, Any]) -> list[dict[str, Any]]:
    thresholds = adversarial_security_thresholds()
    patient_attack = adversarial.get("patient_attack") if isinstance(adversarial.get("patient_attack"), dict) else {}
    attack_impact = adversarial.get("attack_impact") if isinstance(adversarial.get("attack_impact"), dict) else {}
    trust_evolution = adversarial.get("trust_evolution") if isinstance(adversarial.get("trust_evolution"), dict) else {}
    findings: list[dict[str, Any]] = []

    if patient_attack.get("status") == "Evaluated" or adversarial.get("attack_type") not in {None, "", "Not Evaluated"}:
        findings.append(
            {
                "code": "adversarial_attack_evaluated",
                "label": "Adversarial attack detected/evaluated",
                "severity": "warning",
                "value": patient_attack.get("attack_type") or adversarial.get("attack_type"),
                "threshold": "any evaluated attack",
            }
        )

    degradation = _as_float(attack_impact.get("accuracy_degradation"))
    if degradation is not None and degradation >= thresholds["accuracy_degradation"]:
        findings.append(
            {
                "code": "accuracy_degradation_significant",
                "label": "Model accuracy decreased significantly",
                "severity": "critical" if degradation >= thresholds["high_impact_degradation"] else "warning",
                "value": degradation,
                "threshold": thresholds["accuracy_degradation"],
            }
        )

    robustness = _as_float(adversarial.get("robustness_score"))
    if robustness is not None and robustness < thresholds["robustness_minimum"]:
        findings.append(
            {
                "code": "robustness_below_threshold",
                "label": "Robustness score below configured threshold",
                "severity": "critical" if robustness < 0.55 else "warning",
                "value": robustness,
                "threshold": thresholds["robustness_minimum"],
            }
        )

    trust_change = _as_float(trust_evolution.get("trust_change"))
    if trust_change is not None and trust_change <= -thresholds["trust_drop"]:
        findings.append(
            {
                "code": "dtei_decrease_significant",
                "label": "DTEI / Trust Score decreased significantly",
                "severity": "warning",
                "value": trust_change,
                "threshold": -thresholds["trust_drop"],
            }
        )

    if attack_impact.get("impact_level") == "High" or (
        degradation is not None and degradation >= thresholds["high_impact_degradation"]
    ):
        findings.append(
            {
                "code": "high_impact_attack",
                "label": "High-impact attack detected",
                "severity": "critical",
                "value": degradation,
                "threshold": thresholds["high_impact_degradation"],
            }
        )

    explanation_stability = _as_float(adversarial.get("explanation_stability"))
    if explanation_stability is not None and explanation_stability < thresholds["explanation_stability_minimum"]:
        findings.append(
            {
                "code": "explanation_unstable",
                "label": "Explanation became unstable",
                "severity": "warning",
                "value": explanation_stability,
                "threshold": thresholds["explanation_stability_minimum"],
            }
        )

    perturbation_rate = _as_float(patient_attack.get("perturbation_rate"))
    pixels_affected = _as_float(patient_attack.get("percentage_pixels_affected"))
    if patient_attack.get("prediction_changed") is True or any(
        value is not None and value >= thresholds["input_perturbation"]
        for value in (perturbation_rate, pixels_affected)
    ):
        findings.append(
            {
                "code": "suspicious_input_manipulation",
                "label": "Suspicious input manipulation detected",
                "severity": "critical" if patient_attack.get("prediction_changed") is True else "warning",
                "value": {
                    "prediction_changed": patient_attack.get("prediction_changed"),
                    "perturbation_rate": perturbation_rate,
                    "percentage_pixels_affected": pixels_affected,
                },
                "threshold": thresholds["input_perturbation"],
            }
        )

    return findings


def _security_recipients(db: Session, record: DiagnosisRecord) -> list[User]:
    recipients: dict[str, User] = {}
    if record.doctor_id:
        doctor = db.query(User).filter(User.id == record.doctor_id, User.is_active.is_(True)).first()
        if doctor:
            recipients[doctor.id] = doctor
    else:
        for doctor in db.query(User).filter(User.role == Role.DOCTOR.value, User.is_active.is_(True)).all():
            recipients[doctor.id] = doctor
    for admin in db.query(User).filter(
        User.role.in_([Role.SUPER_ADMIN.value, Role.HOSPITAL_ADMIN.value]),
        User.is_active.is_(True),
    ).all():
        recipients[admin.id] = admin
    return list(recipients.values())


def notify_adversarial_security_event(
    db: Session,
    record: DiagnosisRecord,
    adversarial: dict[str, Any],
    findings: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    findings = findings if findings is not None else evaluate_adversarial_security_findings(adversarial)
    if not findings:
        return []
    max_severity = "critical" if any(item.get("severity") == "critical" for item in findings) else "warning"
    title = "Adversarial security event detected"
    message = (
        f"{record.patient_name or 'A patient'} has a {record.disease_key} diagnosis with "
        f"{len(findings)} adversarial security finding(s). Clinical and system review is required."
    )
    metadata = {
        "disease_key": record.disease_key,
        "trust_score": record.trust_score,
        "attack_type": adversarial.get("patient_attack", {}).get("attack_type") if isinstance(adversarial.get("patient_attack"), dict) else adversarial.get("attack_type"),
        "thresholds": adversarial_security_thresholds(),
        "trust_recovery": adversarial.get("trust_recovery"),
        "findings": findings,
    }
    for user in _security_recipients(db, record):
        notify_user(
            db,
            user_id=user.id,
            notification_type="adversarial_security_event",
            title=title,
            message=message,
            diagnosis_id=record.id,
            severity=max_severity,
            metadata=metadata,
        )
    db.add(
        AuditEvent(
            actor_id=record.doctor_id,
            action="security.adversarial_event_detected",
            resource_type="diagnosis",
            resource_id=record.id,
            payload_hash=sha256(json.dumps(metadata, sort_keys=True, default=str).encode("utf-8")).hexdigest(),
            metadata_json=metadata,
        )
    )
    return findings


def mark_notification_read(notification: Notification) -> None:
    notification.is_read = True
    notification.read_at = datetime.utcnow()
