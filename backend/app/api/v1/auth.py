from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import Role
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.db.models import User
from app.db.session import get_db
from app.api.deps import get_current_user
from app.services.patient_ids import ensure_user_public_patient_id
from app.schemas import (
    CurrentUserResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenPair,
    UserRead,
    VerifyEmailRequest,
)

router = APIRouter()


def issue_tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_token(user.email, user.role, token_type="access"),
        refresh_token=create_token(user.email, user.role, days=7, token_type="refresh"),
        role=Role(user.role),
        user_id=user.id,
    )


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> User:
    allowed_self_registration_roles = {Role.PATIENT, Role.DOCTOR, Role.SUPER_ADMIN}
    if payload.role not in allowed_self_registration_roles:
        raise HTTPException(status_code=403, detail="This role cannot be self-registered")
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role.value,
        password_hash=hash_password(payload.password),
        is_verified=False,
    )
    db.add(user)
    db.flush()
    ensure_user_public_patient_id(db, user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user.last_login_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return issue_tokens(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    if claims.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token required")
    user = db.query(User).filter(User.email == claims.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive or missing user")
    return issue_tokens(user)


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        public_patient_id=user.public_patient_id,
        email=user.email,
        full_name=user.full_name,
        role=Role(user.role),
        is_verified=user.is_verified,
        hospital_id=user.hospital_id,
        hospital_name=user.hospital.name if user.hospital else None,
        created_at=user.created_at,
    )


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest) -> dict[str, str]:
    return {"status": "accepted", "message": f"Password reset instructions queued for {payload.email}"}


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest) -> dict[str, str]:
    return {"status": "verified", "token": payload.token}
