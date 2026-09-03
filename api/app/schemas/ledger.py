from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class LedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    transaction_id: str
    credit: Decimal
    debit: Decimal
    balance_after: Decimal
    timestamp: datetime
