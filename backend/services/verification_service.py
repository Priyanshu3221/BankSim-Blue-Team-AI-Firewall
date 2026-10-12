"""BankSim Verification Service — Secure Mock OTP and Risk-Based Face Verification.

Implements Phase 7 multi-factor step-up authentication:
1. Secure Mock OTP provider:
   - Cryptographically random 6-digit codes.
   - Salted SHA-256 hash storage; plaintext is NEVER persisted in the database or ordinary logs.
   - Isolated in-memory dev mailbox for test/development retrieval.
   - Enforces 3 failed attempts, expiration (15 minutes), and single-use consumption.
2. Mock Face Verification provider:
   - Simulated biometric liveness and feature matching.
   - Strictly obeys privacy constraints: NEVER persists raw images or facial templates.
   - Detects spoofing and mismatches.
3. Cryptographic binding:
   - Binds challenge to authenticated user, recipient account, amount, and challenge type.
   - Prevents replay attacks and cross-transfer parameter tampering.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import secrets
import threading
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import (
    ChallengePurpose,
    ChallengeStatus,
    ChallengeType,
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    User,
    VerificationChallenge,
)

logger = logging.getLogger("banksim.security.verification")
_login_verify_lock = threading.Lock()


def ensure_utc(dt: datetime) -> datetime:
    """Normalize naive or aware datetimes to UTC-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class MockOTPProvider:
    """Development-only Mock OTP Provider for simulated multi-factor authentication."""

    def __init__(self) -> None:
        # Isolated in-memory delivery store for automated tests and development.
        # Key: challenge_id (int) -> Value: plaintext OTP string
        # Never logged or persisted to disk/database.
        self._dev_mailbox: Dict[int, str] = {}

    def generate_otp(self, challenge_id: int) -> Tuple[str, str]:
        """Generate a cryptographically secure 6-digit random code and its salted hash.

        Returns (plaintext_code, salted_hash). Plaintext code is saved ONLY to dev mailbox.
        """
        code = f"{secrets.randbelow(1_000_000):06d}"
        salt = secrets.token_hex(16)
        digest = hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()
        code_hash = f"{salt}${digest}"

        # Store in dev mailbox for out-of-band delivery simulation in tests
        self._dev_mailbox[challenge_id] = code
        return code, code_hash

    def verify_otp(self, submitted_code: str, stored_hash: Optional[str]) -> bool:
        """Verify candidate code against stored salted hash with constant-time comparison."""
        if not stored_hash or "$" not in stored_hash or not submitted_code:
            return False

        salt, expected_digest = stored_hash.split("$", 1)
        candidate_digest = hashlib.sha256(f"{salt}:{submitted_code.strip()}".encode()).hexdigest()
        return hmac.compare_digest(candidate_digest, expected_digest)

    def get_dev_otp(self, challenge_id: int) -> Optional[str]:
        """Retrieve delivered OTP from isolated test/dev mailbox."""
        return self._dev_mailbox.get(challenge_id)

    def clear_dev_mailbox(self) -> None:
        """Clear test mailbox entries."""
        self._dev_mailbox.clear()


class MockFaceVerificationProvider:
    """Mock Biometric Face Verification Provider.

    Strictly obeys the BankSim security guarantee:
    Biometric images, templates, and plaintext embeddings are NEVER persisted.
    """

    def verify_face(
        self,
        face_data: Optional[str],
        user_id: int,
    ) -> Tuple[bool, str]:
        """Evaluate simulated face biometric submission.

        Returns (is_verified, reason_message).
        """
        if not face_data or not face_data.strip():
            return False, "Biometric data missing or empty."

        clean_token = face_data.strip().upper()

        # Simulated threat and failure scenarios
        if "SPOOF" in clean_token or "NON_LIVE" in clean_token:
            return False, "Biometric liveness check failed: spoofing attempt or replay presentation detected."

        if "MISMATCH" in clean_token or "UNRECOGNIZED" in clean_token:
            return False, "Biometric verification mismatch: facial signature does not match account profile."

        # Valid simulated markers
        if (
            clean_token in ("MOCK_FACE_VALID", "VALID_BIOMETRIC_DATA", "PASS")
            or clean_token.startswith("DATA:IMAGE/")
            or len(clean_token) >= 20  # Simulated valid biometric descriptor token
        ):
            return True, "Face verification succeeded with high biometric match confidence."

        return False, "Biometric verification failed: unrecognized facial biometric data."


class VerificationService:
    """Orchestrates creation, binding, verification, and consumption of step-up challenges."""

    def __init__(self) -> None:
        self.otp_provider = MockOTPProvider()
        self.face_provider = MockFaceVerificationProvider()
        self.settings = get_settings()

    def compute_transfer_payload_hash(
        self,
        user_id: int,
        recipient_account_number: str,
        amount_paise: int,
    ) -> str:
        """Compute SHA-256 fingerprint binding a challenge to specific transfer parameters."""
        raw = f"{user_id}:{recipient_account_number.strip().upper()}:{amount_paise}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def create_challenge(
        self,
        user_id: int,
        challenge_type: ChallengeType,
        purpose: ChallengePurpose,
        recipient_account_number: str,
        amount_paise: int,
        db: Session,
        expiry_minutes: int = 15,
    ) -> VerificationChallenge:
        """Issue a new step-up challenge cryptographically bound to the pending transfer."""
        now = datetime.now(timezone.utc)
        payload_hash = self.compute_transfer_payload_hash(
            user_id=user_id,
            recipient_account_number=recipient_account_number,
            amount_paise=amount_paise,
        )

        challenge = VerificationChallenge(
            user_id=user_id,
            challenge_type=challenge_type.value,
            purpose=purpose.value,
            status=ChallengeStatus.PENDING.value,
            attempt_count=0,
            expires_at=now + timedelta(minutes=expiry_minutes),
            transfer_payload_hash=payload_hash,
        )
        db.add(challenge)
        db.flush()  # Allocate challenge.id

        if challenge_type == ChallengeType.OTP:
            _, code_hash = self.otp_provider.generate_otp(challenge.id)
            challenge.code_hash = code_hash

        db.commit()
        db.refresh(challenge)
        return challenge

    def create_login_challenge(
        self,
        user: User,
        db: Session,
        expiry_minutes: Optional[int] = None,
    ) -> VerificationChallenge:
        """Create a mandatory login OTP challenge bound to the authenticated user."""
        now = datetime.now(timezone.utc)
        exp_minutes = expiry_minutes or self.settings.LOGIN_OTP_EXPIRE_MINUTES

        # Invalidate any existing pending login challenges for this user
        existing_pending = (
            db.query(VerificationChallenge)
            .filter(
                VerificationChallenge.user_id == user.id,
                VerificationChallenge.purpose == ChallengePurpose.LOGIN.value,
                VerificationChallenge.status == ChallengeStatus.PENDING.value,
            )
            .all()
        )
        for old_ch in existing_pending:
            old_ch.status = ChallengeStatus.EXPIRED.value

        challenge = VerificationChallenge(
            user_id=user.id,
            challenge_type=ChallengeType.OTP.value,
            purpose=ChallengePurpose.LOGIN.value,
            status=ChallengeStatus.PENDING.value,
            attempt_count=0,
            resend_count=0,
            expires_at=now + timedelta(minutes=exp_minutes),
            created_at=now,
            last_resend_at=now,
        )
        db.add(challenge)
        db.flush()

        _, code_hash = self.otp_provider.generate_otp(challenge.id)
        challenge.code_hash = code_hash
        db.commit()
        db.refresh(challenge)
        return challenge

    def verify_login_otp(
        self,
        challenge_id: int,
        verification_code: str,
        db: Session,
    ) -> User:
        """Validate and atomically consume login OTP challenge; returns verified User.

        Thread-safe and atomic to prevent double-consumption concurrency race conditions.
        """
        now = datetime.now(timezone.utc)

        with _login_verify_lock:
            challenge = (
                db.query(VerificationChallenge)
                .filter(VerificationChallenge.id == challenge_id)
                .first()
            )
            if not challenge:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Verification challenge not found.",
                )

            # 1. Enforce purpose
            if challenge.purpose != ChallengePurpose.LOGIN.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid challenge purpose '{challenge.purpose}' for login verification.",
                )

            # 2. Check consumption status
            if challenge.status == ChallengeStatus.CONSUMED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification challenge has already been consumed.",
                )

            if challenge.status == ChallengeStatus.FAILED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification challenge has been invalidated due to excessive failed attempts. Please sign in again.",
                )

            if challenge.status != ChallengeStatus.PENDING.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Verification challenge is no longer valid (status: {challenge.status}).",
                )

            # 3. Check expiration
            if ensure_utc(challenge.expires_at) <= now:
                challenge.status = ChallengeStatus.EXPIRED.value
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification code has expired. Please sign in again.",
                )

            # 4. Validate OTP code format
            code_str = verification_code.strip() if verification_code else ""
            if not code_str or len(code_str) != 6:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification code must be a 6-digit number.",
                )

            is_valid = self.otp_provider.verify_otp(
                submitted_code=code_str,
                stored_hash=challenge.code_hash,
            )
            challenge.attempt_count += 1

            if is_valid:
                # Atomically consume challenge
                challenge.status = ChallengeStatus.CONSUMED.value
                challenge.verified_at = now

                user = db.query(User).filter(User.id == challenge.user_id).first()
                if not user or not user.is_active:
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User account is invalid or inactive.",
                    )

                db.commit()
                db.refresh(challenge)
                return user
            else:
                max_attempts = self.settings.LOGIN_OTP_MAX_ATTEMPTS
                if challenge.attempt_count >= max_attempts:
                    challenge.status = ChallengeStatus.FAILED.value
                    sec_event = SecurityEvent(
                        user_id=challenge.user_id,
                        event_type=SecurityEventType.THREAT_DETECTED.value,
                        severity=SecuritySeverity.HIGH.value,
                        description=f"Login OTP challenge #{challenge.id} locked: exceeded maximum {max_attempts} verification attempts.",
                        risk_score=75,
                    )
                    db.add(sec_event)
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Maximum verification attempts exceeded. Challenge has been invalidated. Please sign in again.",
                    )
                else:
                    db.commit()
                    remaining = max_attempts - challenge.attempt_count
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid verification code. {remaining} attempt(s) remaining.",
                    )

    def resend_login_otp(
        self,
        challenge_id: int,
        db: Session,
    ) -> VerificationChallenge:
        """Invalidate previous OTP, generate a new code, and apply cooldown and limits."""
        now = datetime.now(timezone.utc)

        with _login_verify_lock:
            challenge = (
                db.query(VerificationChallenge)
                .filter(VerificationChallenge.id == challenge_id)
                .first()
            )
            if not challenge:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Verification challenge not found.",
                )

            if challenge.purpose != ChallengePurpose.LOGIN.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid challenge purpose '{challenge.purpose}' for login OTP resend.",
                )

            if challenge.status != ChallengeStatus.PENDING.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot resend code for challenge with status '{challenge.status}'. Please sign in again.",
                )

            if ensure_utc(challenge.expires_at) <= now:
                challenge.status = ChallengeStatus.EXPIRED.value
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification challenge has expired. Please sign in again.",
                )

            # Check resend count limit
            if challenge.resend_count >= self.settings.LOGIN_OTP_MAX_RESENDS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Maximum of {self.settings.LOGIN_OTP_MAX_RESENDS} resend requests reached. Please restart sign in.",
                )

            # Check resend cooldown
            last_sent = challenge.last_resend_at or challenge.created_at
            elapsed = (now - ensure_utc(last_sent)).total_seconds()
            if elapsed < self.settings.LOGIN_OTP_RESEND_COOLDOWN_SECONDS:
                wait_sec = int(self.settings.LOGIN_OTP_RESEND_COOLDOWN_SECONDS - elapsed) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {wait_sec} second(s) before requesting a new code.",
                )

            # Invalidate previous code by generating and setting a new OTP and hash
            _, new_code_hash = self.otp_provider.generate_otp(challenge.id)
            challenge.code_hash = new_code_hash
            challenge.resend_count += 1
            challenge.last_resend_at = now
            challenge.expires_at = now + timedelta(minutes=self.settings.LOGIN_OTP_EXPIRE_MINUTES)
            db.commit()
            db.refresh(challenge)
            return challenge

    def get_dev_otp(self, challenge_id: int) -> Optional[str]:
        """Retrieve plaintext OTP from isolated test/dev mailbox."""
        return self.otp_provider.get_dev_otp(challenge_id)

    def verify_challenge(
        self,
        challenge_id: int,
        current_user: User,
        db: Session,
        verification_code: Optional[str] = None,
        face_data: Optional[str] = None,
    ) -> VerificationChallenge:
        """Complete verification for a pending challenge with strict ownership and attempt checks."""
        now = datetime.now(timezone.utc)

        challenge = (
            db.query(VerificationChallenge)
            .filter(VerificationChallenge.id == challenge_id)
            .first()
        )
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification challenge not found.",
            )

        # Enforce purpose: banking step-up only handles HIGH_RISK_TRANSACTION
        if challenge.purpose != ChallengePurpose.HIGH_RISK_TRANSACTION.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid challenge purpose '{challenge.purpose}' for banking step-up verification.",
            )

        # 1. Enforce ownership: user cannot verify another user's challenge
        if challenge.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Verification challenge does not belong to authenticated user.",
            )

        # 2. Enforce challenge status
        if challenge.status != ChallengeStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Verification challenge is already {challenge.status}.",
            )

        # 3. Enforce expiration
        if ensure_utc(challenge.expires_at) <= now:
            challenge.status = ChallengeStatus.EXPIRED.value
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification challenge has expired.",
            )

        # 4. Evaluate challenge depending on type
        if challenge.challenge_type == ChallengeType.OTP.value:
            if not verification_code or not verification_code.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification code is required for OTP challenge.",
                )

            is_valid = self.otp_provider.verify_otp(
                submitted_code=verification_code,
                stored_hash=challenge.code_hash,
            )
            challenge.attempt_count += 1

            if is_valid:
                challenge.status = ChallengeStatus.VERIFIED.value
                challenge.verified_at = now
                db.commit()
                db.refresh(challenge)
                return challenge
            else:
                if challenge.attempt_count >= 3:
                    challenge.status = ChallengeStatus.FAILED.value
                    sec_event = SecurityEvent(
                        user_id=current_user.id,
                        event_type=SecurityEventType.THREAT_DETECTED.value,
                        severity=SecuritySeverity.HIGH.value,
                        description=f"OTP challenge {challenge.id} locked: exceeded maximum 3 verification attempts.",
                        risk_score=75,
                    )
                    db.add(sec_event)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid verification code provided.",
                )

        elif challenge.challenge_type == ChallengeType.FACE_VERIFICATION.value:
            if not face_data or not face_data.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Biometric face data is required for FACE_VERIFICATION challenge.",
                )

            is_valid, msg = self.face_provider.verify_face(
                face_data=face_data,
                user_id=current_user.id,
            )
            challenge.attempt_count += 1

            if is_valid:
                challenge.status = ChallengeStatus.VERIFIED.value
                challenge.verified_at = now
                db.commit()
                db.refresh(challenge)
                return challenge
            else:
                if challenge.attempt_count >= 3:
                    challenge.status = ChallengeStatus.FAILED.value
                    sec_event = SecurityEvent(
                        user_id=current_user.id,
                        event_type=SecurityEventType.THREAT_DETECTED.value,
                        severity=SecuritySeverity.HIGH.value,
                        description=f"Face verification challenge {challenge.id} locked: {msg} (maximum attempts exceeded).",
                        risk_score=80,
                    )
                    db.add(sec_event)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Face verification failed: {msg}",
                )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported challenge type '{challenge.challenge_type}'.",
            )

    def validate_and_consume_challenge(
        self,
        challenge_id: int,
        current_user: User,
        recipient_account_number: str,
        amount_paise: int,
        required_challenge_type: Optional[ChallengeType],
        db: Session,
    ) -> VerificationChallenge:
        """Validate verified challenge against transfer parameters and consume it atomically."""
        now = datetime.now(timezone.utc)

        challenge = (
            db.query(VerificationChallenge)
            .filter(VerificationChallenge.id == challenge_id)
            .first()
        )
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verification challenge not found.",
            )

        # 1. Enforce ownership
        if challenge.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Verification challenge does not belong to authenticated user.",
            )

        # 2. Check consumption and status
        if challenge.status == ChallengeStatus.CONSUMED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification challenge has already been consumed.",
            )

        if challenge.status != ChallengeStatus.VERIFIED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Verification challenge is not verified (status: {challenge.status}).",
            )

        # 3. Check expiration
        if ensure_utc(challenge.expires_at) <= now:
            challenge.status = ChallengeStatus.EXPIRED.value
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification challenge has expired.",
            )

        # 4. Check purpose
        if challenge.purpose != ChallengePurpose.HIGH_RISK_TRANSACTION.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid challenge purpose '{challenge.purpose}'.",
            )

        # 5. Check challenge type matches escalation requirement if required
        if required_challenge_type is not None and challenge.challenge_type != required_challenge_type.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Challenge type mismatch: this transaction requires '{required_challenge_type.value}' verification, but received '{challenge.challenge_type}'.",
            )

        # 6. Check transfer parameters binding
        expected_hash = self.compute_transfer_payload_hash(
            user_id=current_user.id,
            recipient_account_number=recipient_account_number,
            amount_paise=amount_paise,
        )
        if challenge.transfer_payload_hash and challenge.transfer_payload_hash != expected_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification challenge was issued for a different recipient or amount (parameter mismatch).",
            )

        # Atomically consume challenge
        challenge.status = ChallengeStatus.CONSUMED.value
        return challenge


# Global verification service instance
verification_service = VerificationService()
otp_provider = verification_service.otp_provider
face_provider = verification_service.face_provider
