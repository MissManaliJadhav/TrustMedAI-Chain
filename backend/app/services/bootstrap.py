from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rbac import Role
from app.core.security import hash_password
from app.db.models import Hospital, User


def ensure_bootstrap_data(db: Session) -> None:
    hospital = db.query(Hospital).filter(Hospital.name == "TrustMedAI Reference Hospital").first()
    if not hospital:
        hospital = Hospital(name="TrustMedAI Reference Hospital", region="Global", verified=True)
        db.add(hospital)
        db.flush()

    admin = db.query(User).filter(User.email == settings.super_admin_email).first()
    if not admin:
        db.add(
            User(
                email=settings.super_admin_email,
                full_name="TrustMedAI Super Admin",
                role=Role.SUPER_ADMIN.value,
                password_hash=hash_password(settings.super_admin_password),
                is_verified=True,
                hospital_id=hospital.id,
            )
        )
    db.commit()
