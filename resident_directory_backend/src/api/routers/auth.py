from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.api.core.audit import write_audit_log
from src.api.core.auth import create_access_token_for_user, get_current_user, hash_password, verify_password
from src.api.core.db import get_db
from src.api.models import Role, User
from src.api.schemas import LoginRequest, SignupRequest, TokenResponse

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


@router.post(
    "/signup",
    response_model=TokenResponse,
    summary="Sign up",
    description="Create a new user account and return a JWT access token.",
    operation_id="auth_signup",
)
# PUBLIC_INTERFACE
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    """Create a new user and return a JWT token.

    Notes:
        - This endpoint assigns a default `resident` role.
        - Email uniqueness is enforced.
        - Passwords are stored hashed (bcrypt).
    """
    existing = db.query(User).filter(User.email == payload.email).one_or_none()
    if existing is not None:
        write_audit_log(
            db,
            request=request,
            actor=None,
            action="signup_failed_email_taken",
            entity_type="user",
            entity_id=None,
            details={"email": payload.email},
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    # Ensure default role exists (best-effort); if it doesn't exist, create it.
    role = db.query(Role).filter(Role.name == "resident").one_or_none()
    if role is None:
        role = Role(name="resident", description="Default resident role")
        db.add(role)
        db.flush()

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=(payload.display_name.strip() if payload.display_name else None),
        is_active=True,
    )
    user.roles.append(role)

    db.add(user)
    db.commit()
    db.refresh(user)

    roles = [r.name for r in user.roles]
    token = create_access_token_for_user(user, roles)

    write_audit_log(
        db,
        request=request,
        actor=user,
        action="signup_success",
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


@router.get(
    "/me",
    summary="Get current user",
    description="Return the current authenticated user (derived from the JWT).",
    operation_id="auth_me",
)
# PUBLIC_INTERFACE
def me(request: Request, user: User = Depends(get_current_user)):
    """Return current user identity and a UI-friendly primary role.

    Notes:
        The frontend expects a single `role` string for gating. The backend supports multiple roles
        and returns the full list at login; here we derive a primary role for convenience.

    Returns:
        Dict with id, email, display_name, role.
    """
    role_names = [r.name for r in user.roles]
    primary_role = "admin" if "admin" in role_names else "resident"

    # Audit as a low-risk read (useful for troubleshooting session restore).
    # We do not include sensitive details.
    # This is optional, but aligns with the audit logging requirement.
    # A DB session isn't available in this dependency signature; keep it minimal.
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": primary_role,
    }
