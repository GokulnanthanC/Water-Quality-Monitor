from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Any, Dict
import re

# ================= USER & AUTH SCHEMAS =================

class UserCreate(BaseModel):
    """Schema for user registration"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    role: Optional[str] = "citizen"
    organization_id: Optional[int] = None
    org_role: Optional[str] = "field_worker"
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Enforce strong password requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty or whitespace')
        return ' '.join(v.split())


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class OrgMembershipBrief(BaseModel):
    organization_id: int
    organization_name: str
    role: str
    status: str

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    organization_id: Optional[int] = None
    org_role: Optional[str] = None
    organizations: Optional[List[OrgMembershipBrief]] = []
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


# ================= ORGANIZATION SCHEMAS =================

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    mission: Optional[str] = None
    geographic_focus: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    mission: Optional[str] = None
    geographic_focus: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class OrganizationMemberResponse(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    role: str
    status: str
    joined_at: Optional[str] = None

    class Config:
        from_attributes = True


class OrganizationResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    mission: Optional[str] = None
    geographic_focus: Optional[str] = None
    email: str
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: str
    created_at: Optional[str] = None
    member_count: Optional[int] = 0

    class Config:
        from_attributes = True


class MemberAdd(BaseModel):
    email: EmailStr
    role: str = Field(default="field_worker", pattern="^(admin|field_worker|viewer)$")


class MemberUpdateRole(BaseModel):
    role: str = Field(..., pattern="^(admin|field_worker|viewer)$")


# ================= DATA ACCESS & AUDIT SCHEMAS =================

class DataAccessPolicyCreate(BaseModel):
    resource_type: str
    resource_id: int
    visibility: str = Field(default="private", pattern="^(private|partner|public)$")
    partner_organization_ids: Optional[List[int]] = []


class DataAccessPartnerResponse(BaseModel):
    id: int
    organization_id: int
    permission: str

    class Config:
        from_attributes = True


class DataAccessPolicyResponse(BaseModel):
    id: int
    resource_type: str
    resource_id: int
    owner_organization_id: int
    visibility: str
    partners: List[DataAccessPartnerResponse] = []

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    action: str
    resource_type: str
    resource_id: Optional[int] = None
    ip_address: Optional[str] = None
    timestamp: str
    metadata_json: Optional[str] = None

    class Config:
        from_attributes = True


# ================= INCIDENT & COLLABORATION SCHEMAS =================

class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    severity: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    status: Optional[str] = Field(None, pattern="^(OPEN|ASSIGNED|IN_PROGRESS|RESOLVED|CLOSED)$")


class IncidentTaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    assigned_to_organization_id: Optional[int] = None
    due_date: Optional[str] = None


class IncidentTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(PENDING|IN_PROGRESS|COMPLETED|CANCELLED)$")
    assigned_to_user_id: Optional[int] = None
    due_date: Optional[str] = None


class IncidentTaskResponse(BaseModel):
    id: int
    incident_id: int
    title: str
    description: Optional[str] = None
    status: str
    assigned_to_user_id: Optional[int] = None
    assigned_user_name: Optional[str] = None
    due_date: Optional[str] = None
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True


class IncidentActionCreate(BaseModel):
    description: str = Field(..., min_length=5)


class IncidentActionResponse(BaseModel):
    id: int
    incident_id: int
    performed_by: int
    performer_name: Optional[str] = None
    description: str
    timestamp: str

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    station_id: Optional[str] = None


class CommentResponse(BaseModel):
    id: int
    incident_id: Optional[int] = None
    station_id: Optional[str] = None
    user_id: int
    user_name: Optional[str] = None
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    message: str
    created_at: str

    class Config:
        from_attributes = True


class IncidentResponse(BaseModel):
    id: int
    organization_id: int
    organization_name: Optional[str] = None
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    reported_by: int
    reporter_name: Optional[str] = None
    title: str
    description: str
    severity: str
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    task_count: Optional[int] = 0
    comment_count: Optional[int] = 0

    class Config:
        from_attributes = True


# ================= CALENDAR SCHEMAS =================

class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    start_time: str
    end_time: str
    event_type: str = Field(default="SAMPLING", pattern="^(SAMPLING|INSPECTION|CALIBRATION|MEETING|FIELD_VISIT)$")


class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(SCHEDULED|IN_PROGRESS|COMPLETED|CANCELLED)$")


class CalendarEventResponse(BaseModel):
    id: int
    organization_id: int
    organization_name: Optional[str] = None
    created_by: int
    creator_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    start_time: str
    end_time: str
    event_type: str
    status: str

    class Config:
        from_attributes = True


# ================= EQUIPMENT SCHEMAS =================

class EquipmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    equipment_type: str
    serial_number: Optional[str] = None
    location: Optional[str] = None
    calibration_date: Optional[str] = None
    next_calibration_date: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    equipment_type: Optional[str] = None
    serial_number: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(AVAILABLE|IN_USE|MAINTENANCE|SHARED|RETIRED)$")
    location: Optional[str] = None
    calibration_date: Optional[str] = None
    next_calibration_date: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None


class EquipmentShareCreate(BaseModel):
    shared_with_organization_id: int
    start_date: str
    end_date: str


class EquipmentShareResponse(BaseModel):
    id: int
    equipment_id: int
    equipment_name: Optional[str] = None
    owner_organization_id: int
    owner_organization_name: Optional[str] = None
    shared_with_organization_id: int
    shared_with_organization_name: Optional[str] = None
    status: str
    start_date: str
    end_date: str

    class Config:
        from_attributes = True


class EquipmentResponse(BaseModel):
    id: int
    organization_id: int
    organization_name: Optional[str] = None
    name: str
    equipment_type: str
    serial_number: Optional[str] = None
    status: str
    location: Optional[str] = None
    calibration_date: Optional[str] = None
    next_calibration_date: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ================= REPORTS & DATA SCHEMAS =================

class ReportCreate(BaseModel):
    description: str = Field(..., min_length=10, max_length=1000)
    location: str = Field(..., min_length=3, max_length=200)
    water_source: str = Field(..., min_length=2, max_length=100)
    station_name: str = Field(..., min_length=2, max_length=200)
    visibility: Optional[str] = "public"


class ReportResponse(BaseModel):
    id: int
    description: str
    location: str
    water_source: str
    station_name: str
    photo_url: Optional[str] = None
    status: str
    user_id: Optional[int] = None
    organization_id: Optional[int] = None
    visibility: str = "public"
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class ReportAction(BaseModel):
    report_id: int
    verified: bool


class StationResponse(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    station_no: Optional[str] = None
    territory_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class NGOProjectCreate(BaseModel):
    project_name: str = Field(..., min_length=2, max_length=200)
    contact_email: EmailStr
    description: Optional[str] = None
    visibility: Optional[str] = "public"


class NGOProjectResponse(BaseModel):
    id: int
    project_name: str
    contact_email: str
    description: Optional[str] = None
    owner_id: int
    organization_id: Optional[int] = None
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    station_id: Optional[str] = None
    station_name: str
    organization_id: Optional[int] = None
    alert_type: str = "LIVE"
    level: str
    severity: str = "MEDIUM"
    parameter: Optional[str] = None
    current_value: Optional[float] = None
    baseline_value: Optional[float] = None
    risk_score: Optional[float] = None
    confidence: Optional[float] = None
    explanation: Optional[str] = None
    message: str
    status: str
    created_at: str
    resolved_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    channel: str
    status: str
    created_at: str
    read_at: Optional[str] = None

    class Config:
        from_attributes = True
