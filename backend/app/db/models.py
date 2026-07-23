from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def uuid_str() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    public_patient_id: Mapped[str | None] = mapped_column(String(16), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    hospital_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("hospitals.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    profile_photo_object_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    profile_photo_content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    profile_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    hospital = relationship("Hospital", back_populates="users")


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    region: Mapped[str] = mapped_column(String(120), default="Global")
    reputation_score: Mapped[float] = mapped_column(Float, default=0.82)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    users = relationship("User", back_populates="hospital")


class DiagnosisRecord(Base):
    __tablename__ = "diagnosis_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    patient_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    patient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    patient_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    doctor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    disease_key: Mapped[str] = mapped_column(String(80), index=True)
    prediction: Mapped[str] = mapped_column(String(120))
    confidence: Mapped[float] = mapped_column(Float)
    input_modality: Mapped[str] = mapped_column(String(40), default="tabular")
    input_features: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    trust_score: Mapped[float] = mapped_column(Float)
    aecs: Mapped[float] = mapped_column(Float)
    blockchain_hash: Mapped[str] = mapped_column(String(128), index=True)
    ethereum_tx_hash: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    ethereum_block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ethereum_receipt_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ethereum_anchor_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    fabric_tx_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    fabric_anchor_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    blockchain_status: Mapped[dict] = mapped_column(JSON, default=dict)
    report_object_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    doctor_notes: Mapped[str] = mapped_column(Text, default="")
    review_status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    doctor_decision: Mapped[str | None] = mapped_column(String(80), nullable=True)
    final_clinical_decision: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    priority: Mapped[str] = mapped_column(String(40), default="routine", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    artifacts = relationship("DiagnosisArtifact", back_populates="diagnosis", cascade="all, delete-orphan")


class DiagnosisArtifact(Base):
    __tablename__ = "diagnosis_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    diagnosis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("diagnosis_records.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(40), index=True)
    object_path: Mapped[str] = mapped_column(String(512), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    diagnosis = relationship("DiagnosisRecord", back_populates="artifacts")


class TrustHistory(Base):
    __tablename__ = "trust_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    diagnosis_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("diagnosis_records.id"), nullable=True)
    disease_key: Mapped[str] = mapped_column(String(80), index=True)
    fidelity: Mapped[float] = mapped_column(Float)
    interpretability: Mapped[float] = mapped_column(Float)
    robustness: Mapped[float] = mapped_column(Float)
    blockchain_integrity: Mapped[float] = mapped_column(Float)
    compliance: Mapped[float] = mapped_column(Float)
    dtei: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(160), index=True)
    resource_type: Mapped[str] = mapped_column(String(120))
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(128))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    notification_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    diagnosis_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("diagnosis_records.id"), nullable=True)
    severity: Mapped[str] = mapped_column(String(40), default="info", index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User")
    diagnosis = relationship("DiagnosisRecord")


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), index=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class FederatedRound(Base):
    __tablename__ = "federated_rounds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    round_number: Mapped[int] = mapped_column(Integer, index=True)
    model_name: Mapped[str] = mapped_column(String(120), index=True)
    disease_key: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), default="collecting", index=True)
    strategy: Mapped[str] = mapped_column(String(80), default="FedAvg")
    min_clients: Mapped[int] = mapped_column(Integer, default=2)
    participating_clients: Mapped[int] = mapped_column(Integer, default=0)
    total_samples: Mapped[int] = mapped_column(Integer, default=0)
    previous_global_model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    global_model_version: Mapped[str] = mapped_column(String(80), default="v1")
    global_model_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    global_weights: Mapped[dict] = mapped_column(JSON, default=dict)
    aggregated_weights: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    global_trust: Mapped[float] = mapped_column(Float, default=0.0)
    previous_global_trust: Mapped[float | None] = mapped_column(Float, nullable=True)
    trust_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    privacy_config: Mapped[dict] = mapped_column(JSON, default=dict)
    update_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    updates = relationship("FederatedClientUpdate", back_populates="round", cascade="all, delete-orphan")


class FederatedClient(Base):
    __tablename__ = "federated_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    hospital_id: Mapped[str] = mapped_column(String(36), ForeignKey("hospitals.id"), index=True)
    disease_key: Mapped[str] = mapped_column(String(80), index=True)
    local_sample_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(40), default="idle")
    last_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    partition_strategy: Mapped[str] = mapped_column(String(40), default="iid")
    partition_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    hospital = relationship("Hospital")


class LocalTrainingRun(Base):
    __tablename__ = "local_training_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    round_id: Mapped[str] = mapped_column(String(36), ForeignKey("federated_rounds.id"), index=True)
    hospital_id: Mapped[str] = mapped_column(String(36), ForeignKey("hospitals.id"), index=True)
    model_update_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    local_trust: Mapped[float] = mapped_column(Float, default=0.0)
    trust_components: Mapped[dict] = mapped_column(JSON, default=dict)
    training_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    hospital = relationship("Hospital")
    round = relationship("FederatedRound")


class GlobalModelVersion(Base):
    __tablename__ = "global_model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    disease_key: Mapped[str] = mapped_column(String(80), index=True)
    round_number: Mapped[int] = mapped_column(Integer)
    version: Mapped[str] = mapped_column(String(80))
    model_path: Mapped[str] = mapped_column(String(512))
    model_fingerprint: Mapped[str] = mapped_column(String(128), index=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class FederatedTrustSnapshot(Base):
    __tablename__ = "federated_trust_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    round_id: Mapped[str] = mapped_column(String(36), ForeignKey("federated_rounds.id"), index=True)
    local_trust_values: Mapped[dict] = mapped_column(JSON, default=dict)
    global_trust: Mapped[float] = mapped_column(Float, default=0.0)
    trust_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class FederatedClientUpdate(Base):
    __tablename__ = "federated_client_updates"
    __table_args__ = (UniqueConstraint("round_id", "hospital_id", name="uq_federated_update_round_hospital"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    round_id: Mapped[str] = mapped_column(String(36), ForeignKey("federated_rounds.id"), index=True)
    hospital_id: Mapped[str] = mapped_column(String(36), ForeignKey("hospitals.id"), index=True)
    sample_count: Mapped[int] = mapped_column(Integer)
    weights_delta: Mapped[dict] = mapped_column(JSON, default=dict)
    model_update_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    model_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    privacy_report: Mapped[dict] = mapped_column(JSON, default=dict)
    payload_hash: Mapped[str] = mapped_column(String(128), index=True)
    accepted: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    round = relationship("FederatedRound", back_populates="updates")
    hospital = relationship("Hospital")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, completed, archived
    patient_profile: Mapped[dict] = mapped_column(JSON, default=dict)  # Store patient info collected
    medical_history: Mapped[dict] = mapped_column(JSON, default=dict)  # Store medical history
    symptoms_data: Mapped[dict] = mapped_column(JSON, default=dict)  # Store symptoms
    risk_assessment: Mapped[dict] = mapped_column(JSON, default=dict)  # Store risk scores
    possible_conditions: Mapped[dict] = mapped_column(JSON, default=dict)  # Store predicted conditions
    recommendations: Mapped[dict] = mapped_column(JSON, default=dict)  # Store recommendations
    conversation_stage: Mapped[str] = mapped_column(String(50), default="profile_collection")  # Track stage
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user or assistant
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(50), default="text")  # text, structured_data, assessment, recommendation
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)  # Store additional data like questions asked, confidence scores
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # When ORM loads an object from the database, populate an instance-level
    # `metadata` attribute so APIs that expect `message.metadata` continue to work
    # while avoiding the class-level name collision with SQLAlchemy's MetaData.
    from sqlalchemy.orm import reconstructor

    @reconstructor
    def _init_on_load(self) -> None:
        # set an instance attribute that shadows the class-level `metadata`
        self.metadata = self.metadata_json

    session = relationship("ChatSession", back_populates="messages")
