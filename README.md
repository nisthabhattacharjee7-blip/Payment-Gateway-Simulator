# Payment Gateway Simulator

A backend simulation of a payment gateway — modeled after Razorpay, Stripe, Cashfree, and Juspay — built with FastAPI, SQLAlchemy 2.0, and PostgreSQL. It models the parts of a payment system that are actually hard to get right: state-machine-governed payment lifecycles, idempotent request handling, double-entry ledger bookkeeping, settlement batching, and HMAC-signed webhook delivery with retry/backoff.

**Live API:** [payment-gateway-simulator-1.onrender.com/docs](https://payment-gateway-simulator-1.onrender.com/docs) · [health check](https://payment-gateway-simulator-1.onrender.com/health)
> Hosted on Render's free tier — the service spins down after periods of inactivity, so the first request may take 30-60s to respond while it wakes up. Subsequent requests are fast.

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

**State machine–driven payment lifecycle**
Payments move through `created → authorized → captured → settled`, with `failed`, `refunded`, and `partially_refunded` as branch states. Every transition is checked against an explicit rules map before it's applied — illegal moves (e.g. capturing a payment that's already failed) are rejected in the service layer with a `409`, not silently allowed.

**Double-entry ledger bookkeeping**
Every financial event (capture, refund, settlement) writes matching debit and credit entries to an append-only ledger table, one pair per payment. Debits equal credits system-wide; entries are never edited or deleted, only reversed with new entries — mirroring how real audit trails work.

**Settlement batching**
A dedicated `settlements` resource bundles all of a merchant's captured-but-unsettled payments into a batch, moves them to `settled`, and writes a per-payment ledger movement for each one in the batch — so every payment in a settlement has its own traceable debit/credit pair, not just a single lump entry for the batch. In production this would run on a schedule; here it's manually triggered via `POST /settlements/batch`, which is called out explicitly below rather than glossed over.

**Idempotency protection**
Duplicate requests (e.g. a merchant's network retry) are detected via an `Idempotency-Key` header. The request body is hashed and compared server-side: an identical retry replays the original stored response, while the same key reused with a *different* body is rejected outright rather than silently treated as a valid retry.

**HMAC-signed webhook delivery with exponential backoff**
Payment and refund status changes are pushed to a merchant's webhook URL, signed per-merchant with HMAC so the merchant can verify authenticity. Failed deliveries retry with exponentially increasing delay, capped at a maximum delay and abandoned after a maximum attempt count.

**Hashed API key authentication**
Merchant API keys are generated with `secrets.token_urlsafe`, hashed before storage, and compared using constant-time comparison to prevent timing attacks. The raw key is returned to the merchant exactly once, at creation.

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

    app/
    ├── config/       # enums (PaymentStatus, RefundStatus, Currency, LedgerEntryType,
    │                 #   WebhookStatus, SettlementStatus) and settings
    ├── db/           # SQLAlchemy engine/session setup
    ├── models/       # ORM models — merchant, payment, refund, ledger_entry, wallet,
    │                 #   webhook_log, settlement, idempotency_key
    ├── schemas/      # Pydantic models — the API request/response shape
    ├── services/     # business logic: state machine, ledger, payments, settlement,
    │                 #   webhooks, idempotency
    ├── middlewares/  # auth (API key) and idempotency dependencies
    ├── routers/      # FastAPI route definitions (merchants, payments, refunds,
    │                 #   settlements, webhooks)
    └── main.py       # app entrypoint, router registration, exception handlers

Models and schemas are kept deliberately separate: models describe what's stored in the database, schemas describe what the API accepts and returns. Business rules — state transitions, refund limits, ledger balancing, settlement eligibility — live entirely in `services/`, so routers stay thin and only handle HTTP concerns: auth, request parsing, status codes, and dispatching webhook events after a state change commits.

---

## Setup

**Requirements:** Python 3.13+, PostgreSQL 18+

### 1. Clone and install dependencies

    git clone https://github.com/nisthabhattacharjee7-blip/Payment-Gateway-Simulator.git
    cd Payment-Gateway-Simulator
    python -m venv venv
    venv\Scripts\activate          # Windows
    pip install -r requirements.txt

### 2. Configure environment

Create a `.env` file in the project root:

    DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/payment_gateway_db

### 3. Create the database and run migrations

    psql -U postgres -c "CREATE DATABASE payment_gateway_db;"
    alembic upgrade head

### 4. Run the server

    uvicorn app.main:app --reload

Visit `http://127.0.0.1:8000/docs` for interactive API documentation, or `GET /health` for a liveness check.

---

## Running Tests

    pytest tests/ -v

41 tests across 6 files:

| File | Covers |
|---|---|
| `test_payment.py` | State machine transition rules (valid, invalid, terminal-state rejection) and payment/refund service behavior |
| `test_ledger.py` | Double-entry correctness on capture and refund — debits always equal credits, wallet balances update correctly |
| `test_settlement.py` | Settlement batch creation, eligibility filtering, per-payment ledger balancing, and idempotent re-batching |
| `test_webhook.py` | Webhook payload construction, exponential backoff scheduling, and max-attempt failure handling |
| `test_hmac.py` | API key generation/hashing/verification and webhook payload signing |
| `test_idempotency.py` | Idempotency key hashing, lookup behavior, and duplicate-key/different-body rejection |

Tests run against the configured database inside a per-test rolled-back transaction (see `conftest.py`).

> **Note:** if you've added the settlement or idempotency regression tests from a self-audit, re-run `pytest tests/ -v | tail -1` and update the count above to match — don't leave a stale number here, it's the first thing a reviewer checks against the table.

---

## API Overview

| Endpoint | Method | Description |
|---|---|---|
| `/merchants` | `POST` | Register a merchant, returns API key once |
| `/merchants/me` | `GET` | Get the authenticated merchant's profile |
| `/payments` | `POST` | Create a payment (idempotency-protected) |
| `/payments/{id}` | `GET` | Fetch a payment by id |
| `/payments/{id}/authorize` | `POST` | Send to simulated bank for authorization |
| `/payments/{id}/capture` | `POST` | Capture an authorized payment, writes ledger entries |
| `/payments/{id}/refunds` | `POST` | Full or partial refund, triggers a webhook event |
| `/settlements/batch` | `POST` | Batch all captured-but-unsettled payments into a settlement |
| `/settlements` | `GET` | List settlement batches for the authenticated merchant |
| `/webhooks` | `GET` | List webhook delivery logs |
| `/webhooks/{id}/retry` | `POST` | Manually trigger a webhook delivery attempt |
| `/health` | `GET` | Liveness check |

All merchant, payment, refund, settlement, and webhook routes (except registration and `/health`) require an `X-API-Key` header, obtained from `POST /merchants`.

---

## Known Limitations

Built as a learning project — a few things are deliberately simplified rather than production-hardened:

- The fake bank processor (`processor_simulator.py`) uses randomized outcomes rather than a real payment network integration.
- Settlement batching and webhook retries are triggered manually via their respective endpoints; there's no background scheduler polling for due batches or retries.
- Tests run against the configured PostgreSQL database inside a rolled-back transaction, rather than a fully isolated test database or container.
- No rate limiting or request-size limits on public-facing endpoints.
- A payment that times out during authorization has no reconciliation path — it stays in `created` indefinitely rather than moving to a retryable or expired state.
- Found and fixed during a self-audit: idempotency requests weren't hashing the real request body (so same-key/different-body reuse wasn't actually detected), and settlement ledger entries were attributed only to the first payment in a batch instead of one per payment. Both are fixed as of the current commit; see commit history for the specific changes.

---

## What I Learned

- Why a data-driven state machine (a transition map plus a guard function) is cleaner and more testable than scattered if/else validation.
- Why double-entry bookkeeping requires two entries per transaction, and why ledger tables should be append-only — and why that guarantee has to be enforced per-transaction, not just per-batch, or it silently breaks under batching.
- Why idempotency needs to be enforced at the request layer, not just the service layer, to correctly handle concurrent duplicate requests — and why hashing the actual request body (not just the key) matters for catching key reuse with a different payload.
- Why `hmac.compare_digest` matters when comparing secrets, and why API keys should be hashed like passwords rather than stored in plain text.
- The difference between "settled" as a status flag and settlement as its own auditable entity — and why real gateways model it as a batch with its own ledger movement rather than just flipping a payment's status.
- The importance of keeping ORM relationships (`back_populates`) consistent on both sides — and how SQLAlchemy fails loudly, but not always clearly, when they aren't.
- The value of re-reading your own service-layer code adversarially after it's "done" — the settlement and idempotency bugs above passed code review by me the first time; they only surfaced under a deliberate audit.