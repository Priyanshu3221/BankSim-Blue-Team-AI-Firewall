"""Automated tests for BankSim database models, constraints, and relationships (Phase 2)."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from database import Base, set_sqlite_pragma
from models import (
    Account,
    AccountType,
    ChallengePurpose,
    ChallengeStatus,
    ChallengeType,
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    Transaction,
    TransactionStatus,
    User,
    UserRole,
    VerificationChallenge,
)


@pytest.fixture(scope="function")
def test_db_session():
    """Create an isolated in-memory SQLite database and session for each test."""
    # Use SQLite in-memory with StaticPool/shared connection behavior for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    # Ensure foreign key pragma is applied to the test engine
    event.listen(engine, "connect", set_sqlite_pragma)

    # Initialize all tables
    Base.metadata.create_all(bind=engine)

    SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionTesting()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_tables_initialize_successfully(test_db_session):
    """Test 1: Verify all 5 expected database tables initialize successfully."""
    engine = test_db_session.get_bind()
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    expected_tables = {
        "users",
        "accounts",
        "transactions",
        "security_events",
        "verification_challenges",
    }
    for table in expected_tables:
        assert table in table_names, f"Table '{table}' was not initialized."


def test_user_persistence_and_retrieval(test_db_session: Session):
    """Test 2: Users can be persisted and retrieved correctly."""
    user = User(
        username="john_doe",
        email="john.doe@example.banksim",
        password_hash="mock_hash_for_phase2_testing",
        role=UserRole.USER.value,
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()

    retrieved = (
        test_db_session.query(User).filter_by(username="john_doe").first()
    )
    assert retrieved is not None
    assert retrieved.id is not None
    assert retrieved.email == "john.doe@example.banksim"
    assert retrieved.role == "USER"
    assert retrieved.is_active is True
    assert retrieved.created_at is not None


def test_duplicate_username_and_email_rejected(test_db_session: Session):
    """Test 3: Duplicate usernames or emails are rejected by unique constraints."""
    user1 = User(
        username="unique_user",
        email="unique@banksim.local",
        role=UserRole.USER.value,
    )
    test_db_session.add(user1)
    test_db_session.commit()

    # Attempt duplicate username
    user_dup_name = User(
        username="unique_user",
        email="different@banksim.local",
        role=UserRole.USER.value,
    )
    test_db_session.add(user_dup_name)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

    # Attempt duplicate email
    user_dup_email = User(
        username="different_user",
        email="unique@banksim.local",
        role=UserRole.USER.value,
    )
    test_db_session.add(user_dup_email)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()


def test_accounts_link_to_correct_users(test_db_session: Session):
    """Test 4: Accounts correctly associate with their owner user."""
    user = User(
        username="alice_banking",
        email="alice@banksim.local",
        role=UserRole.USER.value,
    )
    test_db_session.add(user)
    test_db_session.commit()

    account1 = Account(
        user_id=user.id,
        account_number="AC-10001",
        account_type=AccountType.SAVINGS.value,
        balance=150000,  # 1,500.00 INR in paise
        currency="INR",
    )
    account2 = Account(
        user_id=user.id,
        account_number="AC-10002",
        account_type=AccountType.CURRENT.value,
        balance=500000,  # 5,000.00 INR in paise
        currency="INR",
    )
    test_db_session.add_all([account1, account2])
    test_db_session.commit()

    test_db_session.refresh(user)
    assert len(user.accounts) == 2
    assert {acc.account_number for acc in user.accounts} == {
        "AC-10001",
        "AC-10002",
    }
    assert account1.user.username == "alice_banking"


def test_duplicate_account_number_rejected(test_db_session: Session):
    """Test 5: Duplicate account numbers are rejected by unique constraints."""
    user = User(username="bob_user", email="bob@banksim.local")
    test_db_session.add(user)
    test_db_session.commit()

    acc1 = Account(
        user_id=user.id,
        account_number="AC-DUPLICATE",
        account_type=AccountType.SAVINGS.value,
        balance=1000,
    )
    test_db_session.add(acc1)
    test_db_session.commit()

    acc2 = Account(
        user_id=user.id,
        account_number="AC-DUPLICATE",
        account_type=AccountType.CURRENT.value,
        balance=2000,
    )
    test_db_session.add(acc2)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()


def test_invalid_roles_and_statuses_rejected(test_db_session: Session):
    """Test 6: Database CHECK constraints reject invalid roles, types, and statuses."""
    # Invalid user role
    invalid_user = User(
        username="super_hacker",
        email="hacker@banksim.local",
        role="SUPERADMIN_INVALID",
    )
    test_db_session.add(invalid_user)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

    # Valid user for foreign key requirements
    valid_user = User(username="valid_user", email="valid@banksim.local")
    test_db_session.add(valid_user)
    test_db_session.commit()

    # Invalid account type
    invalid_account = Account(
        user_id=valid_user.id,
        account_number="AC-INVALID-TYPE",
        account_type="BITCOIN_WALLET",
        balance=100,
    )
    test_db_session.add(invalid_account)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

    # Valid accounts for transaction check
    acc1 = Account(
        user_id=valid_user.id,
        account_number="AC-TX1",
        account_type=AccountType.SAVINGS.value,
        balance=10000,
    )
    acc2 = Account(
        user_id=valid_user.id,
        account_number="AC-TX2",
        account_type=AccountType.SAVINGS.value,
        balance=10000,
    )
    test_db_session.add_all([acc1, acc2])
    test_db_session.commit()

    # Invalid transaction status
    invalid_tx = Transaction(
        sender_account_id=acc1.id,
        recipient_account_id=acc2.id,
        amount_paise=1000,
        status="REVERSED_UNAUTHORIZED",
        reference="TX-INV-STATUS",
    )
    test_db_session.add(invalid_tx)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

    # Invalid security event severity
    invalid_event = SecurityEvent(
        event_type=SecurityEventType.THREAT_DETECTED.value,
        severity="APOCALYPTIC",
        description="Invalid severity test",
    )
    test_db_session.add(invalid_event)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()


def test_negative_balances_and_non_positive_amounts_rejected(
    test_db_session: Session,
):
    """Test 7: Negative balances and non-positive transfer amounts are rejected."""
    user = User(username="monetary_user", email="money@banksim.local")
    test_db_session.add(user)
    test_db_session.commit()

    # Negative balance rejected
    neg_acc = Account(
        user_id=user.id,
        account_number="AC-NEGATIVE",
        balance=-1,  # Negative balance prohibited
    )
    test_db_session.add(neg_acc)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

    # Valid accounts
    acc_sender = Account(
        user_id=user.id, account_number="AC-SEND", balance=50000
    )
    acc_recv = Account(user_id=user.id, account_number="AC-RECV", balance=50000)
    test_db_session.add_all([acc_sender, acc_recv])
    test_db_session.commit()

    # Zero amount rejected
    tx_zero = Transaction(
        sender_account_id=acc_sender.id,
        recipient_account_id=acc_recv.id,
        amount_paise=0,  # Must be strictly positive
        reference="TX-ZERO-PAISE",
    )
    test_db_session.add(tx_zero)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

    # Negative amount rejected
    tx_neg = Transaction(
        sender_account_id=acc_sender.id,
        recipient_account_id=acc_recv.id,
        amount_paise=-1000,  # Negative transfer prohibited
        reference="TX-NEG-PAISE",
    )
    test_db_session.add(tx_neg)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()


def test_transaction_same_sender_recipient_rejected(test_db_session: Session):
    """Test 8: Transaction cannot reference the same account as sender and recipient."""
    user = User(username="loop_user", email="loop@banksim.local")
    test_db_session.add(user)
    test_db_session.commit()

    acc = Account(user_id=user.id, account_number="AC-LOOP", balance=10000)
    test_db_session.add(acc)
    test_db_session.commit()

    tx_self = Transaction(
        sender_account_id=acc.id,
        recipient_account_id=acc.id,  # Same account!
        amount_paise=500,
        reference="TX-SELF-TRANSFER",
    )
    test_db_session.add(tx_self)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()


def test_security_event_risk_scores_rejected(test_db_session: Session):
    """Test 9: Risk scores outside [0, 100] are rejected by CheckConstraint."""
    # Risk score > 100 rejected
    event_high = SecurityEvent(
        event_type=SecurityEventType.THREAT_DETECTED.value,
        severity=SecuritySeverity.HIGH.value,
        description="Risk score too high",
        risk_score=101,
    )
    test_db_session.add(event_high)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

    # Risk score < 0 rejected
    event_low = SecurityEvent(
        event_type=SecurityEventType.THREAT_DETECTED.value,
        severity=SecuritySeverity.LOW.value,
        description="Risk score negative",
        risk_score=-5,
    )
    test_db_session.add(event_low)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

    # Valid risk score (0, 50, 100, None) succeeds
    event_valid = SecurityEvent(
        event_type=SecurityEventType.RATE_LIMIT.value,
        severity=SecuritySeverity.MEDIUM.value,
        description="Valid security event logged",
        risk_score=85,
    )
    test_db_session.add(event_valid)
    test_db_session.commit()
    assert event_valid.id is not None
    assert event_valid.risk_score == 85


def test_verification_challenge_negative_attempts_rejected(
    test_db_session: Session,
):
    """Test 10: Verification challenges cannot have negative attempt counts."""
    user = User(username="challenge_user", email="challenge@banksim.local")
    test_db_session.add(user)
    test_db_session.commit()

    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=5)

    # Negative attempt count rejected
    challenge_neg = VerificationChallenge(
        user_id=user.id,
        challenge_type=ChallengeType.OTP.value,
        purpose=ChallengePurpose.LOGIN.value,
        attempt_count=-1,
        expires_at=expires,
    )
    test_db_session.add(challenge_neg)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

    # Valid challenge with attempt_count >= 0 succeeds
    challenge_valid = VerificationChallenge(
        user_id=user.id,
        challenge_type=ChallengeType.OTP.value,
        purpose=ChallengePurpose.LOGIN.value,
        attempt_count=0,
        expires_at=expires,
    )
    test_db_session.add(challenge_valid)
    test_db_session.commit()
    assert challenge_valid.id is not None
    assert challenge_valid.attempt_count == 0


def test_foreign_key_enforcement(test_db_session: Session):
    """Test 11: Foreign key enforcement prevents orphaned records."""
    # Account with non-existent user_id
    orphan_acc = Account(
        user_id=999999,  # Non-existent User ID
        account_number="AC-ORPHAN",
        balance=1000,
    )
    test_db_session.add(orphan_acc)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()

    # VerificationChallenge with non-existent user_id
    orphan_challenge = VerificationChallenge(
        user_id=999999,
        challenge_type=ChallengeType.OTP.value,
        purpose=ChallengePurpose.LOGIN.value,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    test_db_session.add(orphan_challenge)
    with pytest.raises(IntegrityError):
        test_db_session.commit()
    test_db_session.rollback()
