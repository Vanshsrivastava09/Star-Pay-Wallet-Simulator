import os


class Settings:
    """Application settings loaded from environment variables."""

    app_name = "Payment Gateway Simulator"
    secret_key = os.getenv("SECRET_KEY", "development-only-change-me-before-production")
    algorithm = "HS256"
    access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    database_url = os.getenv("DATABASE_URL", "sqlite:///./payment_gateway.db")
    cors_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
        if origin.strip()
    ]
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("GMAIL_ADDRESS", "")
    smtp_password = os.getenv("GMAIL_APP_PASSWORD", "")
    smtp_from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username)
    otp_expire_minutes = int(os.getenv("OTP_EXPIRE_MINUTES", "5"))


settings = Settings()
