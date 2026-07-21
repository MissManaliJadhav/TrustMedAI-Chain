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
    public_patient_id: str | None = None
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
    patient_public_id: str | None = None
    disease_key: str
    prediction: str
    confidence: float
    metrics: dict[str, Any]
    explanation: ExplanationBundle
    adversarial: dict[str, Any]
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


class ContactResponse(BaseModel):
    id: str
    status: str
    message: str
    created_at: datetime


class CurrentUserResponse(BaseModel):
    id: str
    public_patient_id: str | None = None
    email: str
    full_name: str
    role: Role
    is_verified: bool
    hospital_id: str | None = None
    hospital_name: str | None = None
    created_at: datetime


class PatientProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    date_of_birth: str | None = Field(default=None, max_length=20)
    sex: str | None = Field(default=None, max_length=40)
    gender: str | None = Field(default=None, max_length=40)
    blood_group: str | None = Field(default=None, max_length=20)
    phone_number: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    emergency_contact_name: str | None = Field(default=None, max_length=255)
    emergency_contact_phone: str | None = Field(default=None, max_length=40)
    medical_information: str | None = Field(default=None, max_length=2000)
    allergies: str | None = Field(default=None, max_length=1000)
    medications: str | None = Field(default=None, max_length=1000)
    insurance: str | None = Field(default=None, max_length=1000)
    lifestyle: str | None = Field(default=None, max_length=1000)
    vaccination_history: str | None = Field(default=None, max_length=1000)


class PatientProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: Role
    patient_id: str
    registration_date: datetime
    last_profile_update: datetime | None = None
    profile_photo_url: str | None = None
    profile_photo_available: bool = False
    age: int | None = None
    profile_completion: int
    profile: dict[str, Any] = Field(default_factory=dict)


class DoctorProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    specialization: str | None = Field(default=None, max_length=160)
    qualifications: str | None = Field(default=None, max_length=1200)
    experience: str | None = Field(default=None, max_length=500)
    hospital_organization: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=40)
    contact_information: str | None = Field(default=None, max_length=1000)
    availability: str | None = Field(default=None, max_length=1000)


class DoctorProtectedProfileUpdate(BaseModel):
    doctor_id: str
    medical_registration_number: str | None = Field(default=None, max_length=120)
    profile_verification_status: str | None = Field(default=None, max_length=80)
    account_status: str | None = Field(default=None, max_length=80)


class DoctorProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    doctor_id: str
    role: Role
    profile_photo_url: str | None = None
    profile_photo_available: bool = False
    medical_registration_number: str | None = None
    specialization: str | None = None
    qualifications: str | None = None
    experience: str | None = None
    hospital_organization: str | None = None
    contact_information: str | None = None
    phone_number: str | None = None
    account_status: str
    last_login: datetime | None = None
    profile_verification_status: str
    created_at: datetime
    profile_updated_at: datetime | None = None


class DoctorSummaryResponse(BaseModel):
    total_assigned_patients: int
    pending_diagnosis_reviews: int
    high_risk_cases: int
    reviewed_diagnoses: int
    todays_new_cases: int
    average_ai_trust_score: float
    blockchain_verified_records: int
    unread_notifications: int


class NotificationResponse(BaseModel):
    id: str
    notification_type: str
    title: str
    message: str
    diagnosis_id: str | None = None
    severity: str
    is_read: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    read_at: datetime | None = None

    model_config = {"from_attributes": True}


class DoctorReviewRequest(BaseModel):
    doctor_decision: str = Field(min_length=2, max_length=80)
    final_clinical_decision: str = Field(min_length=2, max_length=120)
    review_notes: str = Field(default="", max_length=3000)
    review_status: str = Field(default="reviewed", max_length=40)


class DoctorNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=3000)


class DoctorPatientSummary(BaseModel):
    patient_id: str | None = None
    patient_public_id: str | None = None
    patient_name: str | None = None
    patient_email: str | None = None
    total_diagnoses: int
    active_cases: int
    latest_diagnosis_at: datetime | None = None
    average_trust_score: float


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
    patient_public_id: str | None = None
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
    review_status: str | None = None
    doctor_decision: str | None = None
    final_clinical_decision: str | None = None
    review_notes: str | None = None
    reviewed_by_id: str | None = None
    reviewed_at: datetime | None = None
    priority: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FederatedRoundCreateRequest(BaseModel):
    model_name: str = Field(default="trustmedai-risk-model", min_length=3, max_length=120)
    disease_key: str = Field(default="heart", min_length=2, max_length=80)
    min_clients: int = Field(default=2, ge=2, le=20)
    global_model_version: str = Field(default="v1", min_length=1, max_length=80)
    privacy_epsilon: float = Field(default=3.0, gt=0, le=10)
    secure_aggregation: bool = True
    differential_privacy: bool = True


class FederatedClientUpdateRequest(BaseModel):
    hospital_id: str
    sample_count: int = Field(ge=1, le=1_000_000)
    weights_delta: list[float] | None = Field(default=None, max_length=64)
    metrics: dict[str, float] = Field(default_factory=dict)
    privacy_epsilon_spent: float = Field(default=0.2, ge=0, le=10)


class FederatedSimulationRequest(BaseModel):
    model_name: str = Field(default="trustmedai-risk-model", min_length=3, max_length=120)
    disease_key: str = Field(default="heart", min_length=2, max_length=80)
    participating_hospitals: int = Field(default=4, ge=2, le=8)
