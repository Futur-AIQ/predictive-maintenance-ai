from datetime import datetime
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, EmailStr, field_validator

from src.models.user import UserRole
from src.models.work_order import Severity, WorkOrderStatus


# ── Generic Pagination ────────────────────────────────────────────────────────
T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int


# ── Auth / User ───────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.engineer

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    type: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Equipment ─────────────────────────────────────────────────────────────────
class SensorReadings(BaseModel):
    temperature: Optional[float] = None
    vibration: Optional[float] = None
    pressure: Optional[float] = None
    speed_rpm: Optional[float] = None
    oil_level: Optional[float] = None


class HealthStatusResponse(BaseModel):
    equipment_id: str
    health_score: float          # 0.0 – 100.0
    rul: Optional[int] = None    # Remaining Useful Life in cycles
    status: str                  # OK | WARNING | CRITICAL
    sensor_readings: SensorReadings
    last_updated: datetime


class EquipmentListItem(BaseModel):
    equipment_id: str
    equipment_type: str          # turbofan | pump | compressor
    health_score: float
    rul: Optional[int] = None
    status: str
    last_fault_code: Optional[str] = None
    last_updated: datetime


# ── Diagnostic ────────────────────────────────────────────────────────────────
class DiagnosticRequest(BaseModel):
    equipment_id: str
    query: str


class DiagnosticResponse(BaseModel):
    session_id: str
    equipment_id: str
    diagnosis: Optional[str] = None
    root_cause: Optional[str] = None
    recommended_action: Optional[str] = None
    confidence_score: Optional[float] = None
    severity: Optional[str] = None
    work_order_id: Optional[str] = None
    work_order_created: bool = False
    sources_used: Optional[List[str]] = None
    agent_steps: Optional[List[str]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Work Orders ───────────────────────────────────────────────────────────────
class WorkOrderResponse(BaseModel):
    id: int
    work_order_id: str
    equipment_id: str
    fault_code: Optional[str] = None
    fault_description: str
    severity: Severity
    status: WorkOrderStatus
    recommended_action: Optional[str] = None
    assigned_to: Optional[int] = None
    created_by: int
    priority_score: Optional[float] = None
    estimated_completion_hours: Optional[float] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkOrderStatusUpdate(BaseModel):
    status: WorkOrderStatus


# ── Evaluation ────────────────────────────────────────────────────────────────
class EvaluationReport(BaseModel):
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    timestamp: datetime
    sample_count: int = 0
