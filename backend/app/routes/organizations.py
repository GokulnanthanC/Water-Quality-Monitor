from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.database import get_db
from app.models import Organization, OrganizationMember, User, AuditLog
from app.schemas import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationMemberResponse, MemberAdd, MemberUpdateRole,
    AuditLogResponse, TokenResponse
)
from app.auth import get_current_user, require_role, require_org_role, create_token
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizations", tags=["Organizations & Teams"])


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    data: OrganizationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["ngo", "admin"]))
):
    """
    Create a new NGO organization and assign creator as organization admin.
    """
    existing_org = db.query(Organization).filter(Organization.name == data.name.strip()).first()
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An organization with this name already exists"
        )

    new_org = Organization(
        name=data.name.strip(),
        description=data.description,
        mission=data.mission,
        geographic_focus=data.geographic_focus,
        email=data.email,
        phone=data.phone,
        website=data.website,
        address=data.address,
        latitude=data.latitude,
        longitude=data.longitude,
        status="active"
    )

    try:
        db.add(new_org)
        db.commit()
        db.refresh(new_org)

        # Automatically make creator the Organization Admin
        membership = OrganizationMember(
            organization_id=new_org.id,
            user_id=current_user["user_id"],
            role="admin",
            status="active"
        )
        db.add(membership)
        db.commit()

        # Audit log
        audit_service.log(
            db=db,
            action="CREATE",
            user_id=current_user["user_id"],
            organization_id=new_org.id,
            resource_type="organization",
            resource_id=new_org.id,
            ip_address=request.client.host if request.client else None,
            metadata={"name": new_org.name, "email": new_org.email}
        )

        return OrganizationResponse(
            id=new_org.id,
            name=new_org.name,
            description=new_org.description,
            mission=new_org.mission,
            geographic_focus=new_org.geographic_focus,
            email=new_org.email,
            phone=new_org.phone,
            website=new_org.website,
            address=new_org.address,
            latitude=new_org.latitude,
            longitude=new_org.longitude,
            status=new_org.status,
            created_at=new_org.created_at,
            member_count=1
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create organization: {str(e)}"
        )


@router.get("/", response_model=List[OrganizationResponse])
def list_organizations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List all active organizations for partnership directory and cross-team discovery.
    """
    orgs = db.query(Organization).filter(Organization.status == "active").all()
    results = []
    for org in orgs:
        member_count = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.status == "active"
        ).count()
        results.append(
            OrganizationResponse(
                id=org.id,
                name=org.name,
                description=org.description,
                mission=org.mission,
                geographic_focus=org.geographic_focus,
                email=org.email,
                phone=org.phone,
                website=org.website,
                address=org.address,
                latitude=org.latitude,
                longitude=org.longitude,
                status=org.status,
                created_at=org.created_at,
                member_count=member_count
            )
        )
    return results


@router.get("/my", response_model=OrganizationResponse)
def get_my_organization(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get active organization profile for current logged-in user.
    """
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not associated with any active organization"
        )

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.status == "active"
    ).count()

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        description=org.description,
        mission=org.mission,
        geographic_focus=org.geographic_focus,
        email=org.email,
        phone=org.phone,
        website=org.website,
        address=org.address,
        latitude=org.latitude,
        longitude=org.longitude,
        status=org.status,
        created_at=org.created_at,
        member_count=member_count
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get organization details by ID.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.status == "active"
    ).count()

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        description=org.description,
        mission=org.mission,
        geographic_focus=org.geographic_focus,
        email=org.email,
        phone=org.phone,
        website=org.website,
        address=org.address,
        latitude=org.latitude,
        longitude=org.longitude,
        status=org.status,
        created_at=org.created_at,
        member_count=member_count
    )


@router.put("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: int,
    data: OrganizationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update organization profile (Requires Organization Admin or System Admin).
    """
    if current_user["role"] != "admin":
        if current_user.get("organization_id") != org_id or current_user.get("org_role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Organization Admins can update organization profile"
            )

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    update_dict = data.dict(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(org, field, val)

    try:
        db.commit()
        db.refresh(org)

        audit_service.log(
            db=db,
            action="UPDATE",
            user_id=current_user["user_id"],
            organization_id=org.id,
            resource_type="organization",
            resource_id=org.id,
            ip_address=request.client.host if request.client else None,
            metadata=update_dict
        )

        member_count = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.status == "active"
        ).count()

        return OrganizationResponse(
            id=org.id,
            name=org.name,
            description=org.description,
            mission=org.mission,
            geographic_focus=org.geographic_focus,
            email=org.email,
            phone=org.phone,
            website=org.website,
            address=org.address,
            latitude=org.latitude,
            longitude=org.longitude,
            status=org.status,
            created_at=org.created_at,
            member_count=member_count
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update organization: {str(e)}"
        )


# ================= TEAM MEMBER MANAGEMENT =================

@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse])
def get_organization_members(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List all team members of an organization.
    """
    if current_user["role"] != "admin" and current_user.get("organization_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this organization."
        )

    members = db.query(OrganizationMember).filter(OrganizationMember.organization_id == org_id).all()
    results = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        results.append(
            OrganizationMemberResponse(
                id=m.id,
                user_id=m.user_id,
                name=user.name if user else "Unknown",
                email=user.email if user else "Unknown",
                role=m.role,
                status=m.status,
                joined_at=m.joined_at
            )
        )
    return results


@router.post("/{org_id}/members", response_model=OrganizationMemberResponse, status_code=status.HTTP_201_CREATED)
def add_organization_member(
    org_id: int,
    data: MemberAdd,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add/invite an existing user to the organization (Requires Org Admin).
    """
    if current_user["role"] != "admin":
        if current_user.get("organization_id") != org_id or current_user.get("org_role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Organization Admins can add members"
            )

    user_to_add = db.query(User).filter(User.email == data.email.strip()).first()
    if not user_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registered user found with email {data.email}. The user must register first."
        )

    # Check if already a member
    existing_member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_to_add.id
    ).first()

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )

    # Set user system role to 'ngo' if not already
    if user_to_add.role == "citizen":
        user_to_add.role = "ngo"

    new_member = OrganizationMember(
        organization_id=org_id,
        user_id=user_to_add.id,
        role=data.role,
        status="active"
    )

    try:
        db.add(new_member)
        db.commit()
        db.refresh(new_member)

        audit_service.log(
            db=db,
            action="ASSIGN",
            user_id=current_user["user_id"],
            organization_id=org_id,
            resource_type="member",
            resource_id=new_member.id,
            ip_address=request.client.host if request.client else None,
            metadata={"user_email": user_to_add.email, "role": data.role}
        )

        return OrganizationMemberResponse(
            id=new_member.id,
            user_id=user_to_add.id,
            name=user_to_add.name,
            email=user_to_add.email,
            role=new_member.role,
            status=new_member.status,
            joined_at=new_member.joined_at
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add member: {str(e)}"
        )


@router.put("/{org_id}/members/{member_id}", response_model=OrganizationMemberResponse)
def update_member_role(
    org_id: int,
    member_id: int,
    data: MemberUpdateRole,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update member role (admin, field_worker, viewer) in organization.
    """
    if current_user["role"] != "admin":
        if current_user.get("organization_id") != org_id or current_user.get("org_role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Organization Admins can modify member roles"
            )

    member = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == org_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member record not found"
        )

    old_role = member.role
    member.role = data.role

    try:
        db.commit()
        db.refresh(member)

        user = db.query(User).filter(User.id == member.user_id).first()

        audit_service.log(
            db=db,
            action="UPDATE",
            user_id=current_user["user_id"],
            organization_id=org_id,
            resource_type="member",
            resource_id=member.id,
            ip_address=request.client.host if request.client else None,
            metadata={"target_user_id": member.user_id, "old_role": old_role, "new_role": data.role}
        )

        return OrganizationMemberResponse(
            id=member.id,
            user_id=member.user_id,
            name=user.name if user else "Unknown",
            email=user.email if user else "Unknown",
            role=member.role,
            status=member.status,
            joined_at=member.joined_at
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role: {str(e)}"
        )


@router.delete("/{org_id}/members/{member_id}")
def remove_member(
    org_id: int,
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a member from the organization.
    """
    if current_user["role"] != "admin":
        if current_user.get("organization_id") != org_id or current_user.get("org_role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Organization Admins can remove members"
            )

    member = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.organization_id == org_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member record not found"
        )

    try:
        db.delete(member)
        db.commit()

        audit_service.log(
            db=db,
            action="DELETE",
            user_id=current_user["user_id"],
            organization_id=org_id,
            resource_type="member",
            resource_id=member_id,
            ip_address=request.client.host if request.client else None,
            metadata={"removed_member_id": member_id}
        )

        return {"message": "Member removed successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove member: {str(e)}"
        )


@router.get("/{org_id}/audit-logs", response_model=List[AuditLogResponse])
def get_organization_audit_logs(
    org_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve audit logs for organization (Requires Organization Admin or System Admin).
    """
    if current_user["role"] != "admin":
        if current_user.get("organization_id") != org_id or current_user.get("org_role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Organization Admins can view audit logs"
            )

    logs = db.query(AuditLog).filter(
        AuditLog.organization_id == org_id
    ).order_by(AuditLog.id.desc()).limit(limit).all()

    return logs


@router.post("/switch/{org_id}", response_model=TokenResponse)
def switch_active_organization(
    org_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Switch active organization context in JWT token.
    Returns a fresh JWT token with the new organization_id and org_role.
    """
    user_id = current_user["user_id"]
    user = db.query(User).filter(User.id == user_id).first()

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user_id,
        OrganizationMember.organization_id == org_id,
        OrganizationMember.status == "active"
    ).first()

    if not membership and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an active member of this organization"
        )

    org_role = membership.role if membership else "admin"

    access_token = create_token({
        "sub": user.email,
        "role": user.role,
        "user_id": user.id,
        "organization_id": org_id,
        "org_role": org_role
    })

    audit_service.log(
        db=db,
        action="LOGIN",
        user_id=user.id,
        organization_id=org_id,
        resource_type="session",
        ip_address=request.client.host if request.client else None,
        metadata={"action": "switched_organization", "org_id": org_id, "org_role": org_role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "organization_id": org_id,
            "org_role": org_role
        }
    }
