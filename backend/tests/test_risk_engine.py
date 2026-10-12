"""Automated tests for BankSim Adaptive Risk Engine (Phase 4)."""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db, set_sqlite_pragma
from main import app
from models import (
    Account,
    AccountType,
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    Transaction,
    User,
    UserRole,
)
from schemas import RiskLevel, RiskOutcome
from security.login_tracker import login_tracker
from security.passwords import hash_password
from security.tokens import create_access_token
from services.risk_engine import (
    AdaptiveRiskEngine,
    RiskEvaluationContext,
    risk_engine,
)


@pytest.fixture
def risk_fixture():
    """Isolated in-memory SQLite database and TestClient with StaticPool for risk engine tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    event.listen(engine, "connect", set_sqlite_pragma)
    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    login_tracker.reset()

    session = TestingSession()
    client = TestClient(app)

    yield client, session

    session.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    login_tracker.reset()


def test_normal_activity_receives_low_risk(risk_fixture):
    """Test 1: Normal transaction with established recipient and low amount yields LOW risk and ALLOW."""
    _, session = risk_fixture

    user = User(username="normal_user", email="normal@banksim.local", role=UserRole.USER.value)
    session.add(user)
    session.commit()

    sender_acc = Account(user_id=user.id, account_number="AC-SENDER-1", balance=10000000)
    recipient_acc = Account(user_id=user.id, account_number="AC-RECIPIENT-1", balance=5000000)
    session.add_all([sender_acc, recipient_acc])
    session.commit()

    # Create prior history to make recipient established and establish amount baseline
    prior_tx = Transaction(
        sender_account_id=sender_acc.id,
        recipient_account_id=recipient_acc.id,
        amount_paise=50000,  # 500 INR
        status="COMPLETED",
        reference="TX-HIST-1",
    )
    session.add(prior_tx)
    session.commit()

    context = RiskEvaluationContext(
        client_ip="192.168.1.50",
        user_agent="Mozilla/5.0",
        session_age_seconds=300,
        recent_burst_count=1,
    )

    assessment = risk_engine.assess_transaction_risk(
        sender_account=sender_acc,
        recipient_account=recipient_acc,
        amount_paise=40000,
        db=session,
        context=context,
    )

    assert assessment.risk_score <= 25
    assert assessment.risk_level == RiskLevel.LOW
    assert assessment.recommended_outcome == RiskOutcome.ALLOW
    assert len(assessment.triggered_signals) == 0


def test_repeated_login_failures_increase_risk(risk_fixture):
    """Test 2: Repeated login failures trigger failed login anomaly signal and elevate risk score."""
    _, session = risk_fixture

    user = User(username="brute_victim", email="victim@banksim.local", role=UserRole.USER.value)
    session.add(user)
    session.commit()

    sender_acc = Account(user_id=user.id, account_number="AC-SENDER-LOGIN", balance=5000000)
    session.add(sender_acc)
    session.commit()

    # Record 4 login failures in the past 24 hours
    now = datetime.now(timezone.utc)
    for i in range(4):
        event_obj = SecurityEvent(
            user_id=user.id,
            event_type=SecurityEventType.LOGIN_FAILURE.value,
            severity=SecuritySeverity.LOW.value,
            description=f"Simulated login failure {i}",
            created_at=now - timedelta(minutes=10 * i),
        )
        session.add(event_obj)
    session.commit()

    signal_res = risk_engine.evaluate_failed_logins(user, session)
    assert signal_res.triggered is True
    assert signal_res.score_impact >= 25
    assert signal_res.evidence["failed_login_count_24h"] == 4


def test_unusual_amount_increases_risk(risk_fixture):
    """Test 3: Transfer amount far exceeding historical average triggers amount anomaly signal."""
    _, session = risk_fixture

    user = User(username="amount_tester", email="amount@banksim.local", role=UserRole.USER.value)
    session.add(user)
    session.commit()

    sender_acc = Account(user_id=user.id, account_number="AC-AMOUNT-TEST", balance=20000000)
    recipient_acc = Account(user_id=user.id, account_number="AC-AMOUNT-RECV", balance=1000000)
    session.add_all([sender_acc, recipient_acc])
    session.commit()

    # Prior transfers of small amounts (1,000 INR = 100,000 paise)
    tx1 = Transaction(
        sender_account_id=sender_acc.id,
        recipient_account_id=recipient_acc.id,
        amount_paise=100000,
        status="COMPLETED",
        reference="TX-BASELINE-1",
    )
    session.add(tx1)
    session.commit()

    # Request high transfer of 60,000 INR (6,000,000 paise > 5,000,000 threshold and > 3x avg)
    signal_res = risk_engine.evaluate_amount_anomaly(sender_acc, 6000000, session)
    assert signal_res.triggered is True
    assert signal_res.score_impact >= 20
    assert "exceeds" in signal_res.description.lower()


def test_high_velocity_increases_risk(risk_fixture):
    """Test 4: High transaction frequency in window triggers velocity signal."""
    _, session = risk_fixture

    user = User(username="velocity_user", email="velocity@banksim.local", role=UserRole.USER.value)
    session.add(user)
    session.commit()

    sender_acc = Account(user_id=user.id, account_number="AC-VEL-SENDER", balance=10000000)
    recipient_acc = Account(user_id=user.id, account_number="AC-VEL-RECV", balance=1000000)
    session.add_all([sender_acc, recipient_acc])
    session.commit()

    # Insert 3 recent transactions within last 15 minutes
    now = datetime.now(timezone.utc)
    for i in range(3):
        tx = Transaction(
            sender_account_id=sender_acc.id,
            recipient_account_id=recipient_acc.id,
            amount_paise=10000,
            status="COMPLETED",
            reference=f"TX-VEL-{i}",
            created_at=now - timedelta(minutes=5 * i),
        )
        session.add(tx)
    session.commit()

    signal_res = risk_engine.evaluate_velocity(sender_acc, session)
    assert signal_res.triggered is True
    assert signal_res.score_impact >= 20
    assert signal_res.evidence["recent_count"] == 3


def test_new_recipient_triggers_novelty_signal(risk_fixture):
    """Test 5: Transfer to an account never previously transacted with triggers recipient novelty."""
    _, session = risk_fixture

    user = User(username="novelty_user", email="novelty@banksim.local", role=UserRole.USER.value)
    session.add(user)
    session.commit()

    sender_acc = Account(user_id=user.id, account_number="AC-NOV-SENDER", balance=5000000)
    new_recipient = Account(user_id=user.id, account_number="AC-NEVER-SEEN", balance=5000000)
    session.add_all([sender_acc, new_recipient])
    session.commit()

    signal_res = risk_engine.evaluate_recipient_novelty(sender_acc, new_recipient, session)
    assert signal_res.triggered is True
    assert signal_res.score_impact == 15
    assert signal_res.evidence["prior_successful_transfers"] == 0


def test_missing_and_incomplete_signals_handled_safely(risk_fixture):
    """Test 6: Missing telemetry is marked as unknown or omitted without crashing."""
    _, session = risk_fixture

    user = User(username="missing_user", email="missing@banksim.local", role=UserRole.USER.value)
    session.add(user)
    session.commit()

    sender_acc = Account(user_id=user.id, account_number="AC-MISSING-SIGNALS", balance=1000000)
    session.add(sender_acc)
    session.commit()

    # Recipient account is None (unverified recipient)
    novelty_res = risk_engine.evaluate_recipient_novelty(sender_acc, None, session)
    assert novelty_res.status == "unknown"
    assert novelty_res.score_impact == 0

    # Context is None (burst and session context omitted)
    burst_res = risk_engine.evaluate_request_burst(None)
    assert burst_res.status == "omitted"
    assert burst_res.score_impact == 0

    session_res = risk_engine.evaluate_session_anomaly(None)
    assert session_res.status == "omitted"
    assert session_res.score_impact == 0


def test_score_boundaries_and_outcome_mapping(risk_fixture):
    """Test 7: Multi-signal escalation maps correctly across all outcome tiers."""
    _, session = risk_fixture

    user = User(username="multi_signal_user", email="multi@banksim.local", role=UserRole.USER.value)
    session.add(user)
    session.commit()

    sender_acc = Account(user_id=user.id, account_number="AC-MULTI-SENDER", balance=50000000)
    new_recipient = Account(user_id=user.id, account_number="AC-MULTI-NEW", balance=1000000)
    session.add_all([sender_acc, new_recipient])
    session.commit()

    # Simulate lockout (35 points) + new recipient (15 points) + burst (25 points) + extreme amount (25 points)
    login_tracker.record_failure(user.username)
    for _ in range(5):
        login_tracker.record_failure(user.username)

    context = RiskEvaluationContext(
        client_ip=None,
        session_age_seconds=5,
        recent_burst_count=10,  # burst trigger (+25)
    )

    assessment = risk_engine.assess_transaction_risk(
        sender_account=sender_acc,
        recipient_account=new_recipient,
        amount_paise=10000000,  # high amount (+25)
        db=session,
        context=context,
    )

    assert assessment.risk_score >= 80
    assert assessment.risk_score <= 100
    assert assessment.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert assessment.recommended_outcome in (RiskOutcome.RESTRICT, RiskOutcome.BLOCK)
    assert len(assessment.triggered_signals) >= 3


def test_high_risk_assessment_persists_security_event(risk_fixture):
    """Test 8: High or critical risk assessment logs a SecurityEvent in the audit table."""
    _, session = risk_fixture

    user = User(username="audit_test_user", email="audit@banksim.local", role=UserRole.USER.value)
    session.add(user)
    session.commit()

    sender_acc = Account(user_id=user.id, account_number="AC-AUDIT-SENDER", balance=20000000)
    new_recipient = Account(user_id=user.id, account_number="AC-AUDIT-RECV", balance=500000)
    session.add_all([sender_acc, new_recipient])
    session.commit()

    # Lock account to force score >= 70
    for _ in range(5):
        login_tracker.record_failure(user.username)

    context = RiskEvaluationContext(
        client_ip=None,
        session_age_seconds=2,
        recent_burst_count=8,
    )

    initial_event_count = session.query(SecurityEvent).count()

    assessment = risk_engine.assess_transaction_risk(
        sender_account=sender_acc,
        recipient_account=new_recipient,
        amount_paise=15000000,
        db=session,
        context=context,
    )

    assert assessment.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    final_event_count = session.query(SecurityEvent).count()
    assert final_event_count > initial_event_count

    event_record = (
        session.query(SecurityEvent)
        .filter(SecurityEvent.user_id == user.id)
        .order_by(SecurityEvent.id.desc())
        .first()
    )
    assert event_record is not None
    assert event_record.event_type == SecurityEventType.THREAT_DETECTED.value
    assert event_record.risk_score == assessment.risk_score


def test_api_assess_risk_successful(risk_fixture):
    """Test 9: Authenticated user assesses risk on their own account successfully via API."""
    client, session = risk_fixture

    user = User(username="api_user", email="api@banksim.local", role=UserRole.USER.value)
    session.add(user)
    session.commit()

    sender_acc = Account(user_id=user.id, account_number="AC-API-SENDER", balance=5000000)
    recipient_acc = Account(user_id=user.id, account_number="AC-API-RECV", balance=5000000)
    session.add_all([sender_acc, recipient_acc])
    session.commit()

    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "sender_account_id": sender_acc.id,
        "recipient_account_number": "AC-API-RECV",
        "amount_paise": 20000,
    }

    response = client.post("/api/v1/security/assess-risk", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert "risk_level" in data
    assert "recommended_outcome" in data
    assert "triggered_signals" in data
    assert "all_signals" in data
    assert "explanation" in data


def test_api_assess_risk_unauthenticated_rejected(risk_fixture):
    """Test 10: Unauthenticated access to /security/assess-risk returns 401."""
    client, _ = risk_fixture
    payload = {
        "sender_account_id": 1,
        "recipient_account_number": "AC-999",
        "amount_paise": 50000,
    }
    response = client.post("/api/v1/security/assess-risk", json=payload)
    assert response.status_code == 401


def test_api_assess_risk_ownership_boundary_enforced(risk_fixture):
    """Test 11: User attempting to assess risk on another user's sender account receives 403 Forbidden."""
    client, session = risk_fixture

    alice = User(username="alice_risk", email="alice.r@banksim.local", role=UserRole.USER.value)
    bob = User(username="bob_risk", email="bob.r@banksim.local", role=UserRole.USER.value)
    session.add_all([alice, bob])
    session.commit()

    alice_acc = Account(user_id=alice.id, account_number="AC-ALICE", balance=1000000)
    bob_acc = Account(user_id=bob.id, account_number="AC-BOB", balance=1000000)
    session.add_all([alice_acc, bob_acc])
    session.commit()

    # Authenticate as Alice
    token_alice = create_access_token({"sub": str(alice.id), "username": alice.username, "role": alice.role})
    headers = {"Authorization": f"Bearer {token_alice}"}

    # Alice tries to assess risk specifying Bob's account as sender_account_id
    payload = {
        "sender_account_id": bob_acc.id,
        "recipient_account_number": "AC-ALICE",
        "amount_paise": 50000,
    }

    response = client.post("/api/v1/security/assess-risk", json=payload, headers=headers)
    assert response.status_code == 403
    assert "does not belong to the authenticated user" in response.json()["detail"].lower()


def test_api_assess_risk_same_sender_recipient_rejected(risk_fixture):
    """Test 12: Request specifying identical sender and recipient accounts is rejected with 400."""
    client, session = risk_fixture

    user = User(username="self_test_user", email="self@banksim.local", role=UserRole.USER.value)
    session.add(user)
    session.commit()

    account = Account(user_id=user.id, account_number="AC-SELF", balance=2000000)
    session.add(account)
    session.commit()

    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "sender_account_id": account.id,
        "recipient_account_number": "AC-SELF",
        "amount_paise": 10000,
    }

    response = client.post("/api/v1/security/assess-risk", json=payload, headers=headers)
    assert response.status_code == 400
    assert "cannot be identical" in response.json()["detail"].lower()


def test_api_assess_risk_arbitrary_score_spoofing_prevented(risk_fixture):
    """Test 13: Client cannot inject arbitrary risk scores or override server decision."""
    client, session = risk_fixture

    user = User(username="hacker_wannabe", email="hacker@banksim.local", role=UserRole.USER.value)
    session.add(user)
    session.commit()

    sender_acc = Account(user_id=user.id, account_number="AC-HACK-SENDER", balance=50000000)
    recipient_acc = Account(user_id=user.id, account_number="AC-HACK-RECV", balance=1000000)
    session.add_all([sender_acc, recipient_acc])
    session.commit()

    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to inject client-faked risk_score: 0 and recommended_outcome: "ALLOW" on suspicious transfer
    malicious_payload = {
        "sender_account_id": sender_acc.id,
        "recipient_account_number": "AC-HACK-RECV",
        "amount_paise": 10000000,  # 100,000 INR (exceeds high threshold to new recipient)
        "risk_score": 0,  # Spoofed field (must be ignored)
        "recommended_outcome": "ALLOW",  # Spoofed field (must be ignored)
        "is_safe": True,
    }

    response = client.post("/api/v1/security/assess-risk", json=malicious_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    # Server computes authoritatively: amount > 50,000 INR to new recipient => triggered signals
    assert data["risk_score"] > 0
    assert len(data["triggered_signals"]) > 0
