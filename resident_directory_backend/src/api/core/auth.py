from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.api.core.db import get_db
from src.api.core.settings import get_settings
from src.api.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

TOKEN_SUBJECT = "access"


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    return pwd_context.verify(password, password_hash)


def _create_access_token(subject: str, payload: Dict[str, Any], expires_minutes: int) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)
    to_encode = {"sub": subject, "iat": int(now.timestamp()), "exp": int(exp.timestamp()), **payload}
    return jwt.encode(to_encode, s.jwt_secret, algorithm=s.jwt_algorithm)


# PUBLIC_INTERFACE
def create_access_token_for_user(user: User, roles: List[str]) -> str:
    """Create a JWT access token for the given user with role claims."""
    s = get_settings()
    return _create_access_token(
        subject=TOKEN_SUBJECT,
        payload={"user_id": user.id, "email": user.email, "roles": roles},
        expires_minutes=s.access_token_expire_minutes,
    )


# PUBLIC_INTERFACE
def decode_token(token: str) -> Dict[str, Any]:
    """Decode/verify JWT token and return claims."""
    s = get_settings()
    try:
        decoded = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
        if decoded.get("sub") != TOKEN_SUBJECT:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
        return decoded
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from e
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e


# PUBLIC_INTERFACE
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """FastAPI dependency to get current authenticated user."""
    claims = decode_token(token)
    user_id = claims.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing user_id")
    user = db.query(User).filter(User.id == int(user_id)).one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user


# PUBLIC_INTERFACE
def require_roles(required: List[str]):
    """Dependency factory to require one of the provided roles.

    Usage:
        Depends(require_roles(["admin"]))
    """

    def _dep(user: User = Depends(get_current_user), token: str = Depends(oauth2_scheme)) -> User:
        claims = decode_token(token)
        roles = claims.get("roles") or []
        if not any(r in roles for r in required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _dep
