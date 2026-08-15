# Payment Gateway Simulator

A backend simulation of a payment gateway — modeled after Razorpay, Stripe, Cashfree, and Juspay — built with FastAPI, SQLAlchemy, and PostgreSQL. Built as a deep-dive learning project into production-grade backend engineering: payment lifecycle state machines, idempotency, double-entry ledger bookkeeping, webhook delivery with exponential backoff, and API-key authentication.

---

## Table of Contents

- [What This Demonstrates](#what-this-demonstrates)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Setup](#setup)
- [Running Tests](#running-tests)
- [API Overview](#api-overview)
- [Known Limitations](#known-limitations)
- [What I Learned](#what-i-learned)

---

## What This Demonstrates

This isn't a CRUD app — it models the actual hard problems a real payment gateway has to solve.

**State machine–driven payment lifecycle**
Payments move through `created → authorized → captured → settled`, with `failed` and `refunded` / `partially_refunded` branches. Every transition is validated against an explicit rules map before it's applied, so an illegal state change — like capturing an already-failed payment — is rejected at the service layer, not silently allowed.

**Double-entry ledger bookkeeping**
Every financial event (capture, refund) writes matching debit and credit entries to an append-only ledger table. Debits always equal credits across the system; nothing is ever edited or deleted, only reversed with new entries — mirroring how real financial audit trails work.

**Idempotency protection**
Duplicate requests — for example, from a merchant's network retry — are detected via an `Idempotency-Key` header, hashed and matched server-side, and replayed from a cached response instead of being processed twice.

**Webhook delivery with exponential backoff**
Payment status changes are pushed to a merchant's webhook URL. Failed deliveries are retried with exponentially increasing delays (2s, 4s, 8s...), capped at a maximum delay and eventually abandoned after a maximum attempt count.

**Hashed API key authentication**
Merchant API keys are generated with `secrets.token_urlsafe`, hashed with SHA-256 before storage, and compared using constant-time comparison to prevent timing attacks. The raw key is shown to the merchant exactly once, at creation.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| ORM | SQLAlchemy 2.0 (`Mapped` / `mapped_column` declarative style) |
| Database | PostgreSQL |
| Migrations | Alembic |
| Validation | Pydantic |
| Testing | pytest |
| HTTP client | httpx (async, for webhook delivery) |

---

## Architecture

```
app/
├── config/       # enums (PaymentStatus, Currency, etc.) and settings
├── db/           # SQLAlchemy engine/session setup
├── models/       # ORM models — the database shape
├── schemas/      # Pydantic models — the API request/response shape
├── services/     # business logic: state machine, ledger, payments, webhooks
├── middlewares/  # auth (API key) and idempotency dependencies
├── routers/      # FastAPI route definitions
└── main.py       # app entrypoint, router registration, exception handlers
```

Models and schemas are deliberately kept separate: models describe what's stored in the database, schemas describe what the API accepts and returns. Business rules — state transitions, refund limits, ledger balancing — live entirely in the `services/` layer, so routers stay thin and only handle HTTP concerns like auth, request parsing, and status codes.

---

## Setup

**Requirements:** Python 3.13+, PostgreSQL 18+

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd payment-gateway-simulator
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/payment_gateway_db
```

### 3. Create the database and run migrations

```bash
psql -U postgres -c "CREATE DATABASE payment_gateway_db;"
alembic upgrade head
```

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for the interactive API documentation.

---

## Running Tests

```bash
pytest tests/ -v
```

20 tests covering:
- State machine transition rules, including rejection of illegal transitions
- Double-entry ledger correctness — verifying debits always equal credits
- Idempotency key hashing and lookup behavior
- Webhook exponential backoff scheduling and max-attempt handling

---

## API Overview

| Endpoint | Method | Description |
|---|---|---|
| `/merchants` | `POST` | Register a merchant, returns API key once |
| `/merchants/me` | `GET` | Get the authenticated merchant's profile |
| `/payments` | `POST` | Create a payment (idempotency-protected) |
| `/payments/{id}/authorize` | `POST` | Send to simulated bank for authorization |
| `/payments/{id}/capture` | `POST` | Capture an authorized payment, writes ledger entries |
| `/payments/{id}/refunds` | `POST` | Full or partial refund |
| `/webhooks` | `GET` | List webhook delivery logs |
| `/webhooks/{id}/retry` | `POST` | Manually trigger a webhook delivery attempt |

All payment, refund, and webhook routes require an `X-API-Key` header, obtained from `POST /merchants`.

---

## Known Limitations

Built as a learning project — a few things are deliberately simplified rather than production-hardened:

- The fake bank processor (`processor_simulator.py`) uses randomized outcomes (80% success / 15% decline / 5% timeout) rather than a real payment network integration.
- Webhook delivery retries must be triggered manually via the `/retry` endpoint; there's no background scheduler polling for due retries.
- Tests run against the real configured database inside a rolled-back transaction, rather than a fully isolated test database.

---

## What I Learned

- Why a data-driven state machine (a transition map plus a guard function) is cleaner and more testable than scattered if/else validation.
- Why double-entry bookkeeping requires two entries per transaction, and why ledger tables should be append-only.
- Why idempotency needs to be enforced at the request layer, not just the service layer, to correctly handle concurrent duplicate requests.
- Why `hmac.compare_digest` matters when comparing secrets, and why API keys should be hashed like passwords rather than stored in plain text.
- The importance of keeping ORM relationships (`back_populates`) consistent on both sides — and how SQLAlchemy fails loudly, but not always clearly, when they aren't.
