"""Automated tests for BankSim Mandatory OTP for Every Login."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db, set_sqlite_pragma, seed_demo_data
from backend.main import app
from backend.models import ChallengePurpose, ChallengeStatus, User, UserRole, VerificationChallenge
from backend.security.login_tracker import login_tracker
from backend.security.passwords import hash_password
from backend.services.verification_service import otp_provider


@pytest.fixture
def login_otp_fixture():
    """Isolated test database and client for login OTP tests."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    event.listen(test_engine, "connect", set_sqlite_pragma)
    Base.metadata.create_all(bind=test_engine)

    TestingSession = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
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

    yield client, session, TestingSession

    session.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    login_tracker.reset()


def create_user(session, username="alice_test", role=UserRole.USER.value, password="SecurePassword123!"):
    """Helper to populate an active user."""
    user = User(
        username=username,
        email=f"{username}@banksim.local",
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# Test 1: Valid password followed by an OTP challenge does not grant an authenticated session
def test_valid_password_issues_challenge_without_token(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "user1")

    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user1", "password": "SecurePassword123!"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "OTP_REQUIRED"
    assert data["challenge_type"] == "OTP"
    assert data["purpose"] == "LOGIN"
    assert "challenge_id" in data
    # Critical: No access token or user session is granted
    assert "access_token" not in data
    assert "token_type" not in data


# Test 2: A valid OTP completes login successfully
def test_valid_otp_completes_login(login_otp_fixture):
    client, session, _ = login_otp_fixture
    user = create_user(session, "user2")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user2", "password": "SecurePassword123!"},
    )
    ch_id = login_resp.json()["challenge_id"]
    code = otp_provider.get_dev_otp(ch_id)
    assert code is not None

    verify_resp = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": ch_id, "verification_code": code},
    )
    assert verify_resp.status_code == 200
    data = verify_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] == user.id
    assert data["role"] == "USER"


# Test 3: Incorrect OTP is rejected
def test_incorrect_otp_rejected(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "user3")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user3", "password": "SecurePassword123!"},
    )
    ch_id = login_resp.json()["challenge_id"]

    verify_resp = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": ch_id, "verification_code": "000000"},
    )
    assert verify_resp.status_code == 400
    assert "invalid verification code" in verify_resp.json()["detail"].lower()


# Test 4: Expired OTP is rejected
def test_expired_otp_rejected(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "user4")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user4", "password": "SecurePassword123!"},
    )
    ch_id = login_resp.json()["challenge_id"]
    code = otp_provider.get_dev_otp(ch_id)

    # Manually expire the challenge in the database
    ch = session.query(VerificationChallenge).filter(VerificationChallenge.id == ch_id).first()
    ch.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    session.commit()

    verify_resp = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": ch_id, "verification_code": code},
    )
    assert verify_resp.status_code == 400
    assert "expired" in verify_resp.json()["detail"].lower()


# Test 5: Reused OTP is rejected
def test_reused_otp_rejected(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "user5")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user5", "password": "SecurePassword123!"},
    )
    ch_id = login_resp.json()["challenge_id"]
    code = otp_provider.get_dev_otp(ch_id)

    # First verification succeeds
    first_resp = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": ch_id, "verification_code": code},
    )
    assert first_resp.status_code == 200

    # Second attempt to consume same challenge must be rejected
    second_resp = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": ch_id, "verification_code": code},
    )
    assert second_resp.status_code == 400
    assert "consumed" in second_resp.json()["detail"].lower() or "already" in second_resp.json()["detail"].lower()


# Test 6: Maximum failed attempts invalidate the challenge
def test_max_failed_attempts_locks_challenge(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "user6")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user6", "password": "SecurePassword123!"},
    )
    ch_id = login_resp.json()["challenge_id"]
    correct_code = otp_provider.get_dev_otp(ch_id)

    # 3 consecutive incorrect attempts
    for i in range(3):
        fail_resp = client.post(
            "/api/v1/auth/verify-otp",
            json={"challenge_id": ch_id, "verification_code": "999999"},
        )
        assert fail_resp.status_code == 400

    # Even with correct code, challenge is now locked/failed
    locked_resp = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": ch_id, "verification_code": correct_code},
    )
    assert locked_resp.status_code == 400
    assert "invalidated" in locked_resp.json()["detail"].lower() or "maximum" in locked_resp.json()["detail"].lower()


# Test 7: Resending invalidates the previous OTP
def test_resending_invalidates_previous_otp(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "user7")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user7", "password": "SecurePassword123!"},
    )
    ch_id = login_resp.json()["challenge_id"]
    old_code = otp_provider.get_dev_otp(ch_id)

    # Advance time to satisfy resend cooldown
    ch = session.query(VerificationChallenge).filter(VerificationChallenge.id == ch_id).first()
    ch.last_resend_at = datetime.now(timezone.utc) - timedelta(seconds=35)
    session.commit()

    # Request OTP resend
    resend_resp = client.post(
        "/api/v1/auth/resend-otp",
        json={"challenge_id": ch_id},
    )
    assert resend_resp.status_code == 200
    assert resend_resp.json()["status"] == "OTP_RESENT"

    new_code = otp_provider.get_dev_otp(ch_id)
    assert new_code is not None
    # Old code must be rejected
    old_verify = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": ch_id, "verification_code": old_code},
    )
    # If old code happened to differ from new code, it must fail
    if old_code != new_code:
        assert old_verify.status_code == 400

    # New code must succeed
    new_verify = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": ch_id, "verification_code": new_code},
    )
    assert new_verify.status_code == 200


# Test 8: Resend rate limits and cooldowns are enforced
def test_resend_cooldown_and_limit_enforced(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "user8")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user8", "password": "SecurePassword123!"},
    )
    ch_id = login_resp.json()["challenge_id"]

    # Immediate resend attempt without cooldown must trigger 429
    immediate_resend = client.post(
        "/api/v1/auth/resend-otp",
        json={"challenge_id": ch_id},
    )
    assert immediate_resend.status_code == 429
    assert "please wait" in immediate_resend.json()["detail"].lower()

    # Simulate 3 successful resends
    for i in range(3):
        ch = session.query(VerificationChallenge).filter(VerificationChallenge.id == ch_id).first()
        ch.last_resend_at = datetime.now(timezone.utc) - timedelta(seconds=35)
        session.commit()

        ok_resend = client.post(
            "/api/v1/auth/resend-otp",
            json={"challenge_id": ch_id},
        )
        assert ok_resend.status_code == 200

    # 4th resend must be rejected because max resends (3) was reached
    ch = session.query(VerificationChallenge).filter(VerificationChallenge.id == ch_id).first()
    ch.last_resend_at = datetime.now(timezone.utc) - timedelta(seconds=35)
    session.commit()

    over_limit = client.post(
        "/api/v1/auth/resend-otp",
        json={"challenge_id": ch_id},
    )
    assert over_limit.status_code == 429
    assert "maximum" in over_limit.json()["detail"].lower()


# Test 9: An OTP cannot be used for a different user or challenge
def test_otp_cross_challenge_isolation(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "user9a")
    create_user(session, "user9b")

    login_a = client.post("/api/v1/auth/login", json={"username": "user9a", "password": "SecurePassword123!"})
    login_b = client.post("/api/v1/auth/login", json={"username": "user9b", "password": "SecurePassword123!"})

    ch_a = login_a.json()["challenge_id"]
    ch_b = login_b.json()["challenge_id"]

    code_a = otp_provider.get_dev_otp(ch_a)
    code_b = otp_provider.get_dev_otp(ch_b)

    # Attempting to use code_a on challenge b must fail
    if code_a != code_b:
        mismatch_resp = client.post(
            "/api/v1/auth/verify-otp",
            json={"challenge_id": ch_b, "verification_code": code_a},
        )
        assert mismatch_resp.status_code == 400


# Test 10: A pending challenge cannot access protected user endpoints
def test_pending_challenge_cannot_access_user_endpoints(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "user10")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user10", "password": "SecurePassword123!"},
    )
    ch_id = login_resp.json()["challenge_id"]

    # Attempt to use challenge_id as bearer token
    unauth_resp = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {ch_id}"},
    )
    assert unauth_resp.status_code == 401


# Test 11: A pending challenge cannot access admin endpoints
def test_pending_challenge_cannot_access_admin_endpoints(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "admin11", role=UserRole.ADMIN.value)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin11", "password": "SecurePassword123!"},
    )
    ch_id = login_resp.json()["challenge_id"]

    # Attempt to access admin dashboard with challenge_id as bearer
    admin_resp = client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {ch_id}"},
    )
    assert admin_resp.status_code == 401


# Test 12: Both USER and ADMIN logins require OTP
def test_both_user_and_admin_require_otp(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "user_regular", role=UserRole.USER.value)
    create_user(session, "admin_user", role=UserRole.ADMIN.value)

    # Regular user login requires OTP
    resp_user = client.post("/api/v1/auth/login", json={"username": "user_regular", "password": "SecurePassword123!"})
    assert resp_user.status_code == 200
    assert resp_user.json()["status"] == "OTP_REQUIRED"
    assert "access_token" not in resp_user.json()

    # Admin login also requires OTP
    resp_admin = client.post("/api/v1/auth/login", json={"username": "admin_user", "password": "SecurePassword123!"})
    assert resp_admin.status_code == 200
    assert resp_admin.json()["status"] == "OTP_REQUIRED"
    assert "access_token" not in resp_admin.json()


# Test 13: Low-risk login still requires OTP (Mandatory rule: no bypass)
def test_low_risk_login_still_requires_otp(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "alice_lowrisk")

    # Standard clean login from local IP
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "alice_lowrisk", "password": "SecurePassword123!"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "OTP_REQUIRED"
    assert "access_token" not in resp.json()


# Test 14: Missing, malformed, expired, or tampered credentials rejected
def test_malformed_otp_payload_rejected(login_otp_fixture):
    client, session, _ = login_otp_fixture
    create_user(session, "user14")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user14", "password": "SecurePassword123!"},
    )
    ch_id = login_resp.json()["challenge_id"]

    # Short code
    r1 = client.post("/api/v1/auth/verify-otp", json={"challenge_id": ch_id, "verification_code": "123"})
    assert r1.status_code == 422

    # Long code
    r2 = client.post("/api/v1/auth/verify-otp", json={"challenge_id": ch_id, "verification_code": "1234567"})
    assert r2.status_code == 422

    # Non-existent challenge
    r3 = client.post("/api/v1/auth/verify-otp", json={"challenge_id": 999999, "verification_code": "123456"})
    assert r3.status_code == 404


# Test 15: Concurrent verification attempts cannot successfully consume the same challenge twice
def test_concurrent_otp_consumption_race_condition_prevented(login_otp_fixture):
    client, session, TestingSession = login_otp_fixture
    create_user(session, "user15")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "user15", "password": "SecurePassword123!"},
    )
    ch_id = login_resp.json()["challenge_id"]
    code = otp_provider.get_dev_otp(ch_id)
    assert code is not None

    def attempt_verify():
        # Each thread gets its own TestClient to simulate concurrent HTTP requests
        c = TestClient(app)
        return c.post(
            "/api/v1/auth/verify-otp",
            json={"challenge_id": ch_id, "verification_code": code},
        )

    # Launch two concurrent requests attempting to consume the same challenge simultaneously
    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(attempt_verify)
        future2 = executor.submit(attempt_verify)
        res1 = future1.result()
        res2 = future2.result()

    statuses = sorted([res1.status_code, res2.status_code])
    # Exactly one request must succeed (200), and the other must be rejected (400)
    assert statuses == [200, 400], f"Expected [200, 400] but received {statuses}"
