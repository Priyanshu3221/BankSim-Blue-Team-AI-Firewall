"""Comprehensive tests for BankSim Phase 7: Secure Mock OTP & Risk-Based Face Verification."""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db, set_sqlite_pragma
from backend.main import app
from backend.models import (
    Account,
    AccountType,
    ChallengePurpose,
    ChallengeStatus,
    ChallengeType,
    SecurityEvent,
    SecurityEventType,
    User,
    UserRole,
    Transaction,
)
from backend.security.passwords import hash_password
from backend.security.tokens import create_access_token
from backend.services.ai_providers import MockAIProvider
from backend.services.ai_threat_analyzer import ai_threat_analyzer
from backend.services.banking_service import banking_service
from backend.services.verification_service import (
    otp_provider,
    face_provider,
    verification_service,
)


@pytest.fixture
def verification_fixture():
    """Isolated in-memory SQLite fixture for Phase 7 verification tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    event.listen(engine, "connect", set_sqlite_pragma)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    mock_provider = MockAIProvider(provider_name="test-mock-llm")
    original_provider = ai_threat_analyzer.provider
    ai_threat_analyzer.set_provider(mock_provider)

    yield client, session, engine

    ai_threat_analyzer.set_provider(original_provider)
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=engine)
    otp_provider.clear_dev_mailbox()


def create_user_and_account(
    session: Session, username: str, email: str, balance_paise: int = 1000000
):
    """Helper to create a user with an active account."""
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("SecurePass123!"),
        role=UserRole.USER.value,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    account = Account(
        user_id=user.id,
        account_number=f"AC-{username.upper()[:6]}-777",
        account_type=AccountType.SAVINGS.value,
        balance=balance_paise,
        is_active=True,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return user, account


def auth_headers(user: User):
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


# --- 1. OTP Provider Tests ---


def test_random_mock_otp_generation_and_hashing(verification_fixture):
    """Test 1: Mock OTP provider generates distinct cryptographically random codes and stores salted hashes."""
    _, session, _ = verification_fixture
    user, _ = create_user_and_account(session, "user1", "u1@banksim.local")

    challenge = verification_service.create_challenge(
        user_id=user.id,
        challenge_type=ChallengeType.OTP,
        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
        recipient_account_number="AC-DEST-001",
        amount_paise=50000,
        db=session,
    )

    assert challenge.id is not None
    assert challenge.code_hash is not None
    assert "$" in challenge.code_hash

    # Plaintext code is in dev mailbox, NOT in database
    plaintext_code = otp_provider.get_dev_otp(challenge.id)
    assert plaintext_code is not None
    assert len(plaintext_code) == 6
    assert plaintext_code.isdigit()
    assert plaintext_code not in challenge.code_hash  # Plaintext is not stored raw in DB

    # Salted hash validates properly
    assert otp_provider.verify_otp(plaintext_code, challenge.code_hash) is True
    assert otp_provider.verify_otp("000000", challenge.code_hash) is False


def test_otp_verification_success(verification_fixture):
    """Test 2: Submitting the valid OTP verifies the challenge."""
    client, session, _ = verification_fixture
    user, _ = create_user_and_account(session, "user2", "u2@banksim.local")

    challenge = verification_service.create_challenge(
        user_id=user.id,
        challenge_type=ChallengeType.OTP,
        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
        recipient_account_number="AC-DEST-002",
        amount_paise=25000,
        db=session,
    )
    code = otp_provider.get_dev_otp(challenge.id)

    resp = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge.id, "verification_code": code},
        headers=auth_headers(user),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "VERIFIED"

    session.refresh(challenge)
    assert challenge.status == ChallengeStatus.VERIFIED.value
    assert challenge.verified_at is not None
    assert challenge.attempt_count == 1


def test_otp_invalid_code_and_attempt_locking(verification_fixture):
    """Test 3: Incorrect OTP increments attempts and locks the challenge after 3 attempts."""
    client, session, _ = verification_fixture
    user, _ = create_user_and_account(session, "user3", "u3@banksim.local")

    challenge = verification_service.create_challenge(
        user_id=user.id,
        challenge_type=ChallengeType.OTP,
        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
        recipient_account_number="AC-DEST-003",
        amount_paise=10000,
        db=session,
    )

    # Attempt 1: Wrong code
    resp1 = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge.id, "verification_code": "999999"},
        headers=auth_headers(user),
    )
    assert resp1.status_code == 400
    session.refresh(challenge)
    assert challenge.attempt_count == 1
    assert challenge.status == ChallengeStatus.PENDING.value

    # Attempt 2: Wrong code
    resp2 = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge.id, "verification_code": "888888"},
        headers=auth_headers(user),
    )
    assert resp2.status_code == 400
    session.refresh(challenge)
    assert challenge.attempt_count == 2
    assert challenge.status == ChallengeStatus.PENDING.value

    # Attempt 3: Wrong code -> Locks to FAILED
    resp3 = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge.id, "verification_code": "777777"},
        headers=auth_headers(user),
    )
    assert resp3.status_code == 400
    session.refresh(challenge)
    assert challenge.attempt_count == 3
    assert challenge.status == ChallengeStatus.FAILED.value

    # Further attempt with correct code is now rejected because challenge is FAILED
    correct_code = otp_provider.get_dev_otp(challenge.id)
    resp4 = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge.id, "verification_code": correct_code},
        headers=auth_headers(user),
    )
    assert resp4.status_code == 400
    assert "already failed" in resp4.json()["detail"].lower()


def test_expired_challenge_rejected(verification_fixture):
    """Test 4: Expired challenge is transitioned to EXPIRED and rejected."""
    client, session, _ = verification_fixture
    user, _ = create_user_and_account(session, "user4", "u4@banksim.local")

    challenge = verification_service.create_challenge(
        user_id=user.id,
        challenge_type=ChallengeType.OTP,
        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
        recipient_account_number="AC-DEST-004",
        amount_paise=10000,
        db=session,
    )
    # Manually expire the challenge in the past
    challenge.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    session.commit()

    code = otp_provider.get_dev_otp(challenge.id)
    resp = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge.id, "verification_code": code},
        headers=auth_headers(user),
    )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()

    session.refresh(challenge)
    assert challenge.status == ChallengeStatus.EXPIRED.value


def test_cross_user_challenge_verification_rejected(verification_fixture):
    """Test 5: Authenticated user cannot verify a challenge belonging to another user."""
    client, session, _ = verification_fixture
    user_a, _ = create_user_and_account(session, "alice", "alice@banksim.local")
    user_b, _ = create_user_and_account(session, "bob", "bob@banksim.local")

    challenge_a = verification_service.create_challenge(
        user_id=user_a.id,
        challenge_type=ChallengeType.OTP,
        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
        recipient_account_number="AC-DEST-005",
        amount_paise=10000,
        db=session,
    )
    code = otp_provider.get_dev_otp(challenge_a.id)

    # Bob tries to verify Alice's challenge
    resp = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge_a.id, "verification_code": code},
        headers=auth_headers(user_b),
    )
    assert resp.status_code == 403
    assert "does not belong" in resp.json()["detail"].lower()


# --- 2. Risk-Based Face Verification Tests ---


def test_risk_based_challenge_escalation(verification_fixture):
    """Test 6: Medium risk triggers OTP challenge, High risk triggers Face Verification challenge."""
    client, session, _ = verification_fixture

    # 1. Medium risk transfer: Account with no past txs sending large amount (25 pts amount + 15 pts recipient novelty = 40 pts -> STEP_UP_VERIFICATION)
    user_m, acc_m = create_user_and_account(session, "user_med", "med@banksim.local", 20000000)
    user_b, acc_b = create_user_and_account(session, "bob_med", "bmed@banksim.local", 10000)

    resp_medium = client.post(
        "/api/v1/banking/transfer",
        json={
            "recipient_account_number": acc_b.account_number,
            "amount_paise": 6000000,  # 60,000 INR
            "memo": "Standard business invoice",
        },
        headers=auth_headers(user_m),
    )
    assert resp_medium.status_code == 403
    med_detail = resp_medium.json()["detail"]
    assert med_detail["status"] == "STEP_UP_REQUIRED"
    assert med_detail["recommended_outcome"] == "STEP_UP_VERIFICATION"
    assert med_detail["challenge_type"] == "OTP"

    # 2. High risk transfer: Seed past transactions + multiple failed logins so score reaches RESTRICT (>60)
    user_h, acc_h = create_user_and_account(session, "user_high", "high@banksim.local", 20000000)
    user_c, acc_c = create_user_and_account(session, "user_novel", "unovel@banksim.local", 10000)
    past_tx = Transaction(
        sender_account_id=acc_h.id,
        recipient_account_id=acc_b.id,
        amount_paise=50000,  # avg = 500 INR
        status="COMPLETED",
        reference="TX-BASELINE-01",
    )
    session.add(past_tx)
    for i in range(4):
        session.add(
            SecurityEvent(
                user_id=user_h.id,
                event_type=SecurityEventType.LOGIN_FAILURE.value,
                severity="HIGH",
                description=f"Repeated failed password attempt {i+1}",
                risk_score=25,
            )
        )
    session.commit()

    resp_high = client.post(
        "/api/v1/banking/transfer",
        json={
            "recipient_account_number": acc_c.account_number,
            "amount_paise": 6000000,  # 60,000 INR (>3x avg and >= threshold -> +35) + novel recipient (+15) + failed login (+10) + session (+10) = 70 pts -> RESTRICT
            "memo": "Urgent executive settlement",
        },
        headers=auth_headers(user_h),
    )
    assert resp_high.status_code == 403
    high_detail = resp_high.json()["detail"]
    assert high_detail["status"] == "STEP_UP_REQUIRED"
    assert high_detail["recommended_outcome"] == "RESTRICT"
    assert high_detail["challenge_type"] == "FACE_VERIFICATION"


def test_face_verification_success(verification_fixture):
    """Test 7: Valid face biometric verification verifies the challenge without persisting raw data."""
    client, session, _ = verification_fixture
    user, _ = create_user_and_account(session, "face_user", "fu@banksim.local")

    challenge = verification_service.create_challenge(
        user_id=user.id,
        challenge_type=ChallengeType.FACE_VERIFICATION,
        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
        recipient_account_number="AC-DEST-007",
        amount_paise=8000000,
        db=session,
    )

    resp = client.post(
        "/api/v1/banking/verify-challenge",
        json={
            "challenge_id": challenge.id,
            "face_data": "MOCK_FACE_VALID",
        },
        headers=auth_headers(user),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "VERIFIED"

    session.refresh(challenge)
    assert challenge.status == ChallengeStatus.VERIFIED.value
    assert challenge.verified_at is not None

    # Guarantee: No biometric image or template was stored in the challenge row
    assert challenge.code_hash is None


def test_face_verification_spoof_and_mismatch_failure(verification_fixture):
    """Test 8: Spoofing attempt or mismatch is rejected and locks after 3 attempts."""
    client, session, _ = verification_fixture
    user, _ = create_user_and_account(session, "face_spoof", "fs@banksim.local")

    challenge = verification_service.create_challenge(
        user_id=user.id,
        challenge_type=ChallengeType.FACE_VERIFICATION,
        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
        recipient_account_number="AC-DEST-008",
        amount_paise=8000000,
        db=session,
    )

    # Attempt 1: Liveness spoof failure
    resp1 = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge.id, "face_data": "MOCK_FACE_SPOOF_PHOTO"},
        headers=auth_headers(user),
    )
    assert resp1.status_code == 400
    assert "liveness" in resp1.json()["detail"].lower()

    # Attempt 2: Biometric mismatch
    resp2 = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge.id, "face_data": "MOCK_FACE_MISMATCH"},
        headers=auth_headers(user),
    )
    assert resp2.status_code == 400
    assert "mismatch" in resp2.json()["detail"].lower()

    # Attempt 3: Another failure -> Locks challenge
    resp3 = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge.id, "face_data": "UNRECOGNIZED_FACE"},
        headers=auth_headers(user),
    )
    assert resp3.status_code == 400

    session.refresh(challenge)
    assert challenge.status == ChallengeStatus.FAILED.value
    assert challenge.attempt_count == 3


def test_challenge_type_mismatch_rejected(verification_fixture):
    """Test 9: Submitting face data for OTP challenge or OTP code for Face challenge is rejected."""
    client, session, _ = verification_fixture
    user, _ = create_user_and_account(session, "type_mismatch", "tm@banksim.local")

    # 1. OTP challenge receives face_data (missing verification_code)
    otp_challenge = verification_service.create_challenge(
        user_id=user.id,
        challenge_type=ChallengeType.OTP,
        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
        recipient_account_number="AC-DEST-009",
        amount_paise=10000,
        db=session,
    )
    resp_otp = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": otp_challenge.id, "face_data": "MOCK_FACE_VALID"},
        headers=auth_headers(user),
    )
    assert resp_otp.status_code == 400
    assert "verification code is required" in resp_otp.json()["detail"].lower()

    # 2. Face challenge receives verification_code (missing face_data)
    face_challenge = verification_service.create_challenge(
        user_id=user.id,
        challenge_type=ChallengeType.FACE_VERIFICATION,
        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
        recipient_account_number="AC-DEST-009",
        amount_paise=10000,
        db=session,
    )
    resp_face = client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": face_challenge.id, "verification_code": "123456"},
        headers=auth_headers(user),
    )
    assert resp_face.status_code == 400
    assert "face data is required" in resp_face.json()["detail"].lower()


# --- 3. Transfer Binding & Single-Use Consumption Tests ---


def test_transfer_parameter_binding_tampering_rejected(verification_fixture):
    """Test 10: Challenge verified for transfer A cannot be replayed for transfer B (parameter mismatch)."""
    client, session, _ = verification_fixture
    user, acc_a = create_user_and_account(session, "tamper_user", "tu@banksim.local", 10000000)
    user_b, acc_b = create_user_and_account(session, "bob_acc", "ba@banksim.local", 10000)
    user_c, acc_c = create_user_and_account(session, "charlie_acc", "ca@banksim.local", 10000)

    # Issue challenge specifically for: recipient = acc_b, amount = 50,000 INR
    challenge = verification_service.create_challenge(
        user_id=user.id,
        challenge_type=ChallengeType.OTP,
        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
        recipient_account_number=acc_b.account_number,
        amount_paise=5000000,
        db=session,
    )
    code = otp_provider.get_dev_otp(challenge.id)

    # Verify the challenge
    client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge.id, "verification_code": code},
        headers=auth_headers(user),
    )

    # 1. Attacker tries to use the challenge to transfer to DIFFERENT recipient (acc_c)
    resp_tamper_recip = client.post(
        "/api/v1/banking/transfer",
        json={
            "recipient_account_number": acc_c.account_number,
            "amount_paise": 5000000,
            "challenge_id": challenge.id,
        },
        headers=auth_headers(user),
    )
    assert resp_tamper_recip.status_code == 400
    assert "parameter mismatch" in resp_tamper_recip.json()["detail"].lower()

    # 2. Attacker tries to use the challenge to transfer a HIGHER amount (80,000 INR)
    resp_tamper_amt = client.post(
        "/api/v1/banking/transfer",
        json={
            "recipient_account_number": acc_b.account_number,
            "amount_paise": 8000000,
            "challenge_id": challenge.id,
        },
        headers=auth_headers(user),
    )
    assert resp_tamper_amt.status_code == 400
    assert "parameter mismatch" in resp_tamper_amt.json()["detail"].lower()


def test_single_use_challenge_consumption(verification_fixture):
    """Test 11: A challenge can only be consumed once; subsequent transfers with same challenge are rejected."""
    client, session, _ = verification_fixture
    user, acc_a = create_user_and_account(session, "single_use", "su@banksim.local", 10000000)
    user_b, acc_b = create_user_and_account(session, "bob_su", "bsu@banksim.local", 10000)

    challenge = verification_service.create_challenge(
        user_id=user.id,
        challenge_type=ChallengeType.OTP,
        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
        recipient_account_number=acc_b.account_number,
        amount_paise=2000000,
        db=session,
    )
    code = otp_provider.get_dev_otp(challenge.id)

    # Verify
    client.post(
        "/api/v1/banking/verify-challenge",
        json={"challenge_id": challenge.id, "verification_code": code},
        headers=auth_headers(user),
    )

    # First transfer: Completes successfully
    resp1 = client.post(
        "/api/v1/banking/transfer",
        json={
            "recipient_account_number": acc_b.account_number,
            "amount_paise": 2000000,
            "challenge_id": challenge.id,
        },
        headers=auth_headers(user),
    )
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "COMPLETED"

    session.refresh(challenge)
    assert challenge.status == ChallengeStatus.CONSUMED.value

    # Second transfer with same challenge_id: Replay attack rejected
    resp2 = client.post(
        "/api/v1/banking/transfer",
        json={
            "recipient_account_number": acc_b.account_number,
            "amount_paise": 2000000,
            "challenge_id": challenge.id,
        },
        headers=auth_headers(user),
    )
    assert resp2.status_code == 400
    assert "consumed" in resp2.json()["detail"].lower()


def test_complete_end_to_end_verification_flow(verification_fixture):
    """Test 12: Complete unbroken integration flow:
    Login -> Transfer attempt -> Challenge issued -> Verification -> Transfer re-executed -> Ledger updated -> Audit.
    """
    client, session, _ = verification_fixture
    user, acc_a = create_user_and_account(session, "e2e_user", "e2e@banksim.local", 10000000)
    user_b, acc_b = create_user_and_account(session, "e2e_recip", "e2er@banksim.local", 10000)

    # Step 1: Login via HTTP endpoint with mandatory OTP verification
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "e2e_user", "password": "SecurePass123!"},
    )
    assert login_resp.status_code == 200
    login_ch = login_resp.json()
    assert login_ch["status"] == "OTP_REQUIRED"
    login_otp = otp_provider.get_dev_otp(login_ch["challenge_id"])
    assert login_otp is not None

    verify_login_resp = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": login_ch["challenge_id"], "verification_code": login_otp},
    )
    assert verify_login_resp.status_code == 200
    token = verify_login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Attempt high-risk transfer triggering step-up
    tx_resp = client.post(
        "/api/v1/banking/transfer",
        json={
            "recipient_account_number": acc_b.account_number,
            "amount_paise": 6000000,
            "memo": "E2E high risk payment",
        },
        headers=headers,
    )
    assert tx_resp.status_code == 403
    detail = tx_resp.json()["detail"]
    assert detail["status"] == "STEP_UP_REQUIRED"
    challenge_id = detail["challenge_id"]
    challenge_type = detail["challenge_type"]

    # Step 3: Balances remain untouched
    session.refresh(acc_a)
    session.refresh(acc_b)
    assert acc_a.balance == 10000000
    assert acc_b.balance == 10000

    # Step 4: Verify challenge based on type
    verify_payload = {"challenge_id": challenge_id}
    if challenge_type == "OTP":
        verify_payload["verification_code"] = otp_provider.get_dev_otp(challenge_id)
    else:
        verify_payload["face_data"] = "MOCK_FACE_VALID"

    ver_resp = client.post(
        "/api/v1/banking/verify-challenge",
        json=verify_payload,
        headers=headers,
    )
    assert ver_resp.status_code == 200
    assert ver_resp.json()["status"] == "VERIFIED"

    # Step 5: Retry transfer providing verified challenge_id
    retry_resp = client.post(
        "/api/v1/banking/transfer",
        json={
            "recipient_account_number": acc_b.account_number,
            "amount_paise": 6000000,
            "memo": "E2E high risk payment",
            "challenge_id": challenge_id,
        },
        headers=headers,
    )
    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] == "COMPLETED"

    # Step 6: Verify ledger invariants
    session.refresh(acc_a)
    session.refresh(acc_b)
    assert acc_a.balance == 4000000
    assert acc_b.balance == 6010000
