import json
import logging
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from app.models import AuditLog

logger = logging.getLogger(__name__)

# List of sensitive keys that should NEVER be recorded in audit logs
SENSITIVE_KEYS = {"password", "token", "access_token", "secret", "secret_key", "pwd", "authorization"}

def _sanitize_dict(data: Any) -> Any:
    """Recursively strip sensitive data from metadata payloads"""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            key_lower = str(k).lower()
            if any(sens in key_lower for sens in SENSITIVE_KEYS):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                sanitized[k] = _sanitize_dict(v)
            else:
                sanitized[k] = v
        return sanitized
    elif isinstance(data, list):
        return [_sanitize_dict(item) for item in data]
    return data

class AuditService:
    @staticmethod
    def log(
        db: Session,
        action: str,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        resource_type: str = "general",
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[AuditLog]:
        """
        Record a persistent audit log entry in the database.
        Safe against sensitive credential leakage.
        """
        try:
            metadata_str = None
            if metadata:
                sanitized = _sanitize_dict(metadata)
                metadata_str = json.dumps(sanitized)

            log_entry = AuditLog(
                user_id=user_id,
                organization_id=organization_id,
                action=action.upper(),
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                metadata_json=metadata_str
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            logger.info(f"AUDIT: [{action.upper()}] User={user_id} Org={organization_id} Resource={resource_type}:{resource_id}")
            return log_entry
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record audit log: {e}")
            return None

audit_service = AuditService()
