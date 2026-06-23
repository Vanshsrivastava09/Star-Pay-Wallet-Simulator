from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.security import verify_password
from app.dependencies import CurrentUser, DbSession
from app.models import (
    Merchant,
    MerchantPayment,
    MerchantPaymentStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
    utc_now,
)
from app.schemas.merchant import (
    CreateMerchantRequest,
    MerchantPaymentRequest,
    MerchantPaymentResponse,
    MerchantResponse,
    RefundRequest,
)
from app.services.ledger import record_double_entry

router = APIRouter(prefix="/merchants", tags=["Merchants"])
payments_router = APIRouter(prefix="/merchant-payments", tags=["Merchant payments"])


@router.post("", response_model=MerchantResponse, status_code=status.HTTP_201_CREATED)
def create_merchant(payload: CreateMerchantRequest, current_user: CurrentUser, db: DbSession):
    if db.scalar(select(Merchant).where(Merchant.email == payload.email)):
        raise HTTPException(status_code=409, detail="A merchant with this email already exists")
    merchant = Merchant(owner_user_id=current_user.id, name=payload.name, email=str(payload.email))
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant


@router.get("", response_model=list[MerchantResponse])
def list_merchants(db: DbSession):
    return list(db.scalars(select(Merchant).where(Merchant.is_active.is_(True)).order_by(Merchant.name)))


@router.post("/{merchant_id}/pay", response_model=MerchantPaymentResponse, status_code=status.HTTP_201_CREATED)
def pay_merchant(merchant_id: str, payload: MerchantPaymentRequest, current_user: CurrentUser, db: DbSession):
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password confirmation is incorrect")
    merchant = db.get(Merchant, merchant_id)
    if not merchant or not merchant.is_active:
        raise HTTPException(status_code=404, detail="Merchant was not found or is inactive")

    wallet = current_user.wallet
    payment = MerchantPayment(
        merchant_id=merchant.id,
        payer_user_id=current_user.id,
        amount=payload.amount,
        status=MerchantPaymentStatus.PENDING,
        description=payload.description,
    )
    db.add(payment)
    db.flush()
    if wallet.balance < payload.amount:
        payment.status = MerchantPaymentStatus.FAILED
        db.commit()
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")

    wallet.balance -= payload.amount
    merchant.balance += payload.amount
    db.add(Transaction(
        wallet=wallet,
        transaction_id=payment.id,
        transaction_type=TransactionType.MERCHANT_PAYMENT,
        status=TransactionStatus.SUCCESS,
        amount=payload.amount,
        balance_after=wallet.balance,
        reference=payment.id,
        counterparty_email=merchant.email,
        description=payload.description or f"Payment to {merchant.name}",
    ))
    payment.status = MerchantPaymentStatus.SUCCESS
    record_double_entry(
        db,
        transaction_id=payment.id,
        debit_user_id=current_user.id,
        debit_amount=payload.amount,
        debit_balance_after=wallet.balance,
        credit_user_id=merchant.owner_user_id,
        credit_amount=payload.amount,
        credit_balance_after=merchant.balance,
    )
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/{merchant_id}/payments", response_model=list[MerchantPaymentResponse])
def merchant_payment_history(merchant_id: str, current_user: CurrentUser, db: DbSession):
    merchant = db.get(Merchant, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant was not found")
    if merchant.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the merchant owner can view this payment history")
    statement = select(MerchantPayment).where(MerchantPayment.merchant_id == merchant_id).order_by(MerchantPayment.created_at.desc())
    return list(db.scalars(statement))


@payments_router.get("", response_model=list[MerchantPaymentResponse])
def my_merchant_payments(current_user: CurrentUser, db: DbSession):
    statement = select(MerchantPayment).where(MerchantPayment.payer_user_id == current_user.id).order_by(MerchantPayment.created_at.desc())
    return list(db.scalars(statement))


@payments_router.post("/{payment_id}/refund", response_model=MerchantPaymentResponse)
def refund_merchant_payment(payment_id: str, payload: RefundRequest, current_user: CurrentUser, db: DbSession):
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password confirmation is incorrect")
    payment = db.get(MerchantPayment, payment_id)
    if not payment or payment.payer_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Merchant payment was not found")
    if payment.status != MerchantPaymentStatus.SUCCESS:
        raise HTTPException(status_code=400, detail="Only successful merchant payments can be refunded")

    refund_transaction_id = uuid4().hex
    wallet = current_user.wallet
    merchant = payment.merchant
    if merchant.balance < payment.amount:
        raise HTTPException(status_code=400, detail="Merchant does not have sufficient settled balance for this refund")
    wallet.balance += payment.amount
    merchant.balance -= payment.amount
    payment.status = MerchantPaymentStatus.REFUNDED
    payment.refunded_at = utc_now()
    payment.refund_transaction_id = refund_transaction_id
    db.add(Transaction(
        wallet=wallet,
        transaction_id=refund_transaction_id,
        transaction_type=TransactionType.MERCHANT_REFUND,
        status=TransactionStatus.SUCCESS,
        amount=payment.amount,
        balance_after=wallet.balance,
        reference=payment.id,
        counterparty_email=payment.merchant.email,
        description=f"Refund for merchant payment {payment.id}",
    ))
    record_double_entry(
        db,
        transaction_id=refund_transaction_id,
        debit_user_id=merchant.owner_user_id,
        debit_amount=payment.amount,
        debit_balance_after=merchant.balance,
        credit_user_id=current_user.id,
        credit_amount=payment.amount,
        credit_balance_after=wallet.balance,
    )
    db.commit()
    db.refresh(payment)
    return payment
