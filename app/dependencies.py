from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models import RevokedAccessToken, User

bearer_scheme = HTTPBearer()
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)], db: DbSession
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        token_id = payload.get("jti")
        if not user_id or not token_id or payload.get("type") != "access":
            raise unauthorized
    except jwt.PyJWTError:
        raise unauthorized
    if db.get(RevokedAccessToken, token_id):
        raise unauthorized
    try:
        user = db.get(User, int(user_id))
    except (TypeError, ValueError):
        raise unauthorized
    if not user:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
