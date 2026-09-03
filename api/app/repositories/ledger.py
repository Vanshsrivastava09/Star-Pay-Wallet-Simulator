from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import LedgerEntry

ZERO = Decimal("0.00")


def record_double_entry(
    db: Session,
    *,
    transaction_id: str,
    debit_user_id: int,
    debit_amount: Decimal,
    debit_balance_after: Decimal,
    credit_user_id: int,
    credit_amount: Decimal,
    credit_balance_after: Decimal,
) -> None:
    """Append a balanced debit/credit pair for one successful financial movement."""
    if debit_amount != credit_amount or debit_amount <= ZERO:
        raise ValueError("Double-entry ledger amounts must be equal and positive")
    db.add_all([
        LedgerEntry(
            user_id=debit_user_id,
            transaction_id=transaction_id,
            debit=debit_amount,
            credit=ZERO,
            balance_after=debit_balance_after,
        ),
        LedgerEntry(
            user_id=credit_user_id,
            transaction_id=transaction_id,
            debit=ZERO,
            credit=credit_amount,
            balance_after=credit_balance_after,
        ),
    ])
