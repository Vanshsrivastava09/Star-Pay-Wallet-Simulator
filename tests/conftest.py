import os

os.environ["DATABASE_URL"] = "sqlite:///./test_payment_gateway.db"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-thirty-two-bytes"

import pytest
from fastapi.testclient import TestClient

from app.db.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_database(monkeypatch):
    monkeypatch.setattr("app.api.auth.generate_otp", lambda: "123456")
    monkeypatch.setattr("app.api.auth.send_otp_email", lambda recipient, otp: None)
    monkeypatch.setattr("app.api.auth.send_password_reset_otp", lambda recipient, otp: None)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth_header(client, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
