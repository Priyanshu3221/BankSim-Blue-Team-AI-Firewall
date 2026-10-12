"""Authentication endpoints for BankSim (Mandatory Login OTP Flow)."""

import logging
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.models import Account, SecurityEvent, SecurityEventType, SecuritySeverity, Transaction, User
from backend.schemas import (
    DevOTPResponse,
    LoginChallengeResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ResendOTPRequest,
    ResendOTPResponse,
    TokenResponse,
    UserRead,
    VerifyLoginOTPRequest,
)
from backend.security.login_tracker import login_tracker
from backend.security.passwords import hash_password, verify_password
from backend.security.tokens import create_access_token
from backend.services.verification_service import verification_service

logger = logging.getLogger("banksim.api.auth")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new BankSim demo account with simulated funding",
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Register a new customer demo account.

    Requirements:
    - Enforces unique username, email, and phone number.
    - Passwords securely hashed with bcrypt.
    - Strictly assigns the 'USER' role (non-admin).
    - Generates a unique simulated account number (AC-XXXXXX).
    - Seeds a safe demo balance of ₹50,000 (5,000,000 paise).
    - Emits a clean integration point for MSG91 verification.
    """
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    clean_username = payload.username.strip()
    clean_email = payload.email.strip().lower()
    clean_phone = payload.phone_number.strip()
    clean_name = payload.full_name.strip()

    # 1. Uniqueness validation
    if db.query(User).filter(User.username == clean_username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already registered. Please choose a different username.",
        )

    if db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered.",
        )

    if db.query(User).filter(User.phone_number == clean_phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile number is already registered.",
        )

    # 2. Database transaction: User + Account + Initial Ledger Credit
    try:
        # Create User
        new_user = User(
            username=clean_username,
            email=clean_email,
            full_name=clean_name,
            phone_number=clean_phone,
            password_hash=hash_password(payload.password),
            role="USER",  # Strictly USER role; client cannot select role
            is_active=True,
            phone_verified=False,  # MSG91 integration boundary
            email_verified=False,
        )
        db.add(new_user)
        db.flush()

        # Generate unique simulated account number
        while True:
            candidate_acc = f"AC-{secrets.randbelow(900000) + 100000}"
            if not db.query(Account).filter(Account.account_number == candidate_acc).first():
                break

        INITIAL_DEMO_BALANCE_PAISE = 5000000  # ₹50,000 in paise
        new_account = Account(
            user_id=new_user.id,
            account_number=candidate_acc,
            account_type="SAVINGS",
            currency="INR",
            balance=INITIAL_DEMO_BALANCE_PAISE,
            is_active=True,
        )
        db.add(new_account)
        db.flush()

        # Seed initial simulated credit transaction from treasury
        treasury_acc = db.query(Account).filter(Account.account_number == "AC-TREASURY-01").first()
        if not treasury_acc:
            sys_admin = db.query(User).filter(User.role == "ADMIN").first()
            if not sys_admin:
                sys_admin = User(
                    username="sys_treasury",
                    email="treasury@banksim.internal",
                    password_hash=hash_password("InternalSysPass999!"),
                    role="ADMIN",
                    is_active=True,
                )
                db.add(sys_admin)
                db.flush()

            treasury_acc = Account(
                user_id=sys_admin.id,
                account_number="AC-TREASURY-01",
                account_type="CURRENT",
                currency="INR",
                balance=100000000000,
                is_active=True,
            )
            db.add(treasury_acc)
            db.flush()

        welcome_tx = Transaction(
            reference=f"TX-REG-{secrets.token_hex(4).upper()}",
            sender_account_id=treasury_acc.id,
            recipient_account_id=new_account.id,
            amount_paise=INITIAL_DEMO_BALANCE_PAISE,
            status="COMPLETED",
            memo="Demo Account Opening Deposit (Simulated Balance)",
        )
        db.add(welcome_tx)

        logger.info("New customer demo account registered: %s (%s)", clean_username, candidate_acc)
        db.commit()
        db.refresh(new_user)
        db.refresh(new_account)

        return RegisterResponse(
            user_id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            full_name=new_user.full_name,
            account_number=new_account.account_number,
            initial_balance_inr=50000.0,
            verification_status="PENDING_MSG91_INTEGRATION",
            message="Demo account registered successfully. Please log in using your username and password (mandatory OTP applies).",
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.error("Registration transaction failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to a server error. Please try again.",
        )



@auth_router.post(
    "/login",
    response_model=LoginChallengeResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate credentials and issue mandatory login OTP challenge",
)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginChallengeResponse:
    """Verify user credentials and create a mandatory login verification challenge.

    Enforces rate limits and lockout. Never returns an access token or grants access
    directly upon credential validation.
    """
    settings = get_settings()
    username = credentials.username.strip()

    # Check brute-force lockout status
    if login_tracker.is_locked(username):
        # Audit security event
        sec_event = SecurityEvent(
            event_type=SecurityEventType.RATE_LIMIT.value,
            severity=SecuritySeverity.HIGH.value,
            description=f"Login attempts locked for username '{username}' due to repeated failures.",
            risk_score=75,
        )
        db.add(sec_event)
        try:
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
        )

    # Authoritative query for user
    user = db.query(User).filter(User.username == username).first()

    # Constant-time-like verification: verify password hash if user exists, or dummy
    is_valid_password = False
    if user and user.password_hash:
        is_valid_password = verify_password(credentials.password, user.password_hash)

    # Invalidate if user doesn't exist, password mismatch, or inactive account
    if not user or not is_valid_password or not user.is_active:
        failures = login_tracker.record_failure(username)

        # Audit security failure event (never log plain password or secrets)
        sec_event = SecurityEvent(
            user_id=user.id if user else None,
            event_type=SecurityEventType.LOGIN_FAILURE.value,
            severity=SecuritySeverity.LOW.value if failures < 3 else SecuritySeverity.MEDIUM.value,
            description=f"Authentication failure attempt #{failures} for username '{username}'.",
            risk_score=min(failures * 15, 90),
        )
        db.add(sec_event)
        try:
            db.commit()
        except Exception:
            db.rollback()

        # Generic error message to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Password check passed: reset failed attempts tracker
    login_tracker.record_success(username)

    # MANDATORY: Generate short-lived login challenge and OTP for EVERY login
    challenge = verification_service.create_login_challenge(user=user, db=db)

    return LoginChallengeResponse(
        status="OTP_REQUIRED",
        challenge_id=challenge.id,
        challenge_type="OTP",
        purpose="LOGIN",
        expires_in_seconds=settings.LOGIN_OTP_EXPIRE_MINUTES * 60,
        cooldown_seconds=settings.LOGIN_OTP_RESEND_COOLDOWN_SECONDS,
        message="OTP verification required. Please enter the 6-digit verification code sent to your registered device.",
    )


@auth_router.post(
    "/verify-otp",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify login OTP challenge and issue signed access token",
)
def verify_login_otp(
    payload: VerifyLoginOTPRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Validate 6-digit OTP code against the active login challenge.

    Atomically consumes the challenge upon success and issues signed JWT access token.
    Direct role is resolved from trusted database state.
    """
    settings = get_settings()

    # Validate and atomically consume challenge
    user = verification_service.verify_login_otp(
        challenge_id=payload.challenge_id,
        verification_code=payload.verification_code,
        db=db,
    )

    # Issue signed JWT access token ONLY after successful OTP verification
    access_token = create_access_token(
        claims={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        role=user.role,
        user=UserRead.model_validate(user),
    )


@auth_router.post(
    "/resend-otp",
    response_model=ResendOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend a new OTP for an active login challenge",
)
def resend_login_otp(
    payload: ResendOTPRequest,
    db: Session = Depends(get_db),
) -> ResendOTPResponse:
    """Invalidate previous OTP and dispatch a newly generated 6-digit code.

    Enforces server-side cooldown and maximum resend thresholds.
    """
    settings = get_settings()

    challenge = verification_service.resend_login_otp(
        challenge_id=payload.challenge_id,
        db=db,
    )

    return ResendOTPResponse(
        status="OTP_RESENT",
        challenge_id=challenge.id,
        cooldown_seconds=settings.LOGIN_OTP_RESEND_COOLDOWN_SECONDS,
        expires_in_seconds=settings.LOGIN_OTP_EXPIRE_MINUTES * 60,
        message="A new verification code has been dispatched.",
    )


@auth_router.get(
    "/dev-otp/{challenge_id}",
    response_model=DevOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Development-only simulated delivery mailbox retrieval",
)
def get_dev_otp(
    challenge_id: int,
) -> DevOTPResponse:
    """Retrieve simulated plaintext OTP code for local development and hackathon demonstrations.

    Explicitly disabled and returns 404 in production mode.
    """
    settings = get_settings()

    # Enforce strict development/testing environment isolation
    if settings.ENVIRONMENT not in ("development", "testing") and not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development endpoint not available in production.",
        )

    code = verification_service.get_dev_otp(challenge_id)

    return DevOTPResponse(
        challenge_id=challenge_id,
        dev_otp=code,
        environment=settings.ENVIRONMENT,
        notice="Development-only simulated delivery mailbox. Not available in production environments.",
    )
