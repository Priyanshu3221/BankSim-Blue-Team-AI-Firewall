"""BankSim Secure Mock-Bank Banking Service.

Orchestrates atomic mock banking transactions with multi-layered defensive security:
1. Authenticated ownership derivation (never trust client-supplied sender ID).
2. Strict recipient validation and distinct-account enforcement.
3. Numeric amount constraints, positive integer paise, and transfer limits.
4. Sufficient balance verification.
5. Integration with Adaptive Risk Engine and AI Threat Analyzer.
6. Fail-closed security enforcement (block or require step-up verification).
7. Atomic balance updates and audit logging using database transactions.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import (
    Account,
    ChallengePurpose,
    ChallengeStatus,
    ChallengeType,
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    Transaction,
    TransactionStatus,
    User,
    VerificationChallenge,
)
from backend.schemas import (
    RiskLevel,
    RiskOutcome,
    TransferRequest,
    TransferResponse,
)
from backend.services.risk_engine import RiskEvaluationContext, risk_engine
from backend.services.verification_service import verification_service

import threading

logger = logging.getLogger("banksim.banking.service")
_transfer_lock = threading.Lock()


def ensure_utc(dt: datetime) -> datetime:
    """Normalize naive or aware datetimes to UTC-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class BankingService:
    """Service executing simulated banking transfers under defensive blue-team rules."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_user_accounts(self, user_id: int, db: Session):
        """Retrieve all active accounts owned by the user."""
        return (
            db.query(Account)
            .filter(Account.user_id == user_id, Account.is_active == True)
            .order_by(Account.id.asc())
            .all()
        )

    def execute_transfer(
        self,
        transfer_request: TransferRequest,
        current_user: User,
        db: Session,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_age_seconds: Optional[int] = None,
    ) -> TransferResponse:
        """Execute a secure simulated funds transfer with adaptive risk and threat gates."""
        with _transfer_lock:
            now = datetime.now(timezone.utc)

            # 1. Derive and validate sender account ownership
            if transfer_request.sender_account_id is not None:
                sender_account = (
                    db.query(Account)
                    .filter(Account.id == transfer_request.sender_account_id)
                    .first()
                )
                if not sender_account:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Sender account not found.",
                    )
                if sender_account.user_id != current_user.id:
                    # Security audit event for ownership boundary violation attempt
                    sec_event = SecurityEvent(
                        user_id=current_user.id,
                        event_type=SecurityEventType.THREAT_DETECTED.value,
                        severity=SecuritySeverity.HIGH.value,
                        description=f"Ownership boundary violation: User attempted transfer from unowned account {transfer_request.sender_account_id}",
                        risk_score=85,
                    )
                    db.add(sec_event)
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Sender account does not belong to the authenticated user.",
                    )
            else:
                # Derive default active account for current user
                sender_account = (
                    db.query(Account)
                    .filter(Account.user_id == current_user.id, Account.is_active == True)
                    .order_by(Account.id.asc())
                    .first()
                )
                if not sender_account:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No active banking account found for authenticated user.",
                    )

            if not sender_account.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sender account is inactive or suspended.",
                )

            # 2. Recipient existence and distinct account check
            recip_number = transfer_request.recipient_account_number.strip()
            recipient_account = (
                db.query(Account)
                .filter(Account.account_number == recip_number)
                .first()
            )
            if not recipient_account:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Recipient account '{recip_number}' does not exist.",
                )

            if not recipient_account.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Recipient account is inactive or suspended.",
                )

            if sender_account.id == recipient_account.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sender and recipient accounts cannot be the same.",
                )

            # 3. Transfer amount validation
            amount = transfer_request.amount_paise
            if not isinstance(amount, int) or amount <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Transfer amount must be a positive integer in paise.",
                )

            max_limit = self.settings.MAX_TRANSFER_AMOUNT_PAISE
            if amount > max_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Transfer amount exceeds maximum single transfer limit of {max_limit} paise.",
                )

            # 4. Sufficient balance pre-check
            if sender_account.balance < amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Insufficient account balance for requested transfer.",
                )

            # 5. Adaptive Risk Assessment & AI Threat Inspection
            context = RiskEvaluationContext(
                client_ip=client_ip,
                user_agent=user_agent,
                session_age_seconds=session_age_seconds,
            )

            assessment = risk_engine.assess_transaction_risk(
                sender_account=sender_account,
                recipient_account=recipient_account,
                amount_paise=amount,
                db=db,
                context=context,
                memo=transfer_request.memo,
            )

            # 6. Defensive Security Enforcement
            ai_signal = next(
                (s for s in assessment.triggered_signals if s.signal_name == "AI_THREAT_ANALYSIS"),
                None,
            )
            ai_recommends_block = (
                ai_signal is not None
                and ai_signal.evidence is not None
                and ai_signal.evidence.get("ai_recommended_action") == "BLOCK"
            )

            # A. Critical or Blocked Risk
            if (
                assessment.recommended_outcome == RiskOutcome.BLOCK
                or assessment.risk_level == RiskLevel.CRITICAL
                or ai_recommends_block
            ):
                sec_event = SecurityEvent(
                    user_id=current_user.id,
                    event_type=SecurityEventType.TRANSACTION_BLOCKED.value,
                    severity=SecuritySeverity.CRITICAL.value,
                    description=f"Transfer of {amount} paise to {recipient_account.account_number} BLOCKED. {assessment.explanation}"[:500],
                    risk_score=assessment.risk_score,
                )
                db.add(sec_event)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "status": "BLOCKED",
                        "message": "Transfer blocked by security policy due to critical risk or detected adversarial threat.",
                        "risk_score": assessment.risk_score,
                        "risk_level": assessment.risk_level.value,
                        "recommended_outcome": assessment.recommended_outcome.value,
                        "explanation": assessment.explanation,
                    },
                )

            # B. Step-Up Verification Required
            if (
                assessment.recommended_outcome in (
                    RiskOutcome.STEP_UP_VERIFICATION,
                    RiskOutcome.RESTRICT,
                )
                or transfer_request.challenge_id is not None
            ):
                # Escalate challenge type based on risk severity
                required_challenge_type = None
                if (
                    assessment.recommended_outcome == RiskOutcome.RESTRICT
                    or assessment.risk_level == RiskLevel.HIGH
                ):
                    required_challenge_type = ChallengeType.FACE_VERIFICATION
                elif assessment.recommended_outcome == RiskOutcome.STEP_UP_VERIFICATION:
                    required_challenge_type = ChallengeType.OTP

                if transfer_request.challenge_id:
                    # Validates challenge is verified, matches transfer parameters and required challenge type,
                    # and marks it as CONSUMED within the pending db transaction.
                    verification_service.validate_and_consume_challenge(
                        challenge_id=transfer_request.challenge_id,
                        current_user=current_user,
                        recipient_account_number=recipient_account.account_number,
                        amount_paise=amount,
                        required_challenge_type=required_challenge_type,
                        db=db,
                    )
                else:
                    challenge_to_issue = required_challenge_type or ChallengeType.OTP
                    # Create pending step-up challenge for the user bound to this transfer
                    new_challenge = verification_service.create_challenge(
                        user_id=current_user.id,
                        challenge_type=challenge_to_issue,
                        purpose=ChallengePurpose.HIGH_RISK_TRANSACTION,
                        recipient_account_number=recipient_account.account_number,
                        amount_paise=amount,
                        db=db,
                    )

                    sec_event = SecurityEvent(
                        user_id=current_user.id,
                        event_type=SecurityEventType.STEP_UP_REQUIRED.value,
                        severity=SecuritySeverity.HIGH.value,
                        description=f"Step-up {required_challenge_type.value} verification required for transfer of {amount} paise to {recipient_account.account_number}. {assessment.explanation}"[:500],
                        risk_score=assessment.risk_score,
                    )
                    db.add(sec_event)
                    db.commit()

                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "status": "STEP_UP_REQUIRED",
                            "message": f"Transfer restricted: {required_challenge_type.value} verification required before funds can be transferred.",
                            "risk_score": assessment.risk_score,
                            "risk_level": assessment.risk_level.value,
                            "recommended_outcome": assessment.recommended_outcome.value,
                            "challenge_id": new_challenge.id,
                            "challenge_type": new_challenge.challenge_type,
                            "explanation": assessment.explanation,
                        },
                    )

            # 7. Atomic SQLite Execution
            try:
                # Re-verify balance inside atomic block
                if sender_account.balance < amount:
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Insufficient account balance for requested transfer.",
                    )

                # Atomic balance updates
                sender_account.balance -= amount
                recipient_account.balance += amount

                # Generate reference and transaction record
                tx_ref = f"TX-{uuid.uuid4().hex[:12].upper()}"
                transaction = Transaction(
                    sender_account_id=sender_account.id,
                    recipient_account_id=recipient_account.id,
                    amount_paise=amount,
                    status=TransactionStatus.COMPLETED.value,
                    memo=transfer_request.memo.strip()[:255] if transfer_request.memo else None,
                    reference=tx_ref,
                )
                db.add(transaction)
                db.commit()
                db.refresh(transaction)
                db.refresh(sender_account)
                db.refresh(recipient_account)

            except HTTPException:
                raise
            except Exception as exc:
                db.rollback()
                logger.error("Atomic transaction execution error: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Transfer execution failed safely during atomic storage update.",
                )

            return TransferResponse(
                success=True,
                status=TransactionStatus.COMPLETED.value,
                message="Transfer completed successfully.",
                reference=transaction.reference,
                transaction_id=transaction.id,
                amount_paise=amount,
                sender_account_number=sender_account.account_number,
                recipient_account_number=recipient_account.account_number,
                remaining_balance_paise=sender_account.balance,
                risk_score=assessment.risk_score,
                risk_level=assessment.risk_level,
                recommended_outcome=assessment.recommended_outcome,
                challenge_id=transfer_request.challenge_id,
                challenge_type=None,
                executed_at=transaction.created_at,
            )

    def verify_challenge(
        self,
        challenge_id: int,
        current_user: User,
        db: Session,
        verification_code: Optional[str] = None,
        face_data: Optional[str] = None,
    ) -> VerificationChallenge:
        """Verify a pending verification challenge for step-up transaction clearance."""
        return verification_service.verify_challenge(
            challenge_id=challenge_id,
            current_user=current_user,
            db=db,
            verification_code=verification_code,
            face_data=face_data,
        )



# Global banking service instance
banking_service = BankingService()
