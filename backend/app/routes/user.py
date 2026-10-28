from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import logging

from app.database import get_db
from app.models import User, OrganizationMember, Organization
from app.schemas import UserCreate, TokenResponse, UserResponse, OrgMembershipBrief
from app.auth import create_token, require_role, get_current_user
from app.services.audit_service import audit_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])

# Use bcrypt for password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(
    data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin"]))
):
    """
    Register a new user (Admin only)
    """
    logger.info(f"Registration attempt by admin {current_user['email']} for email: {data.email}")
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == data.email.strip()).first()
    if existing_user:
        logger.warning(f"Registration failed - email already exists: {data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. An account with this email already exists."
        )
    
    # Hash password
    hashed_password = pwd_context.hash(data.password[:72])

    # Create new user
    new_user = User(
        name=data.name.strip(),
        email=data.email.strip(),
        password=hashed_password,
        role=data.role or "citizen"
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # If registering an NGO user with organization_id, add membership
        if data.role == "ngo" and data.organization_id:
            org = db.query(Organization).filter(Organization.id == data.organization_id).first()
            if org:
                membership = OrganizationMember(
                    organization_id=data.organization_id,
                    user_id=new_user.id,
                    role=data.org_role or "field_worker",
                    status="active"
                )
                db.add(membership)
                db.commit()
        
        # Log registration audit
        audit_service.log(
            db=db,
            action="CREATE",
            user_id=current_user["user_id"],
            resource_type="user",
            resource_id=new_user.id,
            ip_address=request.client.host if request.client else None,
            metadata={"created_email": new_user.email, "role": new_user.role}
        )

        logger.info(f"User registered successfully: {data.email}")
        
        return {
            "message": "User registered successfully",
            "user_id": new_user.id
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error for {data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    username: str = Form(..., description="Email address"),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Login to get access token with organization context.
    """
    logger.info(f"Login attempt for: {username}")
    
    # Find user by email
    db_user = db.query(User).filter(User.email == username.strip()).first()
    
    # Verify credentials
    if not db_user or not pwd_context.verify(password, db_user.password):
        logger.warning(f"Failed login attempt for: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Resolve organization context if NGO
    organization_id = None
    org_role = None

    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == db_user.id,
        OrganizationMember.status == "active"
    ).all()

    if memberships:
        primary_membership = memberships[0]
        organization_id = primary_membership.organization_id
        org_role = primary_membership.role

    # Create access token
    access_token = create_token({
        "sub": db_user.email,
        "role": db_user.role,
        "user_id": db_user.id,
        "organization_id": organization_id,
        "org_role": org_role
    })
    
    # Audit log
    audit_service.log(
        db=db,
        action="LOGIN",
        user_id=db_user.id,
        organization_id=organization_id,
        resource_type="auth",
        ip_address=request.client.host if request.client else None,
        metadata={"email": db_user.email, "role": db_user.role}
    )

    logger.info(f"Successful login for: {username}")
    
    # Format membership list
    org_list = []
    for m in memberships:
        org_item = db.query(Organization).filter(Organization.id == m.organization_id).first()
        if org_item:
            org_list.append(
                OrgMembershipBrief(
                    organization_id=org_item.id,
                    organization_name=org_item.name,
                    role=m.role,
                    status=m.status
                )
            )

    user_response = UserResponse(
        id=db_user.id,
        name=db_user.name,
        email=db_user.email,
        role=db_user.role,
        organization_id=organization_id,
        org_role=org_role,
        organizations=org_list
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_response
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information and organization memberships.
    """
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.status == "active"
    ).all()

    org_list = []
    for m in memberships:
        org_item = db.query(Organization).filter(Organization.id == m.organization_id).first()
        if org_item:
            org_list.append(
                OrgMembershipBrief(
                    organization_id=org_item.id,
                    organization_name=org_item.name,
                    role=m.role,
                    status=m.status
                )
            )

    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        organization_id=current_user.get("organization_id"),
        org_role=current_user.get("org_role"),
        organizations=org_list
    )
