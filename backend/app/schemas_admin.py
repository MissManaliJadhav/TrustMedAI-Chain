"""
Admin Dashboard Schemas
Pydantic models for admin dashboard requests/responses
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ======================== USER MANAGEMENT SCHEMAS ========================

class UserStatisticsResponse(BaseModel):
    """User statistics for dashboard"""
    total: int
    active: int
    verified: int
    new_in_period: int
    role_distribution: dict[str, int]


class UserActivitySummary(BaseModel):
    """User activity summary"""
    user_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    last_activity: datetime | None = None
    recent_diagnoses: int = 0
    account_created: datetime


class UserBulkActionRequest(BaseModel):
    """Request for bulk user actions"""
    user_ids: list[str]
    action: str = Field(..., regex="^(activate|deactivate|verify|unverify)$")


# ======================== ANALYTICS SCHEMAS ========================

class DailyStatistic(BaseModel):
    """Daily statistics for charting"""
    date: str
    new_users: int
    new_diagnoses: int
    active_sessions: int = 0


class DiagnosisStatistics(BaseModel):
    """Diagnosis statistics"""
    total: int
    in_period: int
    average_trust_score: float
    average_confidence: float = 0.0


class HospitalStatistics(BaseModel):
    """Hospital statistics"""
    total: int
    verified: int
    unverified: int


class AnalyticsOverview(BaseModel):
    """Complete analytics overview"""
    users: UserStatisticsResponse
    diagnoses: DiagnosisStatistics
    hospitals: HospitalStatistics
    period_days: int


# ======================== AUDIT SCHEMAS ========================

class AuditLogEntry(BaseModel):
    """Audit log entry"""
    id: int
    actor_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogsResponse(BaseModel):
    """Audit logs response"""
    total: int
    logs: list[AuditLogEntry]


# ======================== SYSTEM SETTINGS SCHEMAS ========================

class BlockchainSettings(BaseModel):
    """Blockchain configuration"""
    ethereum_enabled: bool
    fabric_enabled: bool


class SystemSettings(BaseModel):
    """System settings"""
    project_name: str
    environment: str
    api_port: int
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    blockchain: BlockchainSettings


class MFAStatus(BaseModel):
    """MFA adoption status"""
    total_users: int
    admin_users: int
    mfa_enabled: int
    mfa_adoption_rate: str


# ======================== REPORT SCHEMAS ========================

class ReportRequest(BaseModel):
    """Request to generate report"""
    title: str
    report_type: str = Field(..., regex="^(users|diagnoses|hospitals|audit)$")
    format: str = Field("pdf", regex="^(pdf|csv|excel)$")
    date_range: str | None = None


class ReportResponse(BaseModel):
    """Generated report response"""
    report_id: str
    title: str
    generated_at: datetime
    download_url: str
    expires_at: datetime


# ======================== NOTIFICATION SCHEMAS ========================

class AnnouncementRequest(BaseModel):
    """Request to send announcement"""
    title: str = Field(..., min_length=5, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)
    target_role: str | None = None
    priority: str = "normal"


class NotificationResponse(BaseModel):
    """Notification response"""
    notification_id: str
    title: str
    status: str
    sent_at: datetime
    recipient_count: int


# ======================== DATA MANAGEMENT SCHEMAS ========================

class DiagnosisRecordSummary(BaseModel):
    """Diagnosis record summary for management"""
    id: str
    patient_name: str | None
    disease_key: str
    prediction: str
    confidence: float
    trust_score: float
    blockchain_hash: str | None
    created_at: datetime


class DataExportRequest(BaseModel):
    """Request to export data"""
    record_type: str = Field("all", regex="^(all|users|records|hospitals)$")
    format: str = Field("json", regex="^(json|csv)$")


class DataExportResponse(BaseModel):
    """Data export response"""
    export_type: str
    format: str
    record_count: int
    exported_at: datetime
    download_url: str


# ======================== HOSPITAL MANAGEMENT SCHEMAS ========================

class HospitalSummary(BaseModel):
    """Hospital information summary"""
    id: str
    name: str
    region: str
    reputation_score: float
    verified: bool
    user_count: int
    created_at: datetime


class HospitalVerificationRequest(BaseModel):
    """Request to verify hospital"""
    hospital_id: str
    notes: str | None = None


# ======================== DASHBOARD WIDGET SCHEMAS ========================

class DashboardWidget(BaseModel):
    """Dashboard widget configuration"""
    widget_id: str
    title: str
    type: str  # card, chart, table, stat
    data: dict[str, Any]
    refresh_interval: int = 300  # seconds


class DashboardLayout(BaseModel):
    """Admin dashboard layout configuration"""
    layout_id: str
    name: str
    widgets: list[DashboardWidget]
    created_at: datetime
    updated_at: datetime
