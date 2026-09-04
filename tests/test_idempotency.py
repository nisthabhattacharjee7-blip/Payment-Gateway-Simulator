import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
load_dotenv()
from app.db.base import Base
from app.models.merchant import Merchant
from app.models.payment import Payment
from app.models.refund import Refund
from app.models.ledger_entry import LedgerEntry
from app.models.wallet import Wallet
from app.models.webhook_log import WebhookLog
from app.models.idempotency_key import IdempotencyKey

TEST_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    """
    Provides a database session for a single test, wrapped in a
    transaction that's always rolled back afterward — so tests never
    leave leftover data in the database.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture()
def test_merchant(db):
    """
    Creates a merchant for tests that need one, without needing to
    duplicate merchant-creation boilerplate in every test.
    """
    merchant = Merchant(
        name="Test Merchant",
        email="test@example.com",
        api_key="test_hashed_key",
    )
    db.add(merchant)
    db.flush()
    return merchant

def test_reusing_key_with_different_body_is_rejected(client, test_merchant):
    headers = {"X-API-Key": test_merchant.raw_api_key, "Idempotency-Key": "dup-key-1"}

    first = client.post("/payments", json={"amount": 1000, "currency": "INR"}, headers=headers)
    assert first.status_code == 201

    second = client.post("/payments", json={"amount": 999999, "currency": "INR"}, headers=headers)
    assert second.status_code == 422


def test_replay_returns_original_response_body(client, test_merchant):
    headers = {"X-API-Key": test_merchant.raw_api_key, "Idempotency-Key": "dup-key-2"}
    payload = {"amount": 1000, "currency": "INR"}

    first = client.post("/payments", json=payload, headers=headers)
    second = client.post("/payments", json=payload, headers=headers)

    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]