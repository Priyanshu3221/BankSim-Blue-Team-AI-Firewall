"""Banking API router for BankSim secure mock banking operations."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import Account, Transaction, User
from schemas import (
    AccountRead,
    CustomerTransactionItem,
    CustomerTransactionListResponse,
    TransferRequest,
    TransferResponse,
)
from security.dependencies import get_current_user
from services.banking_service import banking_service

banking_router = APIRouter(prefix="/banking", tags=["Banking"])


class VerifyChallengePayload(BaseModel):
    """Payload to complete an issued step-up challenge (OTP or Face Verification)."""

    challenge_id: int
    verification_code: Optional[str] = Field(default=None, max_length=32)
    face_data: Optional[str] = Field(default=None, max_length=10000, description="Simulated face biometric token or data")


class ChallengeVerifiedResponse(BaseModel):
    """Response confirming successful challenge verification."""

    challenge_id: int
    status: str
    message: str


@banking_router.get("/accounts", response_model=List[AccountRead])
def list_my_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all active accounts owned by the authenticated user."""
    return banking_service.get_user_accounts(current_user.id, db)


@banking_router.post(
    "/transfer",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
)
def transfer_funds(
    transfer_request: TransferRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute a secure simulated fund transfer with adaptive risk and threat gates.

    - Authenticated user's account ownership is strictly enforced.
    - Recipient existence and distinctness is verified.
    - Transfer amounts are positive integer paise within limits.
    - Balances and transactions are updated atomically.
    - High-risk transfers are gated behind multi-factor step-up verification.
    - Critical threats and adversarial memos are blocked.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return banking_service.execute_transfer(
        transfer_request=transfer_request,
        current_user=current_user,
        db=db,
        client_ip=client_ip,
        user_agent=user_agent,
    )


@banking_router.post(
    "/verify-challenge",
    response_model=ChallengeVerifiedResponse,
    status_code=status.HTTP_200_OK,
)
def verify_challenge(
    payload: VerifyChallengePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Complete a pending step-up multi-factor challenge (OTP or Face Verification)."""
    challenge = banking_service.verify_challenge(
        challenge_id=payload.challenge_id,
        current_user=current_user,
        db=db,
        verification_code=payload.verification_code,
        face_data=payload.face_data,
    )
    return ChallengeVerifiedResponse(
        challenge_id=challenge.id,
        status=challenge.status,
        message="Verification challenge successfully confirmed. Transfer can now be retried.",
    )


@banking_router.get(
    "/transactions",
    response_model=CustomerTransactionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve authenticated customer's transaction ledger history",
)
def list_transactions(
    account_id: Optional[int] = Query(None, description="Optional account ID filter (must belong to authenticated user)"),
    type: Optional[str] = Query(None, description="Direction filter: 'DEBIT', 'CREDIT', or 'ALL'"),
    status_filter: Optional[str] = Query(None, alias="status", description="Status filter: 'COMPLETED', 'PENDING', 'FAILED'"),
    search: Optional[str] = Query(None, description="Search memo or reference"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CustomerTransactionListResponse:
    """Retrieve customer's simulated transaction ledger.

    Enforces strict account ownership. A user cannot query transactions belonging to other users.
    Supports filtering by account, direction (DEBIT/CREDIT), status, search string, and pagination.
    """
    user_accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    user_account_ids = [acc.id for acc in user_accounts]
    account_map = {acc.id: acc.account_number for acc in user_accounts}

    if not user_account_ids:
        return CustomerTransactionListResponse(total=0, limit=limit, offset=offset, items=[])

    if account_id is not None:
        if account_id not in user_account_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: specified account does not belong to the authenticated user.",
            )
        target_ids = [account_id]
    else:
        target_ids = user_account_ids

    # Build filtered query based on direction
    direction = (type or "ALL").upper()
    if direction == "DEBIT":
        query = db.query(Transaction).filter(Transaction.sender_account_id.in_(target_ids))
    elif direction == "CREDIT":
        query = db.query(Transaction).filter(Transaction.recipient_account_id.in_(target_ids))
    else:
        query = db.query(Transaction).filter(
            or_(
                Transaction.sender_account_id.in_(target_ids),
                Transaction.recipient_account_id.in_(target_ids),
            )
        )

    # Status filter
    if status_filter:
        query = query.filter(Transaction.status == status_filter.upper())

    # Search filter
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Transaction.reference.ilike(search_pattern),
                Transaction.memo.ilike(search_pattern),
            )
        )

    total = query.count()

    tx_records = (
        query.order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Resolve counterparty account numbers
    all_ref_ids = set()
    for tx in tx_records:
        if tx.sender_account_id:
            all_ref_ids.add(tx.sender_account_id)
        if tx.recipient_account_id:
            all_ref_ids.add(tx.recipient_account_id)

    missing_ids = all_ref_ids - set(account_map.keys())
    if missing_ids:
        extra_accounts = db.query(Account.id, Account.account_number).filter(Account.id.in_(missing_ids)).all()
        for aid, anum in extra_accounts:
            account_map[aid] = anum

    items = []
    for tx in tx_records:
        is_sender = tx.sender_account_id in target_ids
        tx_dir = "DEBIT" if is_sender else "CREDIT"
        sender_acc_num = account_map.get(tx.sender_account_id) if tx.sender_account_id else None
        recip_acc_num = account_map.get(tx.recipient_account_id) if tx.recipient_account_id else None

        if tx_dir == "DEBIT":
            counterparty = recip_acc_num or "External Transfer"
            desc = tx.memo or f"Transfer to {counterparty}"
        else:
            counterparty = sender_acc_num or "Initial Deposit / Treasury"
            desc = tx.memo or f"Credit from {counterparty}"

        items.append(
            CustomerTransactionItem(
                id=tx.id,
                reference=tx.reference,
                transaction_reference=tx.reference,
                direction=tx_dir,
                amount_paise=tx.amount_paise,
                amount_inr=round(tx.amount_paise / 100.0, 2),
                status=tx.status,
                description=desc,
                memo=tx.memo,
                counterparty_account=counterparty,
                created_at=tx.created_at,
                sender_account_number=sender_acc_num,
                recipient_account_number=recip_acc_num,
            )
        )

    return CustomerTransactionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )

