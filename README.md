# Payment Gateway Simulator

A production-style FastAPI payment gateway simulator with a responsive web dashboard, JWT authentication, user wallets, deposits, transfers, and an auditable transaction ledger. It is designed for local development and API integration practice—not for processing real payments.

## Features

- JWT signup and login
- Responsive browser dashboard served directly by FastAPI (no separate frontend build)
- One SQLite-backed wallet per user
- Authenticated wallet balance and add-money endpoints
- Atomic internal transfers with matching debit/credit ledger entries
- Transaction history with pagination
- Interactive Swagger UI and ReDoc
- Docker image and pytest API tests

## Project layout

```
app/
  api/          Route handlers
  core/         Configuration and JWT/password utilities
  db/           SQLAlchemy engine and session handling
  schemas/      Pydantic request/response contracts
  models.py     SQLAlchemy models
  main.py       Application entry point
tests/          Core API tests
```

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The web app starts at `http://127.0.0.1:8000`. Create an account, add simulated funds, transfer money to another registered user, and inspect the live ledger from the dashboard. Swagger documentation is at `http://127.0.0.1:8000/docs`; ReDoc is at `http://127.0.0.1:8000/redoc`.

For non-development use, set a strong `SECRET_KEY` and an appropriate `DATABASE_URL` before starting. See `.env.example` for the available variables.

## Email verification setup

New accounts are inactive until their email address is verified with a six-digit OTP. Codes expire after five minutes and are stored as hashes in the database.

The same five-minute, single-use OTP protection is used for password recovery. The web app has **Forgot password** and **Reset password** views, and the API exposes `/auth/forgot-password`, `/auth/reset-password` plus root-level `/forgot-password` and `/reset-password` aliases.

## Authentication sessions

Login returns a short-lived access JWT and sets a rotating refresh JWT in an `HttpOnly`, `SameSite=Lax` cookie. Refresh-token database records contain only a SHA-256 hash, expiry, and revocation timestamp. `POST /auth/refresh` rotates the session, while `POST /auth/logout` revokes it and clears the cookie. The frontend refreshes an expired access token automatically.

Set `COOKIE_SECURE=true` when deploying over HTTPS. Keep it `false` only for local HTTP development.

To send verification email with Gmail, enable two-step verification on the Gmail account, create a Google **App Password**, then set these environment variables before starting the server:

```powershell
$env:GMAIL_ADDRESS="your-gmail-address@gmail.com"
$env:GMAIL_APP_PASSWORD="your-16-character-google-app-password"
$env:SECRET_KEY="use-a-long-random-secret-in-production"
uvicorn app.main:app --reload
```

The API supports both the existing `/auth/signup`, `/auth/verify-email-otp`, and `/auth/resend-otp` paths and the root aliases `/signup`, `/verify-email-otp`, and `/resend-otp`.

## Core endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/auth/signup` | Create a user and wallet |
| POST | `/auth/login` | Obtain a bearer token |
| GET | `/wallet` | Read the authenticated user's balance |
| POST | `/wallet/add-money` | Credit the authenticated user's wallet |
| POST | `/wallet/transfer` | Send money to another user by email |
| GET | `/wallet/transactions` | Read ledger history (`limit`, `offset`) |
| POST | `/merchants` | Create a merchant |
| GET | `/merchants` | List active merchants |
| POST | `/merchants/{merchant_id}/pay` | Pay a merchant from a wallet |
| GET | `/merchants/{merchant_id}/payments` | Merchant-owner payment history |
| GET | `/merchant-payments` | Current user's merchant payments |
| POST | `/merchant-payments/{payment_id}/refund` | Refund a successful merchant payment |
| GET | `/health` | Health probe |

Protected endpoints accept `Authorization: Bearer <access_token>`. The dashboard manages this automatically for its current browser session.

Transfers require the sender's password in addition to the bearer token. Each transfer receives a shared `transaction_id`; both ledger sides settle as `SUCCESS`. Insufficient-balance attempts are recorded as `FAILED` without changing balances. The transaction model also supports `PENDING` while a transfer is being settled.

## Merchant simulation

Authenticated users can create merchants, pay any active merchant from their wallet, inspect payments for merchants they own, and refund their own successful merchant payment. Merchant payments use `PENDING`, `SUCCESS`, `FAILED`, and `REFUNDED` states. A refund is a compensating wallet ledger credit and may only be applied once.

## Example flow

```bash
curl -X POST http://127.0.0.1:8000/auth/signup -H "Content-Type: application/json" -d '{"email":"alice@example.com","full_name":"Alice","password":"securepass123"}'
curl -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d '{"email":"alice@example.com","password":"securepass123"}'
```

Use the returned `access_token` in Swagger's **Authorize** dialog or as a bearer token in subsequent requests.

## Run tests

```bash
pytest
```

## Docker

```bash
docker build -t payment-gateway-simulator .
docker run --rm -p 8000:8000 -e SECRET_KEY="replace-with-a-long-random-secret" payment-gateway-simulator
```

The default SQLite file is stored inside the container. Mount a volume and set `DATABASE_URL` if you need persistence across container recreation.
