from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db
from app.models import User, Organization, OrganizationMember

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Granular Permission Matrix for Organization Roles
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "admin": [
        "manage_organization",
        "manage_team",
        "create_incident",
        "update_incident",
        "assign_task",
        "perform_remediation",
        "add_comment",
        "manage_equipment",
        "share_equipment",
        "manage_calendar",
        "view_audit_logs",
        "manage_data_sharing",
        "manage_projects",
        "view_reports",
        "view_alerts"
    ],
    "field_worker": [
        "create_incident",
        "update_incident",
        "update_assigned_task",
        "perform_remediation",
        "add_comment",
        "use_equipment",
        "create_calendar_event",
        "view_reports",
        "view_alerts"
    ],
    "viewer": [
        "view_reports",
        "view_incidents",
        "view_alerts",
        "view_calendar",
        "view_equipment",
        "view_projects"
    ]
}


def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token containing identity, system role, and optional organization context"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        user_id: Optional[int] = payload.get("user_id")
        organization_id: Optional[int] = payload.get("organization_id")
        org_role: Optional[str] = payload.get("org_role")
        
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "email": email,
            "role": role,
            "user_id": user_id,
            "organization_id": organization_id,
            "org_role": org_role
        }
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get full authenticated user context from database and JWT token.
    Resolves organization membership dynamically if not in token.
    """
    payload = verify_token(token)
    email = payload["email"]
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Resolve active organization context
    organization_id = payload.get("organization_id")
    org_role = payload.get("org_role")

    if not organization_id and user.role == "ngo":
        # Look up primary active membership
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.status == "active"
        ).first()
        if membership:
            organization_id = membership.organization_id
            org_role = membership.role

    return {
        "id": user.id,
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "organization_id": organization_id,
        "org_role": org_role
    }


def get_current_organization(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Organization:
    """
    Dependency ensuring the active user belongs to a valid, active organization.
    """
    # System admins bypass organization requirement if not assigned
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not associated with any active NGO organization. Please create or join an organization first."
        )

    org = db.query(Organization).filter(
        Organization.id == org_id,
        Organization.status == "active"
    ).first()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or is currently inactive"
        )

    return org


def require_role(allowed_roles: List[str]):
    """System-level role check (citizen, ngo, authority, admin)"""
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles and current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have system permission to access this resource"
            )
        return current_user
    return role_checker


def require_org_role(allowed_org_roles: List[str]):
    """Organization-level role check (admin, field_worker, viewer)"""
    def org_role_checker(current_user: dict = Depends(get_current_user)):
        # System Admin always allowed
        if current_user["role"] == "admin":
            return current_user

        org_role = current_user.get("org_role")
        if not org_role or org_role not in allowed_org_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires one of the following organization roles: {', '.join(allowed_org_roles)}"
            )
        return current_user
    return org_role_checker


def require_permission(permission: str):
    """Fine-grained capability checker based on organization role matrix"""
    def permission_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] == "admin":
            return current_user

        org_role = current_user.get("org_role", "viewer")
        allowed_permissions = ROLE_PERMISSIONS.get(org_role, [])

        if permission not in allowed_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission}' is not permitted for your role ({org_role})"
            )
        return current_user
    return permission_checker