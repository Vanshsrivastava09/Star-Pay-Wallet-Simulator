# 🚀 NorthStar Pay - Production Ready Wallet & Payment Gateway Simulator

A production-inspired digital wallet and payment gateway simulator built using FastAPI, PostgreSQL, JWT Authentication, and Email OTP verification.

The project simulates how modern fintech applications handle user onboarding, wallet management, money transfers, transaction ledgers, and secure authentication.

---

# 📸 Demo

🎥 Demo Video: [[Video]](https://drive.google.com/file/d/1wOItP8s9pmc1Al2O82CJYt-hLfA7hQsx/view?usp=sharing)

💻 GitHub Repository:
https://github.com/Vanshsrivastava09/northstar-pay-wallet-simulator

---

# ✨ Features

## 🔐 Authentication
- User Signup & Login
- JWT Authentication
- Email OTP Verification
- Secure Password Hashing
- Protected Routes
- Session Management

## 💳 Wallet System
- Create Wallet
- Add Money
- Check Balance
- Wallet Dashboard

## 💸 Payment Features
- Instant Money Transfer
- Double Entry Ledger System
- Transaction History
- Transaction IDs
- Transaction Status Tracking

## 🗄 Database Features
- PostgreSQL (Neon Database)
- SQLAlchemy ORM
- Alembic Database Migrations

## 📧 Email System
- OTP Verification via Gmail SMTP
- Resend OTP Feature
- Email Verification before Login

## 🐳 DevOps Features
- Dockerized Application
- Environment Variables
- Production Ready Project Structure

---

# 🏗 System Architecture

```
Client (HTML/CSS/JS)
        │
        ▼
    FastAPI Backend
        │
 ┌──────┴───────┐
 │              │
 ▼              ▼
JWT Auth     PostgreSQL
              (Neon)
        │
        ▼
   Transaction Ledger
```

---

# 🛠 Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3 |
| Framework | FastAPI |
| Database | PostgreSQL (Neon) |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Authentication | JWT |
| Email Service | Gmail SMTP |
| Containerization | Docker |
| API Testing | Swagger UI |

---

# 📂 Project Structure

```bash
northstar-pay-wallet-simulator/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── schemas/
│   ├── static/
│   ├── dependencies.py
│   ├── main.py
│   └── models.py
│
├── alembic/
├── tests/
├── Dockerfile
├── requirements.txt
├── README.md
├── .env.example
└── alembic.ini
```

---

# ⚙️ Environment Variables

Create a `.env` file or set environment variables in Render.

```env
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql+psycopg://your-db-url
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
EMAIL_DEBUG=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=your-email-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
OTP_EXPIRE_MINUTES=5
```

Use `EMAIL_DEBUG=true` during initial Render deployment if you do not have SMTP configured. This lets the app return OTP codes directly in the response for testing.

For a production-ready Render deployment, set:

- `DATABASE_URL` to your Postgres connection string
- `COOKIE_SECURE=true`
- `EMAIL_DEBUG=false`
- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=587`
- `GMAIL_ADDRESS=your-email@gmail.com`
- `GMAIL_APP_PASSWORD=your-email-app-password`
- `SMTP_FROM_EMAIL=your-email@gmail.com`

---

# 🚀 Local Setup

## Clone Repository

```bash
git clone https://github.com/Vanshsrivastava09/northstar-pay-wallet-simulator.git
cd northstar-pay-wallet-simulator
```

## Create Virtual Environment

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Linux/Mac

```bash
source .venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run Database Migration

```bash
alembic upgrade head
```

---

## Start Server

```bash
uvicorn app.main:app --reload
```

---

# 📖 API Documentation

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

# 🔒 Security Features

- Password Hashing
- JWT Authentication
- Email Verification
- OTP Expiration
- Environment Variables
- Protected Endpoints
- Session Management

---

# 📈 Future Improvements

- UPI Integration Simulation
- Merchant Dashboard
- Refund APIs
- Payment Gateway APIs
- Webhooks
- Redis Caching
- Rate Limiting
- Docker Compose Deployment
- Kubernetes Deployment
- CI/CD Pipeline

---

# 🎯 Learning Outcomes

This project helped me understand:

- Authentication & Authorization
- REST API Development
- Database Design
- Payment System Architecture
- Secure User Management
- Email Verification Workflows
- PostgreSQL Integration
- Docker Deployment
- Production Backend Development

---

# 👨‍💻 Author

### Vansh Srivastava

B.Tech Computer Science & Communication Engineering  
Kalinga Institute of Industrial Technology (KIIT)  
Graduation Year: 2027

LinkedIn:
https://www.linkedin.com/in/vanshsrivastava09/

GitHub:
https://github.com/Vanshsrivastava09

---

# ⭐ If you liked this project, give it a star!
