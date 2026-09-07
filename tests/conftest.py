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

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
from app.middlewares.auth_middleware import get_current_merchant
from app.middlewares.rate_limiter import limiter

TEST_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    """Provides a database session for a single test, wrapped in a
    transaction that's always rolled back afterward — so tests never
    leave leftover data in the database"""

    connection = engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def test_merchant(db):
    """Creates a merchant for tests that need one, without needing to
    duplicate merchant-creation boilerplate in every test"""

    merchant = Merchant(
        name="Test Merchant",
        email="test@example.com",
        api_key="test_hashed_key",
    )
    db.add(merchant)
    db.flush()
    return merchant


@pytest.fixture()
def client(db, test_merchant):
    """
    A TestClient wired to bypass real DB connections and real API-key
    hashing: get_db is overridden to use this test's rolled-back
    transaction session, and get_current_merchant is overridden to
    return test_merchant directly, since test_merchant.api_key above
    isn't a real hash of any raw key.

    Deliberately NOT using `with TestClient(app) as client:` — that
    form triggers the app's real lifespan, which starts the actual
    APScheduler. Tests don't need the real scheduler running (see
    test_scheduler.py, which calls redrive_due_webhooks directly), and
    starting/stopping it across many tests breaks on repeat runs.
    """
    def override_get_db():
        yield db

    def override_get_current_merchant():
        return test_merchant

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_merchant] = override_get_current_merchant

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """
    slowapi's limiter keeps request counts in memory, shared across the
    whole test session — without this, whichever test runs first
    "uses up" part of the rate limit for every test after it that hits
    the same endpoint.
    """
    limiter.reset()
    yield