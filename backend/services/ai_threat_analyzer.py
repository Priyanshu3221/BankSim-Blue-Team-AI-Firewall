"""BankSim AI Threat Analyzer Service.

Analyzes untrusted transaction memos, user comments, and inbound security payloads
for adversarial attacks (prompt injections, jailbreaks, admin impersonation, coercion).
Maintains strict separation: AI recommendations are advisory and never authorize transactions.
"""

from datetime import datetime, timezone
import logging
from typing import Optional
from sqlalchemy.orm import Session

from config import get_settings
from models import SecurityEvent, SecurityEventType, SecuritySeverity, User
from schemas import (
    AIThreatAction,
    AIThreatAnalysisResponse,
    RiskSignalResult,
    ThreatCategory,
)
from services.ai_providers import (
    BaseLLMProvider,
    GeminiProvider,
    MockAIProvider,
    OpenAIProvider,
)

logger = logging.getLogger("banksim.security.ai_threat_analyzer")


class AIThreatAnalyzer:
    """Service orchestrating LLM-based threat detection over untrusted banking text."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None) -> None:
        settings = get_settings()
        if provider is not None:
            self._provider = provider
            return

        provider_name = (settings.AI_PROVIDER or "gemini").strip().lower()

        if provider_name == "gemini":
            self._provider = GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL,
                timeout=settings.GEMINI_TIMEOUT_SECONDS,
            )
        elif provider_name == "openai":
            self._provider = OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                timeout=settings.OPENAI_TIMEOUT_SECONDS,
            )
        elif provider_name == "mock":
            self._provider = MockAIProvider(provider_name="configured-mock-llm")
        else:
            logger.warning(
                "Unrecognized AI_PROVIDER '%s'; defaulting to safe unavailable Gemini provider",
                provider_name,
            )
            self._provider = GeminiProvider(api_key=None)

    @property
    def provider(self) -> BaseLLMProvider:
        """Active LLM provider instance."""
        return self._provider

    def set_provider(self, provider: BaseLLMProvider) -> None:
        """Swap active provider (enables test isolation and provider switching)."""
        self._provider = provider

    def sanitize_input(self, untrusted_text: str) -> str:
        """Strip control characters and truncate to safe inspection bounds.

        Ensures no secrets, passwords, or full credit card / account credentials are sent.
        """
        if not untrusted_text:
            return ""
        # Truncate to maximum 1000 characters
        sanitized = untrusted_text.strip()[:1000]
        # Remove null bytes or non-printable ASCII controls
        sanitized = "".join(ch for ch in sanitized if ch.isprintable() or ch in "\n\r\t")
        return sanitized

    def analyze_text(
        self,
        untrusted_text: str,
        context_type: str = "transaction_memo",
        user: Optional[User] = None,
        db: Optional[Session] = None,
    ) -> AIThreatAnalysisResponse:
        """Analyze untrusted text for adversarial threats using the configured LLM provider.

        Never sends passwords, tokens, or unnecessary personal data to the LLM.
        """
        cleaned_text = self.sanitize_input(untrusted_text)

        if not cleaned_text:
            return AIThreatAnalysisResponse(
                threat_detected=False,
                threat_categories=[ThreatCategory.BENIGN],
                evidence=[],
                confidence=1.0,
                recommended_action=AIThreatAction.ALLOW,
                explanation="Empty text input provided; no threat detected.",
                provider_used=getattr(self._provider, "model", "none"),
                analyzed_at=datetime.now(timezone.utc),
            )

        # Delegate to active provider
        response = self._provider.analyze_threat(cleaned_text, context=context_type)

        # If a critical or blocking threat is detected and a db session is provided, audit it
        if response.threat_detected and db is not None:
            try:
                severity = (
                    SecuritySeverity.CRITICAL.value
                    if response.recommended_action == AIThreatAction.BLOCK
                    else SecuritySeverity.HIGH.value
                )
                sec_event = SecurityEvent(
                    user_id=user.id if user else None,
                    event_type=SecurityEventType.THREAT_DETECTED.value,
                    severity=severity,
                    description=f"AI Threat Detected ({','.join([c.value for c in response.threat_categories])}): {response.explanation}"[:500],
                    risk_score=int(response.confidence * 100),
                )
                db.add(sec_event)
                db.commit()
            except Exception as exc:
                logger.error("Failed to persist security event for AI threat: %s", exc)
                db.rollback()

        return response

    def evaluate_memo_risk_signal(
        self,
        memo: Optional[str],
        user: Optional[User] = None,
        db: Optional[Session] = None,
    ) -> RiskSignalResult:
        """Interface method connecting AI Threat Analyzer output into the Adaptive Risk Engine.

        Translates AI threat findings into a deterministic RiskSignalResult.
        """
        if not memo or not memo.strip():
            return RiskSignalResult(
                signal_name="AI_THREAT_ANALYSIS",
                triggered=False,
                score_impact=0,
                description="No transaction memo provided for AI inspection.",
                status="omitted",
            )

        ai_assessment = self.analyze_text(memo, context_type="transaction_memo", user=user, db=db)

        # Map AI findings to risk score impact
        score_impact = 0
        triggered = False
        desc = ai_assessment.explanation

        if ai_assessment.threat_detected:
            triggered = True
            if ai_assessment.recommended_action == AIThreatAction.BLOCK:
                score_impact = 50  # Significant risk penalty for prompt injections or jailbreaks
            elif ai_assessment.recommended_action == AIThreatAction.STEP_UP_VERIFICATION:
                score_impact = 35  # Step-up verification for coercion or suspicious instructions
            else:
                score_impact = 20
            desc = (
                f"AI Threat Analyzer flagged memo: {','.join([c.value for c in ai_assessment.threat_categories])}. "
                f"{ai_assessment.explanation}"
            )
        elif ai_assessment.threat_categories == [ThreatCategory.UNKNOWN]:
            # Provider unavailable or failed closed
            status_val = "unknown"
            return RiskSignalResult(
                signal_name="AI_THREAT_ANALYSIS",
                triggered=False,
                score_impact=10,  # Minor precautionary score for unverified AI review
                description=f"AI Threat Analyzer review required: {ai_assessment.explanation}",
                status=status_val,
            )

        return RiskSignalResult(
            signal_name="AI_THREAT_ANALYSIS",
            triggered=triggered,
            score_impact=score_impact,
            description=desc,
            evidence={
                "threat_categories": [c.value for c in ai_assessment.threat_categories],
                "confidence": ai_assessment.confidence,
                "ai_recommended_action": ai_assessment.recommended_action.value,
                "evidence": ai_assessment.evidence,
            },
            status="evaluated",
        )


# Global AI threat analyzer instance
ai_threat_analyzer = AIThreatAnalyzer()
