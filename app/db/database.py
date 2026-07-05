from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
try:
    engine = create_engine(settings.database_url, connect_args=connect_args)
except ModuleNotFoundError as exc:
    missing = str(exc).split("'", 2)[1] if "'" in str(exc) else "database driver"
    raise RuntimeError(
        f"Unable to create the database engine because the driver '{missing}' is missing. "
        "For PostgreSQL, install the driver with 'pip install psycopg[binary]'. "
        "For SQLite, use a URL like 'sqlite:///./payment_gateway.db'."
    ) from exc
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_user_verification_columns() -> None:
    """Safely add OTP columns for databases created before email verification existed.

    New deployments receive these fields through ``Base.metadata.create_all``. This
    lightweight compatibility step keeps the local SQLite database usable without
    destroying existing users. Use an Alembic migration for managed production DBs.
    """
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("users")}
    statements = []
    dialect = engine.dialect.name
    # Use dialect-appropriate SQL for altering existing databases
    if "is_verified" not in existing:
        if dialect == "sqlite":
            statements.append("ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 0")
        else:
            statements.append("ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT FALSE")
    if "otp_code" not in existing:
        statements.append("ALTER TABLE users ADD COLUMN otp_code VARCHAR(64)")
    if "otp_expiry" not in existing:
        if dialect == "sqlite":
            statements.append("ALTER TABLE users ADD COLUMN otp_expiry DATETIME")
        else:
            statements.append("ALTER TABLE users ADD COLUMN otp_expiry TIMESTAMP WITH TIME ZONE")
    if "password_reset_otp_code" not in existing:
        statements.append("ALTER TABLE users ADD COLUMN password_reset_otp_code VARCHAR(64)")
    if "password_reset_otp_expiry" not in existing:
        if dialect == "sqlite":
            statements.append("ALTER TABLE users ADD COLUMN password_reset_otp_expiry DATETIME")
        else:
            statements.append("ALTER TABLE users ADD COLUMN password_reset_otp_expiry TIMESTAMP WITH TIME ZONE")
    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}
    transaction_statements = []
    if "transaction_id" not in transaction_columns:
        transaction_statements.append("ALTER TABLE transactions ADD COLUMN transaction_id VARCHAR(32)")
    if "status" not in transaction_columns:
        # Ledger rows that existed before this feature represent completed work.
        transaction_statements.append("ALTER TABLE transactions ADD COLUMN status VARCHAR(10) NOT NULL DEFAULT 'SUCCESS'")
    if transaction_statements:
        with engine.begin() as connection:
            for statement in transaction_statements:
                connection.execute(text(statement))

    if "merchants" in inspector.get_table_names():
        merchant_columns = {column["name"] for column in inspector.get_columns("merchants")}
        if "balance" not in merchant_columns:
            if engine.dialect.name == "sqlite":
                with engine.begin() as connection:
                    connection.execute(text("ALTER TABLE merchants ADD COLUMN balance NUMERIC(14, 2) NOT NULL DEFAULT 0"))
            else:
                with engine.begin() as connection:
                    connection.execute(text("ALTER TABLE merchants ADD COLUMN balance NUMERIC(14, 2) NOT NULL DEFAULT 0"))
