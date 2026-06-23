from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.security import verify_password
from app.dependencies import CurrentUser, DbSession
from app.models import LedgerEntry, Transaction, TransactionStatus, TransactionType, User
from app.schemas.ledger import LedgerEntryResponse
from app.schemas.wallet import AddMoneyRequest, TransactionResponse, TransferRequest, TransferResponse, WalletResponse
from app.services.ledger import record_double_entry

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get("", response_model=WalletResponse)
def get_wallet(current_user: CurrentUser):
    return current_user.wallet


@router.post("/add-money", response_model=WalletResponse)
def add_money(payload: AddMoneyRequest, current_user: CurrentUser, db: DbSession):
    wallet = current_user.wallet
    balance_before = wallet.balance
    transaction_id = uuid4().hex
    wallet.balance += payload.amount
    db.add(Transaction(
        wallet=wallet,
        transaction_id=transaction_id,
        transaction_type=TransactionType.DEPOSIT,
        status=TransactionStatus.SUCCESS,
        amount=payload.amount,
        balance_after=wallet.balance,
        description=payload.description,
    ))
    # An external top-up is represented by matching source and wallet entries.
    record_double_entry(
        db,
        transaction_id=transaction_id,
        debit_user_id=current_user.id,
        debit_amount=payload.amount,
        debit_balance_after=balance_before,
        credit_user_id=current_user.id,
        credit_amount=payload.amount,
        credit_balance_after=wallet.balance,
    )
    db.commit()
    db.refresh(wallet)
    return wallet


@router.post("/transfer", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def transfer(payload: TransferRequest, current_user: CurrentUser, db: DbSession):
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password confirmation is incorrect")

    recipient = db.scalar(select(User).where(User.email == payload.recipient_email))
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient was not found")
    if recipient.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot transfer money to yourself")

    # SQLite serializes writes; both balance updates and ledger rows are committed together.
    sender_wallet = current_user.wallet
    recipient_wallet = recipient.wallet
    amount: Decimal = payload.amount
    transaction_id = uuid4().hex
    if sender_wallet.balance < amount:
        db.add(Transaction(
            wallet=sender_wallet,
            transaction_id=transaction_id,
            transaction_type=TransactionType.TRANSFER_OUT,
            status=TransactionStatus.FAILED,
            amount=amount,
            balance_after=sender_wallet.balance,
            reference=transaction_id,
            counterparty_email=recipient.email,
            description=payload.description or "Transfer failed: insufficient balance",
        ))
        db.commit()
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")

    # Start both ledger entries as pending, then settle them together in one commit.
    reference = transaction_id
    sender_transaction = Transaction(
        wallet=sender_wallet,
        transaction_id=transaction_id,
        transaction_type=TransactionType.TRANSFER_OUT,
        status=TransactionStatus.PENDING,
        amount=amount,
        balance_after=sender_wallet.balance - amount,
        reference=reference,
        counterparty_email=recipient.email,
        description=payload.description,
    )
    recipient_transaction = Transaction(
        wallet=recipient_wallet,
        transaction_id=transaction_id,
        transaction_type=TransactionType.TRANSFER_IN,
        status=TransactionStatus.PENDING,
        amount=amount,
        balance_after=recipient_wallet.balance + amount,
        reference=reference,
        counterparty_email=current_user.email,
        description=payload.description,
    )
    sender_wallet.balance -= amount
    recipient_wallet.balance += amount
    db.add_all([sender_transaction, recipient_transaction])
    db.flush()
    sender_transaction.status = TransactionStatus.SUCCESS
    recipient_transaction.status = TransactionStatus.SUCCESS
    record_double_entry(
        db,
        transaction_id=transaction_id,
        debit_user_id=current_user.id,
        debit_amount=amount,
        debit_balance_after=sender_wallet.balance,
        credit_user_id=recipient.id,
        credit_amount=amount,
        credit_balance_after=recipient_wallet.balance,
    )
    db.commit()
    db.refresh(sender_wallet)
    return TransferResponse(transaction_id=transaction_id, status=TransactionStatus.SUCCESS, reference=reference,
                            sender_balance=sender_wallet.balance, recipient_email=recipient.email, amount=amount)


@router.get("/transactions", response_model=list[TransactionResponse])
def transaction_history(current_user: CurrentUser, db: DbSession, limit: int = 50, offset: int = 0):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(status_code=422, detail="limit must be 1-100 and offset must be non-negative")
    statement = (select(Transaction).where(Transaction.wallet_id == current_user.wallet.id)
                 .order_by(Transaction.created_at.desc()).offset(offset).limit(limit))
    return list(db.scalars(statement))


@router.get("/ledger", response_model=list[LedgerEntryResponse])
def ledger_history(current_user: CurrentUser, db: DbSession, limit: int = 50, offset: int = 0):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(status_code=422, detail="limit must be 1-100 and offset must be non-negative")
    statement = (select(LedgerEntry).where(LedgerEntry.user_id == current_user.id)
                 .order_by(LedgerEntry.timestamp.desc()).offset(offset).limit(limit))
    return list(db.scalars(statement))
