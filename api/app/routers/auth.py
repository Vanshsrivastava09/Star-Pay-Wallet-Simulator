import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Cookie, Header, HTTPException, Response, status
from sqlalchemy import select

from app.core.config import settings
from app.core.email import EmailDeliveryError, send_otp_email, send_password_reset_otp
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    validate_password,
    verify_password,
)
from app.dependencies import CurrentUser, DbSession
from app.models import RefreshToken, RevokedAccessToken, User, Wallet, utc_now
from app.schemas.auth import (
    LoginRequest,
    ForgotPasswordRequest,
    OtpDispatchResponse,
    OtpVerificationRequest,
    ResendOtpRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def issue_otp(user: User, db: DbSession) -> str:
    otp = generate_otp()
    user.otp_code = hash_otp(otp)
    user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)
    db.commit()
    try:
        send_otp_email(user.email, otp)
    except EmailDeliveryError as exc:
        if settings.email_debug:
            return otp
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return otp


def issue_password_reset_otp(user: User, db: DbSession) -> str:
    otp = generate_otp()
    user.password_reset_otp_code = hash_otp(otp)
    user.password_reset_otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)
    db.commit()
    try:
        send_password_reset_otp(user.email, otp)
    except EmailDeliveryError as exc:
        if settings.email_debug:
            return otp
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return otp


def create_token_pair(user: User, db: DbSession, response: Response) -> TokenResponse:
    """Issue an access token and rotate a refresh token stored only as a hash."""
    token_row = RefreshToken(id=secrets.token_hex(16), user_id=user.id)
    refresh_token, expires_at = create_refresh_token(str(user.id), token_row.id)
    token_row.token_hash = hash_token(refresh_token)
    token_row.expires_at = expires_at
    db.add(token_row)
    db.commit()
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        expires_in=settings.access_token_expire_minutes * 60,
    )


def refresh_token_record(refresh_token: str, db: DbSession) -> RefreshToken:
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid, expired, or revoked refresh token")
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        token_id = payload.get("jti")
        user_id = payload.get("sub")
        if not token_id or not user_id or payload.get("type") != "refresh":
            raise invalid
    except jwt.PyJWTError:
        raise invalid
    token_row = db.get(RefreshToken, token_id)
    if not token_row or token_row.token_hash != hash_token(refresh_token) or token_row.revoked_at:
        raise invalid
    expiry = token_row.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc) or str(token_row.user_id) != str(user_id):
        raise invalid
    return token_row


def revoke_access_token(authorization: str | None, db: DbSession) -> None:
    """Denylist the current access JWT until it reaches its own expiry."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return
    try:
        payload = jwt.decode(authorization.split(" ", maxsplit=1)[1], settings.secret_key, algorithms=[settings.algorithm])
        token_id = payload.get("jti")
        expires_at = payload.get("exp")
        if payload.get("type") != "access" or not token_id or not expires_at or db.get(RevokedAccessToken, token_id):
            return
        db.add(RevokedAccessToken(id=token_id, expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc)))
    except (jwt.PyJWTError, TypeError, ValueError):
        return


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: CurrentUser):
    """Return the profile associated with the current bearer token."""
    return current_user


@router.post("/signup", response_model=OtpDispatchResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: DbSession):
    logger.info(
        "Signup request: email=%s full_name=%s password_chars=%d password_bytes=%d",
        payload.email,
        bool(payload.full_name),
        len(payload.password),
        len(payload.password.encode("utf-8")),
    )
    validate_password(payload.password)
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        if existing.is_verified:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        existing.password_hash = hash_password(payload.password)
        if payload.full_name:
            existing.full_name = payload.full_name
        otp = issue_otp(existing, db)
        return OtpDispatchResponse(
            message="A new verification code has been sent to your email.",
            otp=otp if settings.email_debug else None,
        )

    display_name = payload.full_name or str(payload.email).split("@", maxsplit=1)[0]
    user = User(email=str(payload.email), full_name=display_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    otp = issue_otp(user, db)
    return OtpDispatchResponse(
        message="Verification code sent. Check your email to activate your account.",
        otp=otp if settings.email_debug else None,
    )


@router.post("/verify-email-otp", response_model=UserResponse)
def verify_email_otp(payload: OtpVerificationRequest, db: DbSession):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user:
        raise HTTPException(status_code=404, detail="No signup request was found for this email")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="This email address has already been verified")
    if not user.otp_code or not user.otp_expiry:
        raise HTTPException(status_code=400, detail="No active verification code. Request a new code.")

    expiry = user.otp_expiry
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry < datetime.now(timezone.utc):
        user.otp_code = None
        user.otp_expiry = None
        db.commit()
        raise HTTPException(status_code=400, detail="This verification code has expired. Request a new code.")
    if not secrets.compare_digest(user.otp_code, hash_otp(payload.otp)):
        raise HTTPException(status_code=400, detail="The verification code is incorrect")

    user.is_verified = True
    user.otp_code = None
    user.otp_expiry = None
    user.wallet = Wallet()
    db.commit()
    db.refresh(user)
    return user


@router.post("/resend-otp", response_model=OtpDispatchResponse)
def resend_otp(payload: ResendOtpRequest, db: DbSession):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user:
        raise HTTPException(status_code=404, detail="No signup request was found for this email")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="This email address has already been verified")
    otp = issue_otp(user, db)
    return OtpDispatchResponse(
        message="A new verification code has been sent to your email.",
        otp=otp if settings.email_debug else None,
    )


@router.post("/forgot-password", response_model=OtpDispatchResponse)
def forgot_password(payload: ForgotPasswordRequest, db: DbSession):
    """Issue a reset code without exposing whether an email has an account."""
    user = db.scalar(select(User).where(User.email == payload.email))
    generic_response = OtpDispatchResponse(
        message="If an active account exists for this email, a password reset code has been sent."
    )
    if not user or not user.is_verified:
        return generic_response
    otp = issue_password_reset_otp(user, db)
    return OtpDispatchResponse(
        message=generic_response.message,
        otp=otp if settings.email_debug else None,
    )


@router.post("/reset-password", response_model=OtpDispatchResponse)
def reset_password(payload: ResetPasswordRequest, db: DbSession):
    logger.info(
        "Reset password request: email=%s new_password_chars=%d new_password_bytes=%d",
        payload.email,
        len(payload.new_password),
        len(payload.new_password.encode("utf-8")),
    )
    validate_password(payload.new_password)
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not user.is_verified:
        raise HTTPException(status_code=400, detail="The reset code or email address is invalid")
    if not user.password_reset_otp_code or not user.password_reset_otp_expiry:
        raise HTTPException(status_code=400, detail="No active password reset code. Request a new code.")

    expiry = user.password_reset_otp_expiry
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry < datetime.now(timezone.utc):
        user.password_reset_otp_code = None
        user.password_reset_otp_expiry = None
        db.commit()
        raise HTTPException(status_code=400, detail="This password reset code has expired. Request a new code.")
    if not secrets.compare_digest(user.password_reset_otp_code, hash_otp(payload.otp)):
        raise HTTPException(status_code=400, detail="The password reset code is incorrect")

    user.password_hash = hash_password(payload.new_password)
    user.password_reset_otp_code = None
    user.password_reset_otp_expiry = None
    db.commit()
    return OtpDispatchResponse(message="Password reset successful. You can now sign in.")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession, response: Response):
    logger.info(
        "Login request: email=%s password_chars=%d password_bytes=%d",
        payload.email,
        len(payload.password),
        len(payload.password.encode("utf-8")),
    )
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verify your email address before signing in")
    return create_token_pair(user, db, response)


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(db: DbSession, response: Response, refresh_token: str | None = Cookie(default=None)):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing")
    current = refresh_token_record(refresh_token, db)
    current.revoked_at = utc_now()
    return create_token_pair(current.user, db, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    db: DbSession,
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
):
    if refresh_token:
        try:
            refresh_token_record(refresh_token, db).revoked_at = utc_now()
            db.commit()
        except HTTPException:
            # Logout is idempotent: clear a stale client cookie without revealing token state.
            pass
    revoke_access_token(authorization, db)
    db.commit()
    response.delete_cookie(key="refresh_token", path="/")
