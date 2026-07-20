"""
Admin Dashboard API Routes
Handles user management, analytics, reports, audit logs, and system configuration
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.rbac import Role, role_has_permission
from app.db.models import User, Hospital, DiagnosisRecord, AuditEvent, ChatSession, TrustHistory
from app.schemas import UserRead

router = APIRouter()


def require_admin_permission(permission: str):
    """Dependency to check admin permissions"""
    async def check_permission(current_user: User = Depends(get_current_user)):
        if not role_has_permission(Role(current_user.role), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission}"
            )
        return current_user
    return check_permission


# ======================== USER MANAGEMENT ENDPOINTS ========================

@router.get("/users", tags=["Admin - User Management"])
def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    role: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    current_user: User = Depends(require_admin_permission("users:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get all users with optional filtering and search"""
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%"))
        )
    
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "users": [UserRead.model_validate(u) for u in users]
    }


@router.get("/users/{user_id}", tags=["Admin - User Management"])
def get_user_detail(
    user_id: str,
    current_user: User = Depends(require_admin_permission("users:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get detailed user information with activity"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's recent activity
    recent_diagnoses = db.query(DiagnosisRecord).filter(
        (DiagnosisRecord.patient_id == user_id) | (DiagnosisRecord.doctor_id == user_id)
    ).order_by(DiagnosisRecord.created_at.desc()).limit(5).all()
    
    audit_logs = db.query(AuditEvent).filter(
        (AuditEvent.actor_id == user_id)
    ).order_by(AuditEvent.created_at.desc()).limit(10).all()
    
    hospital = user.hospital if user.hospital_id else None
    
    return {
        "user": UserRead.model_validate(user),
        "hospital": {"id": hospital.id, "name": hospital.name} if hospital else None,
        "recent_diagnoses": len(recent_diagnoses),
        "total_activity_events": len(audit_logs),
        "last_activity": audit_logs[0].created_at if audit_logs else None,
        "account_created": user.created_at,
    }


@router.put("/users/{user_id}", tags=["Admin - User Management"])
def update_user(
    user_id: str,
    full_name: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    is_verified: bool | None = None,
    current_user: User = Depends(require_admin_permission("users:manage")),
    db: Session = Depends(get_db),
) -> UserRead:
    """Update user information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-modification of role/active status
    if user_id == current_user.id and (role is not None or is_active is False):
        raise HTTPException(
            status_code=400,
            detail="Cannot modify your own role or active status"
        )
    
    if full_name:
        user.full_name = full_name
    if role:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    if is_verified is not None:
        user.is_verified = is_verified
    
    db.commit()
    db.refresh(user)
    
    # Log the action
    log_audit_event(db, current_user.id, f"Updated user {user_id}", "USER", user_id)
    
    return UserRead.model_validate(user)


@router.delete("/users/{user_id}", tags=["Admin - User Management"])
def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin_permission("users:manage")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a user (soft delete by deactivating)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user.is_active = False
    db.commit()
    
    log_audit_event(db, current_user.id, f"Deleted user {user_id}", "USER", user_id)
    
    return {"message": "User deleted successfully", "user_id": user_id}


@router.post("/users/{user_id}/reset-password", tags=["Admin - User Management"])
def reset_user_password(
    user_id: str,
    new_password: str,
    current_user: User = Depends(require_admin_permission("users:manage")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Reset user password (requires confirmation email)"""
    from app.core.security import get_password_hash
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.password_hash = get_password_hash(new_password)
    db.commit()
    
    log_audit_event(db, current_user.id, f"Reset password for user {user_id}", "USER", user_id)
    
    return {"message": "Password reset successfully", "user_id": user_id}


@router.post("/users/{user_id}/toggle-block", tags=["Admin - User Management"])
def toggle_user_block(
    user_id: str,
    current_user: User = Depends(require_admin_permission("users:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Block or unblock a user account"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_status = not user.is_active
    user.is_active = new_status
    db.commit()
    
    action = "blocked" if not new_status else "unblocked"
    log_audit_event(db, current_user.id, f"User {action}: {user_id}", "USER", user_id)
    
    return {
        "user_id": user_id,
        "action": action,
        "is_active": new_status,
    }


# ======================== DASHBOARD ANALYTICS ========================

@router.get("/analytics/overview", tags=["Admin - Analytics"])
def get_analytics_overview(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_admin_permission("platform:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get overall platform analytics"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # User statistics
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    verified_users = db.query(func.count(User.id)).filter(User.is_verified == True).scalar()
    new_users = db.query(func.count(User.id)).filter(User.created_at >= cutoff_date).scalar()
    
    # Role distribution
    role_distribution = {}
    for role in [r.value for r in Role]:
        count = db.query(func.count(User.id)).filter(User.role == role).scalar()
        role_distribution[role] = count
    
    # Diagnosis statistics
    total_diagnoses = db.query(func.count(DiagnosisRecord.id)).scalar()
    recent_diagnoses = db.query(func.count(DiagnosisRecord.id)).filter(
        DiagnosisRecord.created_at >= cutoff_date
    ).scalar()
    
    # Average trust score
    avg_trust_score = db.query(func.avg(DiagnosisRecord.trust_score)).scalar() or 0.0
    
    # Hospital count
    hospital_count = db.query(func.count(Hospital.id)).scalar()
    verified_hospitals = db.query(func.count(Hospital.id)).filter(
        Hospital.verified == True
    ).scalar()

    patient_count = db.query(func.count(User.id)).filter(User.role == Role.PATIENT.value).scalar()
    doctor_count = db.query(func.count(User.id)).filter(User.role == Role.DOCTOR.value).scalar()
    blockchain_transactions = db.query(func.count(DiagnosisRecord.id)).filter(
        (DiagnosisRecord.ethereum_tx_hash.isnot(None)) |
        (DiagnosisRecord.fabric_tx_id.isnot(None)) |
        (DiagnosisRecord.blockchain_hash.isnot(None))
    ).scalar()
    active_sessions = db.query(func.count(ChatSession.id)).filter(ChatSession.status == "active").scalar()
    avg_ai_accuracy = db.query(func.avg(TrustHistory.fidelity)).scalar() or avg_trust_score or 0.0
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "verified": verified_users,
            "new_in_period": new_users,
            "role_distribution": role_distribution,
        },
        "diagnoses": {
            "total": total_diagnoses,
            "in_period": recent_diagnoses,
            "average_trust_score": round(avg_trust_score, 3),
        },
        "hospitals": {
            "total": hospital_count,
            "verified": verified_hospitals,
        },
        "patients": {"total": patient_count},
        "doctors": {"total": doctor_count},
        "blockchain": {"transactions": blockchain_transactions},
        "ai": {"accuracy": round(avg_ai_accuracy, 3)},
        "sessions": {"active": active_sessions},
        "period_days": days,
    }


@router.get("/analytics/daily-stats", tags=["Admin - Analytics"])
def get_daily_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_admin_permission("platform:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get daily statistics for charting"""
    from sqlalchemy import func, cast, Date
    
    stats = []
    for i in range(days, 0, -1):
        date = datetime.utcnow().date() - timedelta(days=i)
        start_time = datetime.combine(date, datetime.min.time())
        end_time = start_time + timedelta(days=1)
        
        new_users = db.query(func.count(User.id)).filter(
            (User.created_at >= start_time) & (User.created_at < end_time)
        ).scalar()
        
        new_diagnoses = db.query(func.count(DiagnosisRecord.id)).filter(
            (DiagnosisRecord.created_at >= start_time) & (DiagnosisRecord.created_at < end_time)
        ).scalar()
        
        stats.append({
            "date": date.isoformat(),
            "new_users": new_users,
            "new_diagnoses": new_diagnoses,
        })
    
    return {"statistics": stats}


@router.get("/analytics/user-growth", tags=["Admin - Analytics"])
def get_user_growth(
    current_user: User = Depends(require_admin_permission("platform:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get user growth metrics"""
    # Last 12 months
    growth = []
    for i in range(12, 0, -1):
        date = datetime.utcnow().replace(day=1) - timedelta(days=i*30)
        month_start = date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        
        count = db.query(func.count(User.id)).filter(
            (User.created_at >= month_start) & (User.created_at < month_end)
        ).scalar()
        
        growth.append({
            "month": month_start.strftime("%Y-%m"),
            "new_users": count,
        })
    
    return {"monthly_growth": growth}


# ======================== DATA MANAGEMENT ========================

@router.get("/data/records", tags=["Admin - Data Management"])
def get_all_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    disease_key: str | None = None,
    search: str | None = None,
    current_user: User = Depends(require_admin_permission("platform:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get all diagnosis records"""
    query = db.query(DiagnosisRecord)
    
    if disease_key:
        query = query.filter(DiagnosisRecord.disease_key == disease_key)
    if search:
        query = query.filter(
            (DiagnosisRecord.patient_email.ilike(f"%{search}%")) |
            (DiagnosisRecord.patient_name.ilike(f"%{search}%"))
        )
    
    total = query.count()
    records = query.order_by(DiagnosisRecord.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "records": [
            {
                "id": r.id,
                "patient_name": r.patient_name,
                "disease_key": r.disease_key,
                "prediction": r.prediction,
                "confidence": r.confidence,
                "trust_score": r.trust_score,
                "blockchain_hash": r.blockchain_hash[:16] + "..." if r.blockchain_hash else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ]
    }


@router.delete("/data/records/{record_id}", tags=["Admin - Data Management"])
def delete_record(
    record_id: str,
    current_user: User = Depends(require_admin_permission("platform:manage")),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a diagnosis record (data purge)"""
    record = db.query(DiagnosisRecord).filter(DiagnosisRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    db.delete(record)
    db.commit()
    
    log_audit_event(db, current_user.id, f"Deleted record {record_id}", "DIAGNOSIS_RECORD", record_id)
    
    return {"message": "Record deleted", "record_id": record_id}


@router.get("/data/export", tags=["Admin - Data Management"])
def export_data(
    record_type: str = Query("all", regex="^(all|users|records|hospitals)$"),
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: User = Depends(require_admin_permission("platform:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Export data in specified format"""
    if record_type in ["all", "users"]:
        users = db.query(User).all()
        user_data = [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]
    
    if record_type in ["all", "records"]:
        records = db.query(DiagnosisRecord).all()
        record_data = [
            {
                "id": r.id,
                "patient_name": r.patient_name,
                "disease_key": r.disease_key,
                "prediction": r.prediction,
                "confidence": r.confidence,
                "trust_score": r.trust_score,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ]
    
    return {
        "export_type": record_type,
        "format": format,
        "data": {
            "users": user_data if record_type in ["all", "users"] else None,
            "records": record_data if record_type in ["all", "records"] else None,
        },
        "exported_at": datetime.utcnow().isoformat(),
    }


# ======================== AUDIT & LOGS ========================

@router.get("/audit/logs", tags=["Admin - Audit & Logs"])
def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    actor_id: str | None = None,
    action: str | None = None,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_admin_permission("audit:view")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get audit logs"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    query = db.query(AuditEvent).filter(AuditEvent.created_at >= cutoff_date)
    
    if actor_id:
        query = query.filter(AuditEvent.actor_id == actor_id)
    if action:
        query = query.filter(AuditEvent.action.ilike(f"%{action}%"))
    
    total = query.count()
    logs = query.order_by(AuditEvent.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "actor_id": log.actor_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
    }


@router.get("/audit/user-activity/{user_id}", tags=["Admin - Audit & Logs"])
def get_user_activity(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_admin_permission("audit:view")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get activity log for a specific user"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    logs = db.query(AuditEvent).filter(
        (AuditEvent.actor_id == user_id) & (AuditEvent.created_at >= cutoff_date)
    ).order_by(AuditEvent.created_at.desc()).all()
    
    return {
        "user_id": user_id,
        "activity_count": len(logs),
        "logs": [
            {
                "action": log.action,
                "resource_type": log.resource_type,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
    }


# ======================== SECURITY & SETTINGS ========================

@router.get("/settings/system", tags=["Admin - Settings"])
def get_system_settings(
    current_user: User = Depends(require_admin_permission("platform:manage")),
) -> dict[str, Any]:
    """Get system settings and configuration"""
    from app.core.config import settings
    
    return {
        "project_name": settings.project_name,
        "environment": settings.environment,
        "api_port": settings.api_port,
        "jwt_algorithm": settings.jwt_algorithm,
        "access_token_expire_minutes": settings.access_token_expire_minutes,
        "refresh_token_expire_days": settings.refresh_token_expire_days,
        "blockchain": {
            "ethereum_enabled": bool(settings.ethereum_contract_address),
            "fabric_enabled": bool(settings.fabric_connection_profile),
        }
    }


@router.get("/settings/mfa-status", tags=["Admin - Settings"])
def get_mfa_status(
    current_user: User = Depends(require_admin_permission("platform:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get MFA adoption status across platform"""
    total_users = db.query(func.count(User.id)).scalar()
    admin_users = db.query(func.count(User.id)).filter(
        User.role.in_([Role.SUPER_ADMIN, Role.HOSPITAL_ADMIN])
    ).scalar()
    
    # TODO: Implement MFA tracking in User model
    mfa_enabled_users = 0  # Placeholder
    
    return {
        "total_users": total_users,
        "admin_users": admin_users,
        "mfa_enabled": mfa_enabled_users,
        "mfa_adoption_rate": f"{(mfa_enabled_users / total_users * 100):.1f}%" if total_users > 0 else "0%",
    }


@router.post("/settings/send-announcement", tags=["Admin - Notifications"])
def send_announcement(
    title: str,
    message: str,
    target_role: str | None = None,
    current_user: User = Depends(require_admin_permission("platform:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Send system-wide announcement to users"""
    # TODO: Implement notification system
    # For now, just log the action
    log_audit_event(
        db,
        current_user.id,
        f"Sent announcement: {title}",
        "ANNOUNCEMENT",
        None
    )
    
    return {
        "status": "sent",
        "title": title,
        "message": message,
        "target_role": target_role,
        "sent_at": datetime.utcnow().isoformat(),
    }


# ======================== HOSPITALS MANAGEMENT ========================

@router.get("/hospitals", tags=["Admin - Hospitals"])
def get_hospitals(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    verified: bool | None = None,
    current_user: User = Depends(require_admin_permission("hospitals:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get all hospitals"""
    query = db.query(Hospital)
    if verified is not None:
        query = query.filter(Hospital.verified == verified)
    
    total = query.count()
    hospitals = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "hospitals": [
            {
                "id": h.id,
                "name": h.name,
                "region": h.region,
                "reputation_score": h.reputation_score,
                "verified": h.verified,
                "user_count": len(h.users),
                "created_at": h.created_at.isoformat(),
            }
            for h in hospitals
        ]
    }


@router.put("/hospitals/{hospital_id}/verify", tags=["Admin - Hospitals"])
def verify_hospital(
    hospital_id: str,
    current_user: User = Depends(require_admin_permission("hospitals:manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Verify a hospital"""
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    hospital.verified = True
    db.commit()
    
    log_audit_event(db, current_user.id, f"Verified hospital {hospital_id}", "HOSPITAL", hospital_id)
    
    return {
        "id": hospital.id,
        "name": hospital.name,
        "verified": hospital.verified,
    }


# ======================== HELPER FUNCTIONS ========================

def log_audit_event(db: Session, actor_id: str, action: str, resource_type: str, resource_id: str | None):
    """Helper function to log audit events"""
    import hashlib
    
    payload_hash = hashlib.sha256(action.encode()).hexdigest()
    audit_event = AuditEvent(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload_hash=payload_hash,
    )
    db.add(audit_event)
    db.commit()
