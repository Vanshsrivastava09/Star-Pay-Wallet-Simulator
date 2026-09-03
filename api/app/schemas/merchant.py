from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import MerchantPaymentStatus


class CreateMerchantRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr


class MerchantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    is_active: bool
    created_at: datetime


class MerchantPaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    password: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=255)


class RefundRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class MerchantPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    merchant_id: str
    payer_user_id: int
    amount: Decimal
    status: MerchantPaymentStatus
    description: str | None
    created_at: datetime
    refunded_at: datetime | None
    refund_transaction_id: str | None
