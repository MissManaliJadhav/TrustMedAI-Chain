from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.core.rbac import Role


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: Role


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: Role = Role.PATIENT


class UserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    is_verified: bool

    model_config = {"from_attributes": True}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    token: str


class PredictionRequest(BaseModel):
    disease_key: str
    patient_id: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)
    doctor_notes: str = ""


class ExplanationBundle(BaseModel):
    shap: dict[str, Any]
    lime: dict[str, Any]
    gradcam: dict[str, Any]
    captum: dict[str, Any]
    integrated_gradients: dict[str, Any]
    counterfactuals: list[dict[str, Any]]


class PredictionResponse(BaseModel):
    diagnosis_id: str
    disease_key: str
    prediction: str
    confidence: float
    metrics: dict[str, float]
    explanation: ExplanationBundle
    adversarial: dict[str, float]
    aecs: float
    trust_score: float
    dtei_components: dict[str, float]
    blockchain_hash: str
    ethereum_tx_hash: str | None = None
    fabric_tx_id: str | None = None
    created_at: datetime


class TrustPoint(BaseModel):
    timestamp: datetime
    disease_key: str
    dtei: float
    fidelity: float
    interpretability: float
    robustness: float
    blockchain_integrity: float
    compliance: float


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    message: str
