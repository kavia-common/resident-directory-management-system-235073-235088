from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from src.api.models import AuditLog, User


# PUBLIC_INTERFACE
def write_audit_log(
    db: Session,
    *,
    request: Optional[Request],
    actor: Optional[User],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Write an immutable audit log entry (best-effort).

    This is designed to never crash the primary request flow. If audit insert fails,
    the request should still succeed.
    """
    try:
        ip = None
        user_agent = None
        request_id = None
        if request is not None:
            ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            request_id = request.headers.get("x-request-id")

        log = AuditLog(
            actor_user_id=actor.id if actor else None,
            actor_email=actor.email if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip,
            user_agent=user_agent,
            request_id=request_id,
            details=details or {},
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
        # swallow any errors intentionally (best-effort audit)
        return
