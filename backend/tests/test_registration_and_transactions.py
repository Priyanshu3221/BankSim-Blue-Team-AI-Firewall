"""Automated tests for BankSim Registration, Demo Account Provisioning, and Customer Transaction Ledger."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db, set_sqlite_pragma
from backend.main import app
from backend.models import Account, Transaction, User
from backend.security.login_tracker import login_tracker
from backend.security.passwords import hash_password
from backend.security.tokens import create_access_token
from backend.services.ai_providers import MockAIProvider
from backend.services.ai_threat_analyzer import ai_threat_analyzer


@pytest.fixture
def test_setup():
    """Isolated in-memory SQLite database and TestClient for registration and transaction tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    event.listen(engine, "connect", set_sqlite_pragma)
    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    login_tracker.reset()

    # Deterministic Mock AI provider for test safety
    mock_provider = MockAIProvider(provider_name="test-mock-llm")
    original_provider = ai_threat_analyzer.provider
    ai_threat_analyzer.set_provider(mock_provider)

    session = TestingSession()
    client = TestClient(app)

    yield client, session

    # Cleanup
    ai_threat_analyzer.set_provider(original_provider)
    session.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    login_tracker.reset()


def test_public_homepage_and_health_access(test_setup):
    """Confirm public root and health endpoints are accessible without authentication."""
    client, _ = test_setup
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json()["status"] == "online"


def test_successful_registration(test_setup):
    """Register a new customer demo account and verify default role, demo balance, and welcome transaction."""
    client, session = test_setup
    payload = {
        "full_name": "New Evaluator",
        "email": "evaluator@demo.in",
        "phone_number": "+919876500001",
        "username": "evaluator1",
        "password": "SecurePassword999!",
        "confirm_password": "SecurePassword999!",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "evaluator1"
    assert data["account_number"].startswith("AC-")
    assert data["initial_balance_inr"] == 50000.0
    assert data["verification_status"] == "PENDING_MSG91_INTEGRATION"

    # Verify user in database
    created_user = session.query(User).filter(User.username == "evaluator1").first()
    assert created_user is not None
    assert created_user.role == "USER"
    assert created_user.phone_verified is False

    # Verify account in database
    account = session.query(Account).filter(Account.user_id == created_user.id).first()
    assert account is not None
    assert account.balance == 5000000  # 50,000 INR in paise

    # Verify initial welcome transaction
    tx = session.query(Transaction).filter(Transaction.recipient_account_id == account.id).first()
    assert tx is not None
    assert tx.amount_paise == 5000000
    assert tx.status == "COMPLETED"


def test_duplicate_registration_rejected(test_setup):
    """Confirm duplicate usernames, emails, and phone numbers are rejected with 400 Bad Request."""
    client, _ = test_setup

    # Register initial user
    base_payload = {
        "full_name": "Primary User",
        "email": "primary@demo.in",
        "phone_number": "+919876511111",
        "username": "primary_user",
        "password": "SecurePassword999!",
        "confirm_password": "SecurePassword999!",
    }
    res = client.post("/api/v1/auth/register", json=base_payload)
    assert res.status_code == 201

    # Attempt duplicate username
    res_dup_user = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Different Name",
            "email": "unique1@demo.in",
            "phone_number": "+919876522222",
            "username": "primary_user",  # Duplicate
            "password": "SecurePassword999!",
            "confirm_password": "SecurePassword999!",
        },
    )
    assert res_dup_user.status_code == 400
    assert "Username is already registered" in res_dup_user.json()["detail"]

    # Attempt duplicate email
    res_dup_email = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Different Name",
            "email": "primary@demo.in",  # Duplicate
            "phone_number": "+919876533333",
            "username": "unique_user2",
            "password": "SecurePassword999!",
            "confirm_password": "SecurePassword999!",
        },
    )
    assert res_dup_email.status_code == 400
    assert "Email address is already registered" in res_dup_email.json()["detail"]

    # Attempt duplicate phone number
    res_dup_phone = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Different Name",
            "email": "unique3@demo.in",
            "phone_number": "+919876511111",  # Duplicate
            "username": "unique_user3",
            "password": "SecurePassword999!",
            "confirm_password": "SecurePassword999!",
        },
    )
    assert res_dup_phone.status_code == 400
    assert "Mobile number is already registered" in res_dup_phone.json()["detail"]


def test_mismatched_password_rejected(test_setup):
    """Ensure password confirmation mismatch is rejected."""
    client, _ = test_setup
    res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Mismatch Tester",
            "email": "mismatch@demo.in",
            "phone_number": "+919876500004",
            "username": "mismatch_user",
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!",
        },
    )
    assert res.status_code == 400
    assert "Passwords do not match" in res.json()["detail"]


def test_customer_transactions_ownership_and_filtering(test_setup):
    """Verify customers see only their own transactions, and cannot query other users' accounts."""
    client, session = test_setup

    # Create User A
    user_a = User(
        username="cust_a",
        email="cust_a@demo.in",
        full_name="Customer A",
        password_hash=hash_password("Pass12345!"),
        role="USER",
        is_active=True,
    )
    session.add(user_a)
    session.commit()
    session.refresh(user_a)

    acc_a = Account(
        user_id=user_a.id,
        account_number="AC-TEST-A",
        account_type="SAVINGS",
        currency="INR",
        balance=1000000,
        is_active=True,
    )
    session.add(acc_a)
    session.commit()
    session.refresh(acc_a)

    # Create User B
    user_b = User(
        username="cust_b",
        email="cust_b@demo.in",
        full_name="Customer B",
        password_hash=hash_password("Pass12345!"),
        role="USER",
        is_active=True,
    )
    session.add(user_b)
    session.commit()
    session.refresh(user_b)

    acc_b = Account(
        user_id=user_b.id,
        account_number="AC-TEST-B",
        account_type="SAVINGS",
        currency="INR",
        balance=500000,
        is_active=True,
    )
    session.add(acc_b)
    session.commit()
    session.refresh(acc_b)

    # Seed transaction: User A sends 100 INR to User B
    tx = Transaction(
        reference="TX-TEST-AB-01",
        sender_account_id=acc_a.id,
        recipient_account_id=acc_b.id,
        amount_paise=10000,
        status="COMPLETED",
        memo="Lunch payment test",
    )
    session.add(tx)
    session.commit()

    # User A token
    token_a = create_access_token(
        claims={"sub": str(user_a.id), "username": user_a.username, "role": user_a.role}
    )
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User A queries their statement
    res_a = client.get("/api/v1/banking/transactions", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["total"] == 1
    item = data_a["items"][0]
    assert item["transaction_reference"] == "TX-TEST-AB-01"
    assert item["direction"] == "DEBIT"
    assert item["amount_paise"] == 10000
    assert item["counterparty_account"] == "AC-TEST-B"

    # User B queries their statement
    token_b = create_access_token(
        claims={"sub": str(user_b.id), "username": user_b.username, "role": user_b.role}
    )
    headers_b = {"Authorization": f"Bearer {token_b}"}
    res_b = client.get("/api/v1/banking/transactions", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["total"] == 1
    item_b = data_b["items"][0]
    assert item_b["direction"] == "CREDIT"
    assert item_b["counterparty_account"] == "AC-TEST-A"

    # Filter by direction: User A checks DEBIT (should find 1)
    res_debit = client.get("/api/v1/banking/transactions?type=DEBIT", headers=headers_a)
    assert res_debit.status_code == 200
    assert len(res_debit.json()["items"]) == 1

    # Filter by direction: User A checks CREDIT (should find 0)
    res_credit = client.get("/api/v1/banking/transactions?type=CREDIT", headers=headers_a)
    assert res_credit.status_code == 200
    assert len(res_credit.json()["items"]) == 0

    # User A attempts to filter by User B's account ID (Ownership Violation -> 403 Forbidden)
    res_forbidden = client.get(
        f"/api/v1/banking/transactions?account_id={acc_b.id}", headers=headers_a
    )
    assert res_forbidden.status_code == 403


def test_judge_a_normal_transfer_and_judge_b_step_up_escalation(test_setup):
    """Judge A executes normal small transfer (low-risk), Judge B attempts ₹25,00,000 transfer (triggers step-up)."""
    client, session = test_setup

    # Setup Judge A (Alice)
    alice = User(
        username="alice",
        email="alice@demo.in",
        full_name="Alice Customer",
        password_hash=hash_password("SecurePass123!"),
        role="USER",
        is_active=True,
    )
    session.add(alice)
    session.commit()
    session.refresh(alice)

    acc_alice = Account(
        user_id=alice.id,
        account_number="AC-10001",
        account_type="SAVINGS",
        currency="INR",
        balance=10000000,  # ₹1,00,000
        is_active=True,
    )
    session.add(acc_alice)

    # Setup Judge B (Bob)
    bob = User(
        username="bob",
        email="bob@demo.in",
        full_name="Bob Customer",
        password_hash=hash_password("SecurePass123!"),
        role="USER",
        is_active=True,
    )
    session.add(bob)
    session.commit()
    session.refresh(bob)

    acc_bob = Account(
        user_id=bob.id,
        account_number="AC-10002",
        account_type="SAVINGS",
        currency="INR",
        balance=500000000,  # ₹50,00,000
        is_active=True,
    )
    session.add(acc_bob)
    session.commit()

    # 1. Judge A executes small transfer (₹500 = 50000 paise to Bob AC-10002)
    token_alice = create_access_token(
        claims={"sub": str(alice.id), "username": alice.username, "role": alice.role}
    )
    headers_alice = {"Authorization": f"Bearer {token_alice}"}

    res_transfer_a = client.post(
        "/api/v1/banking/transfer",
        json={
            "sender_account_id": acc_alice.id,
            "recipient_account_number": "AC-10002",
            "amount_paise": 50000,
            "memo": "Routine utility bill reimbursement",
        },
        headers=headers_alice,
    )
    assert res_transfer_a.status_code == 200
    data_a = res_transfer_a.json()
    assert data_a["status"] == "COMPLETED"
    assert data_a["remaining_balance_paise"] == 9950000

    # 2. Judge B attempts high-value ₹25 Lakh transfer (250000000 paise to Alice AC-10001)
    token_bob = create_access_token(
        claims={"sub": str(bob.id), "username": bob.username, "role": bob.role}
    )
    headers_bob = {"Authorization": f"Bearer {token_bob}"}

    res_transfer_b = client.post(
        "/api/v1/banking/transfer",
        json={
            "sender_account_id": acc_bob.id,
            "recipient_account_number": "AC-10001",
            "amount_paise": 250000000,  # ₹25,00,000
            "memo": "High-value asset purchase demonstration",
        },
        headers=headers_bob,
    )
    assert res_transfer_b.status_code == 403
    detail = res_transfer_b.json()["detail"]
    assert detail["status"] == "STEP_UP_REQUIRED"
    assert detail["challenge_id"] is not None
    assert detail["challenge_type"] in ("OTP", "FACE_VERIFICATION")
