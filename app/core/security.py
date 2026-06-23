from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


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
