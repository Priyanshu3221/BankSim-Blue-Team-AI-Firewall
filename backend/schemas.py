"""Pydantic validation and representation schemas for BankSim entities."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.models import (
    AccountType,
    ChallengePurpose,
    ChallengeStatus,
    ChallengeType,
    SecurityEventType,
    SecuritySeverity,
    TransactionStatus,
    UserRole,
)


# --- User Schemas ---


class UserBase(BaseModel):
    """Base user fields."""

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Valid email address",
    )
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    phone_verified: bool = False
    email_verified: bool = False
    role: UserRole = UserRole.USER
    is_active: bool = True


class RegisterRequest(BaseModel):
    """User registration credentials and details."""

    full_name: str = Field(..., min_length=2, max_length=100, description="Full customer name")
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Valid customer email address",
    )
    phone_number: str = Field(
        ...,
        min_length=8,
        max_length=20,
        pattern=r"^\+?[0-9]{8,15}$",
        description="Customer mobile number with optional + country code",
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=30,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Alphanumeric username",
    )
    password: str = Field(..., min_length=8, max_length=128, description="Strong customer password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Password confirmation")


class RegisterResponse(BaseModel):
    """Safe response returned upon account registration."""

    user_id: int
    username: str
    email: str
    full_name: Optional[str] = None
    account_number: str
    initial_balance_inr: float
    verification_status: str
    message: str


class UserCreate(UserBase):
    """Schema for user creation (Phase 2 validation)."""

    password_hash: Optional[str] = None


class UserRead(UserBase):
    """User representation schema (never leaks password hashes)."""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Authentication Schemas ---


class LoginRequest(BaseModel):
    """Credentials required for user login."""

    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class LoginChallengeResponse(BaseModel):
    """Response returned upon valid credentials requiring mandatory OTP verification."""

    status: str = "OTP_REQUIRED"
    challenge_id: int
    challenge_type: str = "OTP"
    purpose: str = "LOGIN"
    expires_in_seconds: int
    cooldown_seconds: int
    message: str


class VerifyLoginOTPRequest(BaseModel):
    """Payload to complete mandatory login OTP verification."""

    challenge_id: int = Field(..., gt=0, description="Active login verification challenge ID")
    verification_code: str = Field(
        ..., min_length=6, max_length=6, description="6-digit One-Time Password"
    )


class ResendOTPRequest(BaseModel):
    """Request to generate and dispatch a new OTP for an active login challenge."""

    challenge_id: int = Field(..., gt=0, description="Active login verification challenge ID")


class ResendOTPResponse(BaseModel):
    """Response returned when an OTP is resent."""

    status: str = "OTP_RESENT"
    challenge_id: int
    cooldown_seconds: int
    expires_in_seconds: int
    message: str


class DevOTPResponse(BaseModel):
    """Development-only response exposing mock mailbox OTP for local testing."""

    challenge_id: int
    dev_otp: Optional[str]
    environment: str
    notice: str


class TokenResponse(BaseModel):
    """Authentication session response upon successful login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    role: str
    user: Optional[UserRead] = None


# --- Account Schemas ---


class AccountBase(BaseModel):
    """Base account fields."""

    account_number: str = Field(..., min_length=5, max_length=32)
    account_type: AccountType = AccountType.SAVINGS
    currency: str = Field(default="INR", min_length=3, max_length=3)
    is_active: bool = True


class AccountRead(AccountBase):
    """Account representation schema."""

    id: int
    user_id: int
    balance: int = Field(..., ge=0, description="Balance in paise (minor units)")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Transaction Schemas ---


class TransactionBase(BaseModel):
    """Base transaction fields."""

    sender_account_id: int
    recipient_account_id: int
    amount_paise: int = Field(
        ..., gt=0, description="Positive transfer amount in paise"
    )
    memo: Optional[str] = Field(default=None, max_length=255)


class TransactionRead(TransactionBase):
    """Transaction representation schema."""

    id: int
    status: TransactionStatus
    reference: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerTransactionItem(BaseModel):
    """Customer-facing ledger item detailing debit or credit transaction."""

    id: int
    reference: str
    transaction_reference: Optional[str] = None
    created_at: datetime
    amount_paise: int
    amount_inr: float
    direction: str  # "CREDIT" or "DEBIT"
    counterparty_account: str
    status: str
    description: Optional[str] = None
    memo: Optional[str] = None
    sender_account_number: Optional[str] = None
    recipient_account_number: Optional[str] = None


class CustomerTransactionListResponse(BaseModel):
    """Paginated list of customer transactions with filters."""

    items: List[CustomerTransactionItem]
    total: int
    limit: int
    offset: int


# --- Security Event Schemas ---


class SecurityEventBase(BaseModel):
    """Base security event fields."""

    user_id: Optional[int] = None
    event_type: SecurityEventType
    severity: SecuritySeverity
    description: str = Field(..., max_length=500)
    risk_score: Optional[int] = Field(default=None, ge=0, le=100)
    request_id: Optional[str] = Field(default=None, max_length=64)


class SecurityEventRead(SecurityEventBase):
    """Security event representation schema."""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Verification Challenge Schemas ---


class VerificationChallengeBase(BaseModel):
    """Base verification challenge metadata."""

    user_id: int
    challenge_type: ChallengeType
    purpose: ChallengePurpose
    status: ChallengeStatus = ChallengeStatus.PENDING
    attempt_count: int = Field(default=0, ge=0)
    expires_at: datetime


class VerificationChallengeRead(VerificationChallengeBase):
    """Verification challenge representation schema."""

    id: int
    created_at: datetime
    verified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Risk Engine Schemas ---


class RiskLevel(str, Enum):
    """Categorical risk classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskOutcome(str, Enum):
    """Defensive recommendation produced by the risk engine."""

    ALLOW = "ALLOW"
    STEP_UP_VERIFICATION = "STEP_UP_VERIFICATION"
    RESTRICT = "RESTRICT"
    BLOCK = "BLOCK"


class RiskSignalResult(BaseModel):
    """Evaluation output for an individual risk signal."""

    signal_name: str
    triggered: bool
    score_impact: int
    description: str
    evidence: Optional[Dict[str, Any]] = None
    status: str = "evaluated"  # evaluated, unknown, or omitted


class RiskAssessmentRequest(BaseModel):
    """Parameters submitted to request an assessment for a proposed transaction."""

    sender_account_id: int
    recipient_account_number: str = Field(..., min_length=1, max_length=32)
    amount_paise: int = Field(..., gt=0, description="Proposed transfer amount in paise")
    memo: Optional[str] = Field(default=None, max_length=255, description="Optional untrusted memo to analyze")
    client_ip: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=255)
    session_age_seconds: Optional[int] = Field(default=None, ge=0)


class RiskAssessmentResponse(BaseModel):
    """Authoritative assessment output from the adaptive risk engine."""

    risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    recommended_outcome: RiskOutcome
    triggered_signals: List[RiskSignalResult]
    all_signals: List[RiskSignalResult]
    explanation: str
    evaluated_at: datetime


# --- AI Threat Analyzer Schemas ---


class ThreatCategory(str, Enum):
    """Allowlist of detected adversarial threat categories."""

    PROMPT_INJECTION = "PROMPT_INJECTION"
    JAILBREAK = "JAILBREAK"
    ADMIN_IMPERSONATION = "ADMIN_IMPERSONATION"
    COERCION = "COERCION"
    SUSPICIOUS_INSTRUCTION = "SUSPICIOUS_INSTRUCTION"
    BENIGN = "BENIGN"
    UNKNOWN = "UNKNOWN"


class AIThreatAction(str, Enum):
    """Defensive actions recommended by the AI threat analyzer."""

    ALLOW = "ALLOW"
    FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW"
    STEP_UP_VERIFICATION = "STEP_UP_VERIFICATION"
    BLOCK = "BLOCK"


class AIThreatAnalysisRequest(BaseModel):
    """Request to inspect untrusted text (e.g. transaction memo) for adversarial threats."""

    text: str = Field(..., min_length=1, max_length=1000, description="Untrusted text to analyze")
    context_type: Optional[str] = Field(default="transaction_memo", max_length=50)


class AIThreatAnalysisResponse(BaseModel):
    """Structured, validated assessment produced by the AI threat analyzer."""

    threat_detected: bool
    threat_categories: List[ThreatCategory]
    evidence: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    recommended_action: AIThreatAction
    explanation: str = Field(..., max_length=1000)
    provider_used: str = Field(default="openai", max_length=50)
    analyzed_at: datetime


# --- Banking Transfer Schemas ---


class TransferRequest(BaseModel):
    """Secure mock-bank transfer request payload."""

    recipient_account_number: str = Field(
        ..., min_length=1, max_length=32, description="Destination account number"
    )
    amount_paise: int = Field(
        ..., gt=0, description="Positive transfer amount in paise (minor currency units)"
    )
    sender_account_id: Optional[int] = Field(
        default=None,
        description="Optional sender account ID; must belong to authenticated user",
    )
    memo: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional transaction memo analyzed for threats",
    )
    challenge_id: Optional[int] = Field(
        default=None,
        description="Optional ID of completed verification challenge for step-up authorization",
    )


class TransferResponse(BaseModel):
    """Response returned upon mock-bank transfer execution or restriction."""

    success: bool
    status: str  # COMPLETED, STEP_UP_REQUIRED, BLOCKED, FAILED
    message: str
    reference: Optional[str] = None
    transaction_id: Optional[int] = None
    amount_paise: int
    sender_account_number: str
    recipient_account_number: str
    remaining_balance_paise: Optional[int] = None
    risk_score: int
    risk_level: RiskLevel
    recommended_outcome: RiskOutcome
    challenge_id: Optional[int] = None
    challenge_type: Optional[str] = None
    executed_at: datetime

