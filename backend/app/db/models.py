from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def uuid_str() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    hospital_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("hospitals.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    hospital = relationship("Hospital", back_populates="users")


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    region: Mapped[str] = mapped_column(String(120), default="Global")
    reputation_score: Mapped[float] = mapped_column(Float, default=0.82)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(160), index=True)
    resource_type: Mapped[str] = mapped_column(String(120))
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(128))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user or assistant
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(50), default="text")  # text, structured_data, assessment, recommendation
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)  # Store additional data like questions asked, confidence scores
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # When ORM loads an object from the database, populate an instance-level
    # `metadata` attribute so APIs that expect `message.metadata` continue to work
    # while avoiding the class-level name collision with SQLAlchemy's MetaData.
    from sqlalchemy.orm import reconstructor

    @reconstructor
    def _init_on_load(self) -> None:
        # set an instance attribute that shadows the class-level `metadata`
        self.metadata = self.metadata_json

    session = relationship("ChatSession", back_populates="messages")
