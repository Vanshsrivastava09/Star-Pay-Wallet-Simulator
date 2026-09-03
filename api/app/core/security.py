from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_password(password: str) -> None:
    if not isinstance(password, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be a string.")
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters long.")
    if len(password) > 128:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must not exceed 128 characters.")
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must not exceed 72 bytes when encoded as UTF-8.",
        )


def hash_password(password: str) -> str:
    validate_password(password)
    try:
        return pwd_context.hash(password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not isinstance(plain_password, str):
        return False
    if len(plain_password.encode("utf-8")) > 72:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": subject, "exp": expires_at, "type": "access", "jti": uuid4().hex},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def create_refresh_token(subject: str, token_id: str) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    token = jwt.encode(
        {"sub": subject, "exp": expires_at, "type": "refresh", "jti": token_id},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return token, expires_at


def hash_token(token: str) -> str:
    """Create a non-reversible database identifier for a refresh token."""
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
