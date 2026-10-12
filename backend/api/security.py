"""Security, AI Threat Analyzer, and risk assessment API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Account, User
from backend.schemas import (
    AIThreatAnalysisRequest,
    AIThreatAnalysisResponse,
    RiskAssessmentRequest,
    RiskAssessmentResponse,
)
from backend.security.dependencies import get_current_user
from backend.services.ai_threat_analyzer import ai_threat_analyzer
from backend.services.risk_engine import RiskEvaluationContext, risk_engine

security_router = APIRouter(prefix="/security", tags=["Security & AI Firewall"])


@security_router.post(
    "/assess-risk",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Assess risk for a proposed transaction (Authentication & Ownership Enforced)",
)
def assess_transaction_risk_endpoint(
    assessment_req: RiskAssessmentRequest,
    raw_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskAssessmentResponse:
    """Evaluate multi-signal risk for a proposed transfer without executing it.

    Enforces ownership boundaries: users cannot assess risk on accounts they do not own.
    Users cannot submit arbitrary risk scores or override defensive evaluation rules.
    """
    # 1. Authoritative verification of sender account ownership
    sender_account = (
        db.query(Account)
        .filter(Account.id == assessment_req.sender_account_id)
        .first()
    )
    if not sender_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sender account not found.",
        )

    if sender_account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: sender account does not belong to the authenticated user.",
        )

    # 2. Recipient account resolution
    recipient_account = (
        db.query(Account)
        .filter(Account.account_number == assessment_req.recipient_account_number)
        .first()
    )

    if recipient_account and recipient_account.id == sender_account.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transfer request: sender and recipient accounts cannot be identical.",
        )

    # 3. Construct telemetry context from server-side headers and client input
    client_ip = (
        assessment_req.client_ip
        or (raw_request.client.host if raw_request.client else None)
    )
    user_agent = (
        assessment_req.user_agent
        or raw_request.headers.get("user-agent")
    )

    context = RiskEvaluationContext(
        client_ip=client_ip,
        user_agent=user_agent,
        session_age_seconds=assessment_req.session_age_seconds,
    )

    # 4. Run authoritative risk evaluation including optional AI memo inspection
    assessment = risk_engine.assess_transaction_risk(
        sender_account=sender_account,
        recipient_account=recipient_account,
        amount_paise=assessment_req.amount_paise,
        db=db,
        context=context,
        memo=assessment_req.memo,
    )

    return assessment


@security_router.post(
    "/analyze-text",
    response_model=AIThreatAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze untrusted text for adversarial threats using the AI Threat Analyzer (Auth Required)",
)
def analyze_untrusted_text_endpoint(
    request: AIThreatAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIThreatAnalysisResponse:
    """Analyze untrusted transaction memos or messages for prompt injection, jailbreaks, and coercion.

    Model output is advisory and never directly authorizes transactions or balance mutations.
    """
    return ai_threat_analyzer.analyze_text(
        untrusted_text=request.text,
        context_type=request.context_type or "transaction_memo",
        user=current_user,
        db=db,
    )
