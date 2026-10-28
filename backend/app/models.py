from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="citizen", nullable=False) # citizen, ngo, authority, admin
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    organization_memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user")
    ngo_projects = relationship("NGOProject", back_populates="owner")
    comments = relationship("Comment", back_populates="user")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    mission = Column(Text, nullable=True)
    geographic_focus = Column(String, nullable=True) # e.g., "Ganga Basin, Bihar", "Yamuna Region"
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    address = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(String, default="active", nullable=False) # active, suspended, pending
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="organization")
    calendar_events = relationship("CalendarEvent", back_populates="organization")
    equipment_items = relationship("Equipment", back_populates="organization")
    projects = relationship("NGOProject", back_populates="organization")
    audit_logs = relationship("AuditLog", back_populates="organization")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, default="field_worker", nullable=False) # admin, field_worker, viewer
    status = Column(String, default="active", nullable=False) # active, invited, suspended
    joined_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organization_memberships")


class DataAccessPolicy(Base):
    __tablename__ = "data_access_policies"
    id = Column(Integer, primary_key=True, index=True)
    resource_type = Column(String, nullable=False) # report, incident, equipment, calendar_event, project
    resource_id = Column(Integer, nullable=False)
    owner_organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    visibility = Column(String, default="private", nullable=False) # private, partner, public
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    partners = relationship("DataAccessPartner", back_populates="policy", cascade="all, delete-orphan")


class DataAccessPartner(Base):
    __tablename__ = "data_access_partners"
    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("data_access_policies.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    permission = Column(String, default="read", nullable=False) # read, write, full
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    policy = relationship("DataAccessPolicy", back_populates="partners")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    action = Column(String, nullable=False) # LOGIN, VIEW, CREATE, UPDATE, DELETE, SHARE, ASSIGN, RESOLVE
    resource_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    metadata_json = Column(Text, nullable=True) # JSON payload string with change diffs

    organization = relationship("Organization", back_populates="audit_logs")


class Station(Base):
    __tablename__ = "stations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    station_no = Column(String, nullable=True)
    territory_name = Column(String, nullable=True)


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    water_source = Column(String, nullable=False)
    station_name = Column(String, nullable=False)
    photo_url = Column(String, nullable=True)
    location = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False) # pending, verified, rejected
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    visibility = Column(String, default="public", nullable=False) # public, private, partner
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    user = relationship("User", back_populates="reports")


class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    station_id = Column(String, nullable=True) # station_id / code (e.g. BH72)
    station_name = Column(String, nullable=True)
    reported_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, default="MEDIUM", nullable=False) # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String, default="OPEN", nullable=False) # OPEN, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    resolved_at = Column(String, nullable=True)

    organization = relationship("Organization", back_populates="incidents")
    tasks = relationship("IncidentTask", back_populates="incident", cascade="all, delete-orphan")
    actions = relationship("IncidentAction", back_populates="incident", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="incident", cascade="all, delete-orphan")


class IncidentTask(Base):
    __tablename__ = "incident_tasks"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="PENDING", nullable=False) # PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    due_date = Column(String, nullable=True)
    completed_at = Column(String, nullable=True)

    incident = relationship("Incident", back_populates="tasks")


class IncidentAction(Base):
    __tablename__ = "incident_actions"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=False)
    timestamp = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    incident = relationship("Incident", back_populates="actions")


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True)
    station_id = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    incident = relationship("Incident", back_populates="comments")
    user = relationship("User", back_populates="comments")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    station_id = Column(String, nullable=True)
    station_name = Column(String, nullable=True)
    start_time = Column(String, nullable=False) # ISO 8601 string or YYYY-MM-DD HH:MM
    end_time = Column(String, nullable=False)
    event_type = Column(String, default="SAMPLING", nullable=False) # SAMPLING, INSPECTION, CALIBRATION, MEETING, FIELD_VISIT
    status = Column(String, default="SCHEDULED", nullable=False) # SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED

    organization = relationship("Organization", back_populates="calendar_events")


class Equipment(Base):
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    equipment_type = Column(String, nullable=False) # pH Meter, Turbidimeter, DO Sensor, Sampler Kit, etc.
    serial_number = Column(String, nullable=True)
    status = Column(String, default="AVAILABLE", nullable=False) # AVAILABLE, IN_USE, MAINTENANCE, SHARED, RETIRED
    location = Column(String, nullable=True)
    calibration_date = Column(String, nullable=True)
    next_calibration_date = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    description = Column(Text, nullable=True)

    organization = relationship("Organization", back_populates="equipment_items")
    shares = relationship("EquipmentShare", back_populates="equipment", cascade="all, delete-orphan")


class EquipmentShare(Base):
    __tablename__ = "equipment_shares"
    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    owner_organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    shared_with_organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="PENDING", nullable=False) # PENDING, APPROVED, ACTIVE, RETURNED, REJECTED
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)

    equipment = relationship("Equipment", back_populates="shares")


class NGOProject(Base):
    __tablename__ = "ngo_projects"
    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    visibility = Column(String, default="public", nullable=False) # public, partner, private

    owner = relationship("User", back_populates="ngo_projects")
    organization = relationship("Organization", back_populates="projects")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(String, nullable=True)
    station_name = Column(String, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    alert_type = Column(String, default="LIVE", nullable=False) # LIVE, PREDICTIVE, ANOMALY, THRESHOLD
    level = Column(String, default="Warning", nullable=False) # Warning, High, Critical
    severity = Column(String, default="MEDIUM", nullable=False) # LOW, MEDIUM, HIGH, CRITICAL
    parameter = Column(String, nullable=True) # ph, turbidity, do
    current_value = Column(Float, nullable=True)
    baseline_value = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True) # 0.0 to 1.0
    confidence = Column(Float, nullable=True) # 0.0 to 1.0
    explanation = Column(Text, nullable=True)
    message = Column(String, nullable=False)
    status = Column(String, default="active", nullable=False) # active, acknowledged, resolved
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    resolved_at = Column(String, nullable=True)

    notifications = relationship("Notification", back_populates="alert", cascade="all, delete-orphan")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String, default="in_platform", nullable=False) # in_platform, email, sms
    status = Column(String, default="unread", nullable=False) # unread, read, archived
    created_at = Column(String, default=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    read_at = Column(String, nullable=True)

    user = relationship("User", back_populates="notifications")
    alert = relationship("Alert", back_populates="notifications")
