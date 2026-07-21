from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas import PatientProfileResponse, PatientProfileUpdate
from app.services.patient_ids import ensure_user_public_patient_id
from app.services.storage import read_object, store_object

router = APIRouter()

PROFILE_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
PROFILE_FIELDS = [
    "full_name",
    "date_of_birth",
    "sex",
    "gender",
    "blood_group",
    "phone_number",
    "address",
    "city",
    "state",
    "country",
    "emergency_contact_name",
    "emergency_contact_phone",
    "medical_information",
    "allergies",
    "medications",
    "insurance",
    "lifestyle",
    "vaccination_history",
]


def _clean_profile_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _calculate_age(date_of_birth: str | None) -> int | None:
    if not date_of_birth:
        return None
    try:
        born = date.fromisoformat(date_of_birth[:10])
    except ValueError:
        return None
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def _profile_completion(user: User, profile: dict[str, Any]) -> int:
    checks = [
        bool(user.profile_photo_object_path),
        bool(user.full_name),
        bool(user.email),
        bool(profile.get("date_of_birth")) or _calculate_age(profile.get("date_of_birth")) is not None,
        bool(profile.get("sex") or profile.get("gender")),
        bool(profile.get("blood_group")),
        bool(profile.get("phone_number")),
        bool(profile.get("address") or profile.get("city") or profile.get("state") or profile.get("country")),
        bool(profile.get("emergency_contact_name") or profile.get("emergency_contact_phone")),
        bool(profile.get("medical_information") or profile.get("allergies") or profile.get("medications")),
    ]
    return round(100 * sum(checks) / len(checks))


def _profile_response(user: User) -> PatientProfileResponse:
    profile = dict(user.profile or {})
    if user.full_name:
        profile["full_name"] = user.full_name
    profile["email"] = user.email
    age = _calculate_age(profile.get("date_of_birth"))
    return PatientProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        patient_id=user.public_patient_id or user.id,
        registration_date=user.created_at,
        last_profile_update=user.profile_updated_at,
        profile_photo_url="/patients/profile/photo" if user.profile_photo_object_path else None,
        profile_photo_available=bool(user.profile_photo_object_path),
        age=age,
        profile_completion=_profile_completion(user, profile),
        profile=profile,
    )


@router.get("/profile", response_model=PatientProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PatientProfileResponse:
    ensure_user_public_patient_id(db, user)
    db.commit()
    db.refresh(user)
    return _profile_response(user)


@router.put("/profile", response_model=PatientProfileResponse)
def update_profile(
    payload: PatientProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PatientProfileResponse:
    ensure_user_public_patient_id(db, user)
    profile = dict(user.profile or {})
    updates = payload.model_dump(exclude_unset=True)
    if "full_name" in updates and updates["full_name"]:
        user.full_name = updates["full_name"].strip()
    for field, value in updates.items():
        if field == "full_name":
            continue
        cleaned = _clean_profile_value(value)
        if cleaned is None:
            profile.pop(field, None)
        else:
            profile[field] = cleaned
    user.profile = profile
    user.profile_updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return _profile_response(user)


@router.post("/profile/photo", response_model=PatientProfileResponse)
async def upload_profile_photo(
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PatientProfileResponse:
    ensure_user_public_patient_id(db, user)
    content_type = photo.content_type or ""
    if content_type not in PROFILE_PHOTO_TYPES:
        raise HTTPException(status_code=422, detail="Upload a JPEG, PNG, or WebP profile photo.")
    content = await photo.read()
    if not content or len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="The profile photo must be between 1 byte and 5 MB.")
    suffix = Path(photo.filename or "profile-photo").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg" if content_type == "image/jpeg" else ".png"
    stored = store_object(f"profiles/{user.id}/photo-{uuid4().hex}{suffix}", content, content_type)
    user.profile_photo_object_path = stored.object_path
    user.profile_photo_content_type = content_type
    user.profile_updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return _profile_response(user)


@router.get("/profile/photo")
def profile_photo(user: User = Depends(get_current_user)) -> Response:
    if not user.profile_photo_object_path:
        raise HTTPException(status_code=404, detail="No profile photo has been uploaded.")
    content = read_object(user.profile_photo_object_path)
    return Response(content=content, media_type=user.profile_photo_content_type or "image/jpeg")
