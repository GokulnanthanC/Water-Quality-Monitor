import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SECRET_KEY = os.getenv("SECRET_KEY", "default-dev-secret-key-water-quality-2026-secure")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

# File upload settings
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}