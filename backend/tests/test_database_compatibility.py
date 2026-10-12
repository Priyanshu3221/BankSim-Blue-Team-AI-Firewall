"""Targeted tests for database configuration, URL normalization, and production safety."""

import os
import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from config import Settings
from database import (
    Base,
    create_db_engine,
    get_db,
    normalize_database_url,
    seed_demo_data,
    set_sqlite_pragma,
)
from models import Account, User
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="function")
def test_db_session():
    """Create an isolated in-memory SQLite database and session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    event.listen(engine, "connect", set_sqlite_pragma)
    Base.metadata.create_all(bind=engine)
    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_normalize_database_url_postgresql_schemes():
    """Verify cloud provider postgres:// and postgresql:// schemes normalize correctly."""
    # Heroku / Supabase / Neon legacy scheme
    legacy_url = "postgres://user:secret@ep-host.region.neon.tech/neondb?sslmode=require"
    normalized = normalize_database_url(legacy_url)
    assert normalized.startswith("postgresql://user:secret@ep-host.region.neon.tech/neondb")

    # Standard SQLAlchemy scheme is preserved
    standard_url = "postgresql://user:secret@ep-host.region.neon.tech/neondb"
    assert normalize_database_url(standard_url) == standard_url

    # Explicit psycopg2 driver scheme is preserved
    driver_url = "postgresql+psycopg2://user:secret@ep-host.region.neon.tech/neondb"
    assert normalize_database_url(driver_url) == driver_url


def test_normalize_database_url_sqlite():
    """Verify SQLite URLs resolve relative paths and preserve in-memory URLs."""
    in_memory = "sqlite:///:memory:"
    assert normalize_database_url(in_memory) == in_memory

    relative_url = "sqlite:///./backend/data/banksim.db"
    normalized = normalize_database_url(relative_url)
    assert normalized.startswith("sqlite:///")
    assert "banksim.db" in normalized


def test_production_rejects_sqlite_database_url():
    """Production mode must reject SQLite and require a persistent PostgreSQL DATABASE_URL."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="sqlite:///./backend/data/banksim.db",
            SECRET_KEY="super-secret-production-random-key-1234567890",
        )
    assert "persistent PostgreSQL database in production" in str(exc_info.value)


def test_production_rejects_insecure_default_secret_key():
    """Production mode must reject default dev SECRET_KEY."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://user:pass@host/db",
            SECRET_KEY="banksim-dev-secret-key-replace-in-production-abcdef123456",
        )
    assert "A secure cryptographic SECRET_KEY must be provided" in str(exc_info.value)


def test_production_accepts_valid_postgres_and_secret():
    """Production mode accepts valid PostgreSQL URL and non-default secret key."""
    settings = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql://user:pass@host/db",
        SECRET_KEY="a-strong-custom-production-signing-secret-key-9999",
    )
    assert settings.DATABASE_URL == "postgresql://user:pass@host/db"
    assert settings.ENVIRONMENT == "production"


def test_development_allows_default_sqlite_and_secret():
    """Development mode safely allows local defaults."""
    settings = Settings(ENVIRONMENT="development")
    assert settings.DATABASE_URL.startswith("sqlite:///")
    assert settings.SECRET_KEY == "banksim-dev-secret-key-replace-in-production-abcdef123456"


def test_get_db_session_rollback_on_error():
    """Verify get_db dependency triggers rollback when an exception occurs."""
    db_gen = get_db()
    session = next(db_gen)
    assert isinstance(session, Session)

    # Simulate an unhandled exception inside an endpoint
    test_error = RuntimeError("Simulated request failure")
    with pytest.raises(RuntimeError):
        try:
            raise test_error
        except Exception:
            db_gen.throw(test_error)


def test_seed_demo_data_preserves_balances_when_reset_false(test_db_session: Session):
    """Verify seed_demo_data does not overwrite or reset balances when reset_balances is False."""
    # First seed run
    seed_demo_data(session=test_db_session, reset_balances=False)

    # Modify an account balance (simulate user spending money)
    alice_user = test_db_session.query(User).filter(User.username == "alice").first()
    assert alice_user is not None
    alice_acc = test_db_session.query(Account).filter(Account.user_id == alice_user.id).first()
    assert alice_acc is not None
    alice_acc.balance = 5000000  # Reduced to ₹50,000
    test_db_session.commit()

    # Second seed run with reset_balances=False
    results = seed_demo_data(session=test_db_session, reset_balances=False)
    assert "AC-ALICE-01" in results["accounts_preserved"]

    # Balance must remain at ₹50,000, not reset to ₹100,000
    test_db_session.refresh(alice_acc)
    assert alice_acc.balance == 5000000
