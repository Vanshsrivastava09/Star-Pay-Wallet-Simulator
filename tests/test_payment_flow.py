from tests.conftest import auth_header


def signup(client, email: str, name: str = "Test User"):
    response = client.post("/auth/signup", json={"email": email, "full_name": name, "password": "securepass123"})
    assert response.status_code == 201
    verification = client.post("/auth/verify-email-otp", json={"email": email, "otp": "123456"})
    assert verification.status_code == 200
    return response


def test_root_serves_frontend(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Northstar Pay" in response.text


def test_signup_login_and_wallet(client):
    assert signup(client, "alice@example.com", "Alice").status_code == 201
    headers = auth_header(client, "alice@example.com", "securepass123")

    response = client.get("/wallet", headers=headers)
    assert response.status_code == 200
    assert float(response.json()["balance"]) == 0.0


def test_email_must_be_verified_before_login(client):
    response = client.post("/signup", json={"email": "pending@example.com", "password": "securepass123"})
    assert response.status_code == 201
    login = client.post("/auth/login", json={"email": "pending@example.com", "password": "securepass123"})
    assert login.status_code == 403
    assert "Verify your email" in login.json()["detail"]

    verification = client.post("/verify-email-otp", json={"email": "pending@example.com", "otp": "123456"})
    assert verification.status_code == 200
    assert verification.json()["email"] == "pending@example.com"


def test_add_money_and_transaction_history(client):
    signup(client, "alice@example.com")
    headers = auth_header(client, "alice@example.com", "securepass123")

    response = client.post("/wallet/add-money", headers=headers, json={"amount": "125.50", "description": "Initial funding"})
    assert response.status_code == 200
    assert float(response.json()["balance"]) == 125.5

    response = client.get("/wallet/transactions", headers=headers)
    assert response.status_code == 200
    item = response.json()[0]
    assert item["transaction_type"] == "deposit"
    assert float(item["amount"]) == 125.5


def test_transfer_creates_balanced_ledger_entries(client):
    signup(client, "alice@example.com", "Alice")
    signup(client, "bob@example.com", "Bob")
    alice_headers = auth_header(client, "alice@example.com", "securepass123")
    bob_headers = auth_header(client, "bob@example.com", "securepass123")
    client.post("/wallet/add-money", headers=alice_headers, json={"amount": "100.00"})

    response = client.post("/wallet/transfer", headers=alice_headers, json={
        "recipient_email": "bob@example.com", "amount": "40.00", "description": "Lunch split", "password": "securepass123"
    })
    assert response.status_code == 201
    assert float(response.json()["sender_balance"]) == 60.0
    assert response.json()["status"] == "SUCCESS"
    assert response.json()["transaction_id"]

    assert float(client.get("/wallet", headers=bob_headers).json()["balance"]) == 40.0
    alice_history = client.get("/wallet/transactions", headers=alice_headers).json()
    bob_history = client.get("/wallet/transactions", headers=bob_headers).json()
    assert alice_history[0]["transaction_type"] == "transfer_out"
    assert bob_history[0]["transaction_type"] == "transfer_in"
    assert alice_history[0]["reference"] == bob_history[0]["reference"]
    assert alice_history[0]["transaction_id"] == bob_history[0]["transaction_id"]
    assert alice_history[0]["status"] == "SUCCESS"


def test_transfer_rejects_insufficient_balance(client):
    signup(client, "alice@example.com")
    signup(client, "bob@example.com")
    headers = auth_header(client, "alice@example.com", "securepass123")

    response = client.post("/wallet/transfer", headers=headers, json={
        "recipient_email": "bob@example.com", "amount": "1.00", "password": "securepass123"
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient wallet balance"
    history = client.get("/wallet/transactions", headers=headers).json()
    assert history[0]["status"] == "FAILED"


def test_transfer_requires_password_confirmation(client):
    signup(client, "alice@example.com")
    signup(client, "bob@example.com")
    headers = auth_header(client, "alice@example.com", "securepass123")
    client.post("/wallet/add-money", headers=headers, json={"amount": "10.00"})

    response = client.post("/wallet/transfer", headers=headers, json={
        "recipient_email": "bob@example.com", "amount": "1.00", "password": "wrong-password"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Password confirmation is incorrect"


def test_merchant_payment_history_and_refund(client):
    signup(client, "owner@example.com", "Merchant Owner")
    signup(client, "payer@example.com", "Payer")
    owner_headers = auth_header(client, "owner@example.com", "securepass123")
    payer_headers = auth_header(client, "payer@example.com", "securepass123")

    merchant_response = client.post("/merchants", headers=owner_headers, json={
        "name": "Corner Coffee", "email": "payments@cornercoffee.example"
    })
    assert merchant_response.status_code == 201
    merchant_id = merchant_response.json()["id"]

    client.post("/wallet/add-money", headers=payer_headers, json={"amount": "50.00"})
    payment_response = client.post(f"/merchants/{merchant_id}/pay", headers=payer_headers, json={
        "amount": "20.00", "password": "securepass123", "description": "Morning coffee"
    })
    assert payment_response.status_code == 201
    payment = payment_response.json()
    assert payment["status"] == "SUCCESS"
    assert float(client.get("/wallet", headers=payer_headers).json()["balance"]) == 30.0

    history = client.get(f"/merchants/{merchant_id}/payments", headers=owner_headers)
    assert history.status_code == 200
    assert history.json()[0]["id"] == payment["id"]

    refund_response = client.post(f"/merchant-payments/{payment['id']}/refund", headers=payer_headers, json={
        "password": "securepass123"
    })
    assert refund_response.status_code == 200
    assert refund_response.json()["status"] == "REFUNDED"
    assert float(client.get("/wallet", headers=payer_headers).json()["balance"]) == 50.0


def test_password_reset_replaces_old_password(client):
    signup(client, "alice@example.com")

    response = client.post("/forgot-password", json={"email": "alice@example.com"})
    assert response.status_code == 200
    assert "reset code" in response.json()["message"]

    response = client.post("/reset-password", json={
        "email": "alice@example.com", "otp": "123456", "new_password": "newsecurepass123"
    })
    assert response.status_code == 200
    assert client.post("/auth/login", json={"email": "alice@example.com", "password": "securepass123"}).status_code == 401
    assert client.post("/auth/login", json={"email": "alice@example.com", "password": "newsecurepass123"}).status_code == 200


def test_refresh_tokens_rotate_and_logout_revokes_session(client):
    signup(client, "alice@example.com")
    login = client.post("/auth/login", json={"email": "alice@example.com", "password": "securepass123"})
    assert login.status_code == 200
    first_access_token = login.json()["access_token"]
    first_refresh_token = client.cookies.get("refresh_token")
    assert first_refresh_token

    refreshed = client.post("/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"] != first_access_token
    assert client.cookies.get("refresh_token") != first_refresh_token

    logout = client.post("/auth/logout", headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"})
    assert logout.status_code == 204
    assert client.post("/auth/refresh").status_code == 401
    assert client.get("/wallet", headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"}).status_code == 401
