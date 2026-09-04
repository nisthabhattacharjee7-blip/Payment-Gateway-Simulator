
### 3. Create the database and run migrations

```bash
psql -U postgres -c "CREATE DATABASE payment_gateway_db;"
alembic upgrade head
```

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive API documentation, or `GET /health` for a liveness check.

---

## Running Tests

```bash
pytest tests/ -v
```

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