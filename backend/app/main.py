try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from passlib.context import CryptContext

from app.database import SessionLocal, engine
from app import models
from app.models import User, Organization, OrganizationMember

# Create tables
models.Base.metadata.create_all(bind=engine)

from app.routes.reports import router as reports_router
from app.routes.user import router as user_router
from app.routes.stations import router as stations_router
from app.routes.analytics import router as analytics_router
from app.routes.water_data import router as water_data_router
from app.routes.ngo import router as ngo_router
from app.routes.dashboard import router as dashboard_router
from app.routes.organizations import router as organizations_router
from app.config import UPLOAD_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Water Quality Monitoring API",
    description="Multi-Tenant API for real-time water quality monitoring, citizen reporting, NGO collaboration, and predictive alerts",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    max_age=3600
)

# Serve uploaded files
if os.path.exists(UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(user_router)
app.include_router(organizations_router)
app.include_router(reports_router)
app.include_router(stations_router)
app.include_router(analytics_router)
app.include_router(water_data_router)
app.include_router(ngo_router)
app.include_router(dashboard_router)


@app.get("/")
def root():
    """Root endpoint - API health check"""
    return {
        "message": "Water Quality Monitoring API - Multi-Tenant Platform",
        "status": "running",
        "version": "2.0.0"
    }


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "water-quality-api",
        "version": "2.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("Starting Water Quality Monitoring API (Multi-Tenant NGO Collaboration)")
    logger.info(f"Allowed CORS origins: {allowed_origins}")
    
    # Create upload directory if it doesn't exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory: {UPLOAD_DIR}")

    # Schema migration checks (non-destructive)
    try:
        with engine.connect() as conn:
            # Check/Add columns to stations table
            conn.execute(text("ALTER TABLE stations ADD COLUMN IF NOT EXISTS station_no VARCHAR"))
            conn.execute(text("ALTER TABLE stations ADD COLUMN IF NOT EXISTS territory_name VARCHAR"))

            # Check/Add columns to users table
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at VARCHAR"))

            # Check/Add columns to reports table
            conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS station_name VARCHAR"))
            conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS photo_url VARCHAR"))
            conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS location VARCHAR"))
            conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'pending'"))
            conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS user_id INTEGER"))
            conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS organization_id INTEGER"))
            conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS visibility VARCHAR DEFAULT 'public'"))
            conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS created_at VARCHAR"))

            # Check/Add columns to alerts table
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS station_id VARCHAR"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS station_name VARCHAR DEFAULT 'Unknown Station'"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS organization_id INTEGER"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS alert_type VARCHAR DEFAULT 'LIVE'"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS level VARCHAR DEFAULT 'Warning'"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS severity VARCHAR DEFAULT 'MEDIUM'"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS parameter VARCHAR"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS current_value FLOAT"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS baseline_value FLOAT"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS risk_score FLOAT"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS confidence FLOAT"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS explanation TEXT"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS message VARCHAR DEFAULT 'No message'"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'active'"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS created_at VARCHAR"))
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS resolved_at VARCHAR"))

            # Check/Add columns to ngo_projects table
            conn.execute(text("ALTER TABLE ngo_projects ADD COLUMN IF NOT EXISTS organization_id INTEGER"))
            conn.execute(text("ALTER TABLE ngo_projects ADD COLUMN IF NOT EXISTS visibility VARCHAR DEFAULT 'public'"))
            conn.execute(text("ALTER TABLE ngo_projects ADD COLUMN IF NOT EXISTS created_at VARCHAR"))

            conn.commit()
            logger.info("Database schema columns checked and verified")
    except Exception as e:
        logger.warning(f"Schema check warning: {e}")

    # Seed Default Admin User & Pilot NGO
    db: Session = SessionLocal()
    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

        # 1. Seed Admin
        admin_email = "admin123@gmail.com"
        admin_pass = "Admin@123"
        admin_user = db.query(User).filter(User.email == admin_email).first()
        hashed_admin_password = pwd_context.hash(admin_pass)
        
        if not admin_user:
            admin_user = User(
                name="System Admin",
                email=admin_email,
                password=hashed_admin_password,
                role="admin"
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            logger.info(f"Created default admin user: {admin_email}")

        # 2. Seed Pilot NGO Organization
        pilot_org_name = "Clean Rivers Alliance"
        pilot_org = db.query(Organization).filter(Organization.name == pilot_org_name).first()
        if not pilot_org:
            pilot_org = Organization(
                name=pilot_org_name,
                description="Community-led water quality protection and pollution mitigation network for major river basins.",
                mission="Restoring freshwater ecosystems and engaging citizens in water conservation.",
                geographic_focus="Ganga & Yamuna Basins",
                email="contact@cleanrivers.org",
                phone="+91-9876543210",
                website="https://cleanrivers.org",
                address="12 Riverfront Road, Patna, Bihar",
                status="active"
            )
            db.add(pilot_org)
            db.commit()
            db.refresh(pilot_org)
            logger.info(f"Created default pilot organization: {pilot_org_name}")

        # 3. Seed Default NGO User
        ngo_email = "ngo123@gmail.com"
        ngo_pass = "Ngo@123"
        ngo_user = db.query(User).filter(User.email == ngo_email).first()
        if not ngo_user:
            ngo_user = User(
                name="NGO Representative",
                email=ngo_email,
                password=pwd_context.hash(ngo_pass),
                role="ngo"
            )
            db.add(ngo_user)
            db.commit()
            db.refresh(ngo_user)

            # Associate with pilot organization as Admin
            membership = OrganizationMember(
                organization_id=pilot_org.id,
                user_id=ngo_user.id,
                role="admin",
                status="active"
            )
            db.add(membership)
            db.commit()
            logger.info(f"Created default NGO admin user: {ngo_email}")
        else:
            # Keep credentials and role synchronized
            ngo_user.password = pwd_context.hash(ngo_pass)
            ngo_user.role = "ngo"
            db.commit()
            # Ensure membership exists
            membership = db.query(OrganizationMember).filter(
                OrganizationMember.organization_id == pilot_org.id,
                OrganizationMember.user_id == ngo_user.id
            ).first()
            if not membership:
                membership = OrganizationMember(
                    organization_id=pilot_org.id,
                    user_id=ngo_user.id,
                    role="admin",
                    status="active"
                )
                db.add(membership)
                db.commit()
            logger.info(f"Updated default NGO user credentials: {ngo_email}")

    except Exception as e:
        logger.error(f"Error during startup seed: {e}")
        db.rollback()
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("Shutting down Water Quality Monitoring API")