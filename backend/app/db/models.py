from datetime import datetime
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
    doctor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    disease_key: Mapped[str] = mapped_column(String(80), index=True)
    prediction: Mapped[str] = mapped_column(String(120))
    confidence: Mapped[float] = mapped_column(Float)
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
    report_object_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    doctor_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
