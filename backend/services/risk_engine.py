"""BankSim Adaptive Rules-Based Risk Engine.

Evaluates multi-factor banking signals deterministically:
1. Repeated failed login attempts.
2. Unusual transaction amounts (historical variance and high-value thresholds).
3. Transaction velocity (frequency within time window).
4. Recipient novelty (first-time transfer destination).
5. Suspicious request bursts.
6. Session and authentication anomalies.

Produces structured risk assessments with transparent explanations and recommended outcomes.
Assessment is decoupled from enforcement: this engine does NOT execute or approve transactions.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import get_settings
from models import (
    Account,
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    Transaction,
    User,
)
from schemas import (
    RiskAssessmentResponse,
    RiskLevel,
    RiskOutcome,
    RiskSignalResult,
)
from security.login_tracker import login_tracker

logger = logging.getLogger("banksim.security.risk_engine")


@dataclass
class RiskEvaluationContext:
    """Optional contextual telemetry for risk assessment."""

    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_age_seconds: Optional[int] = None
    recent_burst_count: Optional[int] = None


class AdaptiveRiskEngine:
    """Deterministic, rules-based risk assessment engine."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def evaluate_failed_logins(self, user: User, db: Session) -> RiskSignalResult:
        """Signal 1: Evaluate recent failed login attempts and lockout state."""
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24)

        # Count login failures in audit log over last 24 hours
        failure_count = (
            db.query(func.count(SecurityEvent.id))
            .filter(
                SecurityEvent.user_id == user.id,
                SecurityEvent.event_type == SecurityEventType.LOGIN_FAILURE.value,
                SecurityEvent.created_at >= since,
            )
            .scalar()
            or 0
        )

        is_locked = login_tracker.is_locked(user.username)

        score = 0
        triggered = False
        desc = "No recent failed logins detected."

        if is_locked:
            score = 35
            triggered = True
            desc = f"Account '{user.username}' is currently locked due to repeated authentication failures."
        elif failure_count >= 4:
            score = 25
            triggered = True
            desc = f"High number of failed login attempts ({failure_count}) in the past 24 hours."
        elif failure_count >= 1:
            score = 10
            triggered = True
            desc = f"Recent failed login attempt ({failure_count}) recorded in the past 24 hours."

        return RiskSignalResult(
            signal_name="FAILED_LOGIN_ANOMALY",
            triggered=triggered,
            score_impact=score,
            description=desc,
            evidence={
                "failed_login_count_24h": failure_count,
                "is_locked": is_locked,
            },
            status="evaluated",
        )

    def evaluate_amount_anomaly(
        self,
        sender_account: Account,
        amount_paise: int,
        db: Session,
    ) -> RiskSignalResult:
        """Signal 2: Evaluate transaction amount against account history and high-value threshold."""
        # Query completed past transactions for baseline
        past_txs = (
            db.query(Transaction.amount_paise)
            .filter(
                Transaction.sender_account_id == sender_account.id,
                Transaction.status == "COMPLETED",
            )
            .all()
        )

        high_threshold = self.settings.RISK_HIGH_AMOUNT_THRESHOLD_PAISE
        tx_count = len(past_txs)

        score = 0
        triggered = False
        desc = "Transaction amount is within normal historical ranges."

        if tx_count > 0:
            amounts = [t[0] for t in past_txs]
            avg_amount = sum(amounts) / tx_count
            max_amount = max(amounts)

            if amount_paise > (3 * avg_amount) and amount_paise >= high_threshold:
                score = 35
                triggered = True
                desc = (
                    f"Extreme amount anomaly: {amount_paise} paise exceeds 3x historical average "
                    f"({int(avg_amount)} paise) and high-value threshold ({high_threshold} paise)."
                )
            elif amount_paise > (2 * avg_amount) or amount_paise >= high_threshold:
                score = 20
                triggered = True
                desc = (
                    f"Elevated amount: {amount_paise} paise exceeds 2x historical average "
                    f"or high-value threshold ({high_threshold} paise)."
                )
        else:
            # New account with no history
            if amount_paise >= high_threshold:
                score = 25
                triggered = True
                desc = (
                    f"High-value transfer ({amount_paise} paise) on an account with no previous transaction history."
                )

        return RiskSignalResult(
            signal_name="UNUSUAL_TRANSACTION_AMOUNT",
            triggered=triggered,
            score_impact=score,
            description=desc,
            evidence={
                "proposed_amount_paise": amount_paise,
                "historical_tx_count": tx_count,
                "high_threshold_paise": high_threshold,
            },
            status="evaluated",
        )

    def evaluate_velocity(
        self,
        sender_account: Account,
        db: Session,
    ) -> RiskSignalResult:
        """Signal 3: Evaluate transaction frequency within the velocity time window."""
        window_minutes = self.settings.RISK_VELOCITY_WINDOW_MINUTES
        threshold = self.settings.RISK_VELOCITY_TX_COUNT_THRESHOLD
        now = datetime.now(timezone.utc)
        since = now - timedelta(minutes=window_minutes)

        recent_count = (
            db.query(func.count(Transaction.id))
            .filter(
                Transaction.sender_account_id == sender_account.id,
                Transaction.created_at >= since,
            )
            .scalar()
            or 0
        )

        score = 0
        triggered = False
        desc = f"Transaction velocity is normal ({recent_count} transfers in last {window_minutes}m)."

        if recent_count >= (threshold * 2):
            score = 30
            triggered = True
            desc = (
                f"Critical transaction velocity: {recent_count} transfers attempted "
                f"in the last {window_minutes} minutes (threshold: {threshold})."
            )
        elif recent_count >= threshold:
            score = 20
            triggered = True
            desc = (
                f"Elevated transaction velocity: {recent_count} transfers attempted "
                f"in the last {window_minutes} minutes."
            )

        return RiskSignalResult(
            signal_name="TRANSACTION_VELOCITY",
            triggered=triggered,
            score_impact=score,
            description=desc,
            evidence={
                "recent_count": recent_count,
                "window_minutes": window_minutes,
                "threshold": threshold,
            },
            status="evaluated",
        )

    def evaluate_recipient_novelty(
        self,
        sender_account: Account,
        recipient_account: Optional[Account],
        db: Session,
    ) -> RiskSignalResult:
        """Signal 4: Evaluate whether the recipient has been previously transacted with."""
        if recipient_account is None:
            return RiskSignalResult(
                signal_name="RECIPIENT_NOVELTY",
                triggered=False,
                score_impact=0,
                description="Recipient account not identifiable in system records.",
                status="unknown",
            )

        # Check if recipient has ever received a completed transfer from sender
        prior_transfers = (
            db.query(func.count(Transaction.id))
            .filter(
                Transaction.sender_account_id == sender_account.id,
                Transaction.recipient_account_id == recipient_account.id,
                Transaction.status == "COMPLETED",
            )
            .scalar()
            or 0
        )

        if prior_transfers == 0:
            return RiskSignalResult(
                signal_name="RECIPIENT_NOVELTY",
                triggered=True,
                score_impact=15,
                description=f"First-time transfer to recipient account '{recipient_account.account_number}'.",
                evidence={
                    "recipient_account_number": recipient_account.account_number,
                    "prior_successful_transfers": 0,
                },
                status="evaluated",
            )

        return RiskSignalResult(
            signal_name="RECIPIENT_NOVELTY",
            triggered=False,
            score_impact=0,
            description=f"Established recipient: {prior_transfers} previous completed transfers.",
            evidence={
                "recipient_account_number": recipient_account.account_number,
                "prior_successful_transfers": prior_transfers,
            },
            status="evaluated",
        )

    def evaluate_request_burst(
        self,
        context: Optional[RiskEvaluationContext],
    ) -> RiskSignalResult:
        """Signal 5: Evaluate rapid bursts of requests in a short time frame."""
        if context is None or context.recent_burst_count is None:
            return RiskSignalResult(
                signal_name="REQUEST_BURST_ANOMALY",
                triggered=False,
                score_impact=0,
                description="Burst telemetry not available.",
                status="omitted",
            )

        threshold = self.settings.RISK_BURST_REQUEST_COUNT_THRESHOLD
        burst = context.recent_burst_count
        triggered = burst >= threshold
        score = 25 if triggered else 0

        desc = (
            f"Suspicious request burst detected ({burst} calls in window, threshold {threshold})."
            if triggered
            else f"Request burst level normal ({burst} calls)."
        )

        return RiskSignalResult(
            signal_name="REQUEST_BURST_ANOMALY",
            triggered=triggered,
            score_impact=score,
            description=desc,
            evidence={
                "burst_count": burst,
                "burst_threshold": threshold,
            },
            status="evaluated",
        )

    def evaluate_session_anomaly(
        self,
        context: Optional[RiskEvaluationContext],
    ) -> RiskSignalResult:
        """Signal 6: Evaluate session freshness and authentication anomalies."""
        if context is None:
            return RiskSignalResult(
                signal_name="SESSION_ANOMALY",
                triggered=False,
                score_impact=0,
                description="Session telemetry not provided.",
                status="omitted",
            )

        score = 0
        triggered = False
        reasons = []

        # Check if session is suspiciously brand new (< 15 seconds) attempting immediate transfer
        if context.session_age_seconds is not None and context.session_age_seconds < 15:
            score += 15
            triggered = True
            reasons.append(
                f"Immediate transfer attempt {context.session_age_seconds}s after session establishment."
            )

        # Check for missing client network telemetry
        if not context.client_ip:
            score += 10
            triggered = True
            reasons.append("Unidentified client IP address.")

        desc = (
            "; ".join(reasons)
            if triggered
            else "Session telemetry shows no anomalies."
        )

        return RiskSignalResult(
            signal_name="SESSION_ANOMALY",
            triggered=triggered,
            score_impact=score,
            description=desc,
            evidence={
                "session_age_seconds": context.session_age_seconds,
                "client_ip_present": bool(context.client_ip),
            },
            status="evaluated",
        )

    def evaluate_ai_threat(
        self,
        memo: Optional[str],
        user: Optional[User],
        db: Session,
    ) -> RiskSignalResult:
        """Signal 7: Evaluate transaction memo using the AI Threat Analyzer service."""
        from services.ai_threat_analyzer import ai_threat_analyzer

        return ai_threat_analyzer.evaluate_memo_risk_signal(memo, user=user, db=db)

    def assess_transaction_risk(
        self,
        sender_account: Account,
        recipient_account: Optional[Account],
        amount_paise: int,
        db: Session,
        context: Optional[RiskEvaluationContext] = None,
        memo: Optional[str] = None,
    ) -> RiskAssessmentResponse:
        """Run all risk signal evaluations and synthesize an authoritative risk assessment."""
        user = sender_account.user

        # Evaluate all signals (signals 1-6 rules-based + signal 7 AI Threat Analysis)
        sig1 = self.evaluate_failed_logins(user, db)
        sig2 = self.evaluate_amount_anomaly(sender_account, amount_paise, db)
        sig3 = self.evaluate_velocity(sender_account, db)
        sig4 = self.evaluate_recipient_novelty(sender_account, recipient_account, db)
        sig5 = self.evaluate_request_burst(context)
        sig6 = self.evaluate_session_anomaly(context)
        sig7 = self.evaluate_ai_threat(memo, user, db)

        all_signals = [sig1, sig2, sig3, sig4, sig5, sig6, sig7]
        triggered_signals = [s for s in all_signals if s.triggered]

        # Calculate capped score
        raw_score = sum(s.score_impact for s in triggered_signals)
        risk_score = min(100, max(0, raw_score))

        # Map to risk level and recommended outcome
        allow_limit = self.settings.RISK_THRESHOLD_ALLOW
        step_up_limit = self.settings.RISK_THRESHOLD_STEP_UP
        restrict_limit = self.settings.RISK_THRESHOLD_RESTRICT

        if risk_score <= allow_limit:
            risk_level = RiskLevel.LOW
            recommended_outcome = RiskOutcome.ALLOW
        elif risk_score <= step_up_limit:
            risk_level = RiskLevel.MEDIUM
            recommended_outcome = RiskOutcome.STEP_UP_VERIFICATION
        elif risk_score <= restrict_limit:
            risk_level = RiskLevel.HIGH
            recommended_outcome = RiskOutcome.RESTRICT
        else:
            risk_level = RiskLevel.CRITICAL
            recommended_outcome = RiskOutcome.BLOCK

        # Generate human-readable explanation
        if not triggered_signals:
            explanation = "Transaction activity conforms to normal operational patterns with no risk signals triggered."
        else:
            signal_summaries = [s.description for s in triggered_signals]
            explanation = (
                f"{risk_level.value} Risk (Score: {risk_score}/100, Outcome: {recommended_outcome.value}): "
                + " | ".join(signal_summaries)
            )

        assessment = RiskAssessmentResponse(
            risk_score=risk_score,
            risk_level=risk_level,
            recommended_outcome=recommended_outcome,
            triggered_signals=triggered_signals,
            all_signals=all_signals,
            explanation=explanation,
            evaluated_at=datetime.now(timezone.utc),
        )

        # Audit high-risk recommendations as security events
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            try:
                sec_event = SecurityEvent(
                    user_id=user.id,
                    event_type=SecurityEventType.THREAT_DETECTED.value,
                    severity=(
                        SecuritySeverity.CRITICAL.value
                        if risk_level == RiskLevel.CRITICAL
                        else SecuritySeverity.HIGH.value
                    ),
                    description=explanation[:500],
                    risk_score=risk_score,
                )
                db.add(sec_event)
                db.commit()
            except Exception as exc:
                logger.error("Failed to persist high-risk security event: %s", exc)
                db.rollback()

        return assessment


# Global risk engine instance
risk_engine = AdaptiveRiskEngine()
