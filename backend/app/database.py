from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./water_quality.db")

# Create engine with settings based on database type
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


def get_db():
    """Database dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()