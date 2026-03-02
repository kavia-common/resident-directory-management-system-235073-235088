from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.api.core.audit import write_audit_log
from src.api.core.auth import create_access_token_for_user, verify_password
from src.api.core.db import get_db
from src.api.models import User
from src.api.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate user by email/password and return a JWT access token.",
    operation_id="auth_login",
)
# PUBLIC_INTERFACE
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        # Avoid leaking which field was wrong.
        write_audit_log(
            db,
            request=request,
            actor=None,
            action="login_failed",
            entity_type="user",
            entity_id=None,
            details={"email": payload.email},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    roles = [r.name for r in user.roles]
    token = create_access_token_for_user(user, roles)

    write_audit_log(
        db,
        request=request,
        actor=user,
        action="login_success",
        entity_type="user",
        entity_id=str(user.id),
        details={"roles": roles},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        roles=roles,
        user={"id": user.id, "email": user.email, "display_name": user.display_name},
    )
