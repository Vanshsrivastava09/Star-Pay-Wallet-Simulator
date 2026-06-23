from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, merchants, wallets
from app.core.config import settings
from app.db.database import Base, engine, ensure_user_verification_columns

Base.metadata.create_all(bind=engine)
ensure_user_verification_columns()

app = FastAPI(
    title="Payment Gateway Simulator",
    version="1.0.0",
    description="A JWT-protected payment gateway simulator with wallets and transfers.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router)
app.include_router(wallets.router)
app.include_router(merchants.router)
app.include_router(merchants.payments_router)

# Root-level aliases preserve the API names used by clients that do not prefix
# auth routes, while the original /auth/... routes remain fully supported.
app.add_api_route("/signup", auth.signup, methods=["POST"], response_model=auth.OtpDispatchResponse, status_code=201, tags=["Authentication"])
app.add_api_route("/verify-email-otp", auth.verify_email_otp, methods=["POST"], response_model=auth.UserResponse, tags=["Authentication"])
app.add_api_route("/resend-otp", auth.resend_otp, methods=["POST"], response_model=auth.OtpDispatchResponse, tags=["Authentication"])
app.add_api_route("/forgot-password", auth.forgot_password, methods=["POST"], response_model=auth.OtpDispatchResponse, tags=["Authentication"])
app.add_api_route("/reset-password", auth.reset_password, methods=["POST"], response_model=auth.OtpDispatchResponse, tags=["Authentication"])
app.add_api_route("/refresh", auth.refresh_access_token, methods=["POST"], response_model=auth.TokenResponse, tags=["Authentication"])
app.add_api_route("/logout", auth.logout, methods=["POST"], status_code=204, tags=["Authentication"])

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(static_dir / "index.html")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
