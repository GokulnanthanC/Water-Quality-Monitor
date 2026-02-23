from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import logging

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, TokenResponse, UserResponse
from app.auth import create_token, require_role

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])

# Use bcrypt for password hashing (more secure than pbkdf2)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Higher rounds = more secure but slower
)


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db), current_user: dict = Depends(require_role(["admin"]))):
    """
    Register a new user (Admin only)
    
    - **name**: User's full name (2-100 characters)
    - **email**: Valid email address
    - **password**: Strong password (min 8 chars, must contain uppercase, lowercase, and number)
    - **role**: Role to assign (citizen, ngo, authority)
    """
    logger.info(f"Registration attempt by admin {current_user['email']} for email: {data.email}")
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        logger.warning(f"Registration failed - email already exists: {data.email}")
        # Generic message to prevent email enumeration
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your information."
        )
    
    # Hash password
    hashed_password = pwd_context.hash(data.password[:72])

    
    # Create new user
    new_user = User(
        name=data.name,
        email=data.email,
        password=hashed_password,
        role=data.role or "citizen"  # Use provided role or default
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
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
    username: str = Form(..., description="Email address"),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Login to get access token
    
    - **username**: Your email address
    - **password**: Your password
    
    Returns a JWT token to use for authenticated requests
    """
    logger.info(f"Login attempt for: {username}")
    
    # Find user by email (username field contains email)
    db_user = db.query(User).filter(User.email == username).first()
    
    # Verify credentials
    if not db_user or not pwd_context.verify(password, db_user.password):
        logger.warning(f"Failed login attempt for: {username}")
        # Generic message to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_token({
        "sub": db_user.email,
        "role": db_user.role,
        "user_id": db_user.id
    })
    
    logger.info(f"Successful login for: {username}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: dict = Depends(lambda token: __import__('app.auth', fromlist=['get_current_user']).get_current_user(token)),
    db: Session = Depends(get_db)
):
    """
    Get current user information
    
    Requires authentication token
    """
    user = db.query(User).filter(User.email == current_user["email"]).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
