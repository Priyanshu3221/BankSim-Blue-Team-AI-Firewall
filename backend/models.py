"""SQLAlchemy 2.x ORM models and database constraints for BankSim."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# --- Domain Enums ---


class UserRole(str, Enum):
    """Allowed user authorization roles."""

    USER = "USER"
    ADMIN = "ADMIN"


class AccountType(str, Enum):
    """Supported simulated banking account types."""

    SAVINGS = "SAVINGS"
    CURRENT = "CURRENT"


class TransactionStatus(str, Enum):
    """Status lifecycle of simulated transactions."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class SecurityEventType(str, Enum):
    """Categories of security and threat events."""

    LOGIN_FAILURE = "LOGIN_FAILURE"
    RATE_LIMIT = "RATE_LIMIT"
    THREAT_DETECTED = "THREAT_DETECTED"
    TRANSACTION_BLOCKED = "TRANSACTION_BLOCKED"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"


class SecuritySeverity(str, Enum):
    """Severity classification for security events."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ChallengeType(str, Enum):
    """Forms of risk-based verification challenges."""

    OTP = "OTP"
    FACE_VERIFICATION = "FACE_VERIFICATION"


class ChallengePurpose(str, Enum):
    """Trigger context requiring challenge verification."""

    LOGIN = "LOGIN"
    HIGH_RISK_TRANSACTION = "HIGH_RISK_TRANSACTION"


class ChallengeStatus(str, Enum):
    """Resolution status of a verification challenge."""

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    CONSUMED = "CONSUMED"


# --- ORM Models ---


class User(Base):
    """User account entity representing customers and security administrators."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.USER.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_user_role"),
    )

    # Relationships
    accounts: Mapped[List["Account"]] = relationship(
        "Account", back_populates="user", cascade="all, delete-orphan"
    )
    security_events: Mapped[List["SecurityEvent"]] = relationship(
        "SecurityEvent", back_populates="user"
    )
    challenges: Mapped[List["VerificationChallenge"]] = relationship(
        "VerificationChallenge", back_populates="user", cascade="all, delete-orphan"
    )


class Account(Base):
    """Simulated banking account owned by a user."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_number: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    account_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AccountType.SAVINGS.value,
    )
    # Monetary balance stored strictly in integer minor units (paise)
    balance: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "account_type IN ('SAVINGS', 'CURRENT')", name="ck_account_type"
        ),
        CheckConstraint("balance >= 0", name="ck_account_balance_non_negative"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    sent_transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="Transaction.sender_account_id",
        back_populates="sender_account",
    )
    received_transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="Transaction.recipient_account_id",
        back_populates="recipient_account",
    )


class Transaction(Base):
    """Simulated financial transfer between two distinct accounts."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    recipient_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Amount stored strictly in positive integer minor units (paise)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=TransactionStatus.PENDING.value,
        nullable=False,
    )
    memo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reference: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_transaction_amount_positive"),
        CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'BLOCKED', 'FAILED')",
            name="ck_transaction_status",
        ),
        CheckConstraint(
            "sender_account_id != recipient_account_id",
            name="ck_transaction_distinct_accounts",
        ),
    )

    # Relationships
    sender_account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[sender_account_id],
        back_populates="sent_transactions",
    )
    recipient_account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[recipient_account_id],
        back_populates="received_transactions",
    )


class SecurityEvent(Base):
    """Audit log entry capturing security anomalies and firewall decisions."""

    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('LOGIN_FAILURE', 'RATE_LIMIT', 'THREAT_DETECTED', 'TRANSACTION_BLOCKED', 'STEP_UP_REQUIRED')",
            name="ck_security_event_type",
        ),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_security_event_severity",
        ),
        CheckConstraint(
            "risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)",
            name="ck_security_event_risk_score",
        ),
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="security_events"
    )


class VerificationChallenge(Base):
    """Metadata tracking multi-factor step-up challenges (OTP / Face).

    Biometric images, templates, and plaintext OTP secrets are NEVER persisted.
    """

    __tablename__ = "verification_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    challenge_type: Mapped[str] = mapped_column(String(30), nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default=ChallengeStatus.PENDING.value,
        nullable=False,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    code_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    transfer_payload_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    resend_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_resend_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "challenge_type IN ('OTP', 'FACE_VERIFICATION')",
            name="ck_challenge_type",
        ),
        CheckConstraint(
            "purpose IN ('LOGIN', 'HIGH_RISK_TRANSACTION')",
            name="ck_challenge_purpose",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'VERIFIED', 'EXPIRED', 'FAILED', 'CONSUMED')",
            name="ck_challenge_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_challenge_attempt_count_non_negative",
        ),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="challenges")
