from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.core.rbac import Role


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: Role
    user_id: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    # Login must accept already-provisioned local-development accounts such as
    # the configurable bootstrap admin; signup still requires a deliverable shape.
    email: str = Field(min_length=3, max_length=255)
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
    patient_name: str = Field(min_length=2, max_length=255)
    patient_email: EmailStr
    features: dict[str, Any] = Field(default_factory=dict)
    doctor_notes: str = ""


class ExplanationBundle(BaseModel):
    shap: dict[str, Any]
    lime: dict[str, Any]
    gradcam: dict[str, Any]
    captum: dict[str, Any]
    integrated_gradients: dict[str, Any]
    counterfactuals: list[dict[str, Any]]


class DiagnosisArtifactResponse(BaseModel):
    id: str
    kind: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime

    model_config = {"from_attributes": True}


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
    blockchain_status: dict[str, Any] = Field(default_factory=dict)
    input_modality: str
    artifacts: list[DiagnosisArtifactResponse] = Field(default_factory=list)
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


# Chatbot Schemas

class PatientProfileData(BaseModel):
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    height: str | None = None
    weight: str | None = None
    blood_group: str | None = None
    country: str | None = None
    occupation: str | None = None


class MedicalHistoryData(BaseModel):
    existing_diseases: list[str] = []
    previous_surgeries: list[str] = []
    allergies: list[str] = []
    current_medications: list[str] = []
    family_history: list[str] = []
    smoking_status: str | None = None
    alcohol_consumption: str | None = None
    pregnancy_status: str | None = None


class SymptomData(BaseModel):
    primary_symptom: str | None = None
    duration: str | None = None
    severity: int | None = None  # 1-10 scale
    additional_symptoms: list[str] = []
    triggers: list[str] = []
    relieving_factors: list[str] = []


class RiskAssessmentData(BaseModel):
    age_risk: str | None = None  # LOW, MODERATE, HIGH
    lifestyle_risk: str | None = None
    family_history_risk: str | None = None
    chronic_disease_risk: str | None = None
    overall_risk_score: str | None = None
    emergency_risk: str | None = None


class PossibleCondition(BaseModel):
    condition: str
    probability: float
    confidence_level: str
    supporting_symptoms: list[str]
    missing_information: list[str]


class RecommendationData(BaseModel):
    immediate_actions: list[str] = []
    monitoring_advice: list[str] = []
    lifestyle_advice: list[str] = []
    diet_suggestions: list[str] = []
    exercise_suggestions: list[str] = []
    specialist_recommendation: str | None = None
    diagnostic_tests: list[str] = []


class ChatMessageRequest(BaseModel):
    session_id: str | None = None
    content: str
    message_type: str = "text"


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    message_type: str
    metadata: dict[str, Any] = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionData(BaseModel):
    id: str
    title: str
    status: str
    conversation_stage: str
    patient_profile: PatientProfileData
    medical_history: MedicalHistoryData
    symptoms_data: SymptomData
    risk_assessment: RiskAssessmentData
    possible_conditions: list[PossibleCondition] = []
    recommendations: RecommendationData
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    status: str
    conversation_stage: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionCreateRequest(BaseModel):
    title: str = "New Chat"


class ExportRequest(BaseModel):
    """Request schema for exporting chat session as diagnosis."""
    disease_key: str = "general_health_assessment"


class ChatAssessmentResponse(BaseModel):
    session_id: str
    patient_summary: PatientProfileData
    symptoms_summary: SymptomData
    risk_assessment: RiskAssessmentData
    possible_conditions: list[PossibleCondition]
    recommendations: RecommendationData
    medical_disclaimer: str = (
        "This assessment is informational only and not a medical diagnosis. "
        "Please consult a licensed healthcare professional for medical advice."
    )


class DiagnosisRecordResponse(BaseModel):
    """Response schema for diagnosis records with role-based filtering."""
    diagnosis_id: str
    patient_id: str | None
    patient_name: str | None = None
    patient_email: str | None = None
    doctor_id: str | None
    disease_key: str
    prediction: str
    confidence: float
    input_modality: str = "tabular"
    artifacts: list[DiagnosisArtifactResponse] = Field(default_factory=list)
    trust_score: float
    blockchain_hash: str
    ethereum_tx_hash: str | None = None
    fabric_tx_id: str | None = None
    doctor_notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
