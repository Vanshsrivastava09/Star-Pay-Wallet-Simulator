from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import TransactionStatus, TransactionType


class WalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    balance: Decimal
    updated_at: datetime


class AddMoneyRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default="Wallet top-up", max_length=255)


class TransferRequest(BaseModel):
    recipient_email: str
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    password: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=255)


class TransferResponse(BaseModel):
    transaction_id: str
    status: TransactionStatus
    reference: str
    sender_balance: Decimal
    recipient_email: str
    amount: Decimal


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_type: TransactionType
    transaction_id: str | None
    status: TransactionStatus
    amount: Decimal
    balance_after: Decimal
    reference: str | None
    counterparty_email: str | None
    description: str | None
    created_at: datetime
