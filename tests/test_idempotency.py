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