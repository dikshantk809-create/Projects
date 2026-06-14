"""
Billing engine.

Single responsibility: whenever a DailyEntry is created or changed, the
matching MonthlyBill (customer + year + month) is recomputed from scratch
by summing that month's entries. Recomputing (rather than incrementing)
makes edits and deletes correct for free — no drift.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import DailyEntry, MonthlyBill, PaymentStatus, User


class BillingError(Exception):
    pass


def upsert_entry(
    db: Session,
    *,
    customer_id: int,
    entry_date: date,
    morning_qty: float = 0,
    evening_qty: float = 0,
    rate: float | None = None,
    source: str = "app",
) -> DailyEntry:
    """Create or update the single entry for (customer, date), then reroll
    that month's bill. One entry per customer per day is enforced by a
    unique constraint; sending another message for the same day updates it."""
    customer = db.get(User, customer_id)
    if customer is None:
        raise BillingError(f"customer {customer_id} not found")

    if rate is None:
        rate = customer.default_rate
    if rate is None:
        raise BillingError("no rate supplied and customer has no default rate")

    entry = db.scalar(
        select(DailyEntry).where(
            DailyEntry.customer_id == customer_id,
            DailyEntry.entry_date == entry_date,
        )
    )
    if entry is None:
        entry = DailyEntry(customer_id=customer_id, entry_date=entry_date)
        db.add(entry)

    entry.morning_qty = morning_qty
    entry.evening_qty = evening_qty
    entry.rate = rate
    entry.source = source
    db.flush()

    _reroll_month(db, customer_id, entry_date.year, entry_date.month)
    db.commit()
    db.refresh(entry)
    return entry


def delete_entry(db: Session, entry_id: int) -> None:
    entry = db.get(DailyEntry, entry_id)
    if entry is None:
        return
    cid, y, m = entry.customer_id, entry.entry_date.year, entry.entry_date.month
    db.delete(entry)
    db.flush()
    _reroll_month(db, cid, y, m)
    db.commit()


def _reroll_month(db: Session, customer_id: int, year: int, month: int) -> MonthlyBill:
    entries = db.scalars(
        select(DailyEntry).where(DailyEntry.customer_id == customer_id)
    ).all()
    month_entries = [
        e for e in entries
        if e.entry_date.year == year and e.entry_date.month == month
    ]
    total_qty = round(sum(e.total_qty for e in month_entries), 2)
    total_amount = round(sum(e.total_amount for e in month_entries), 2)

    bill = db.scalar(
        select(MonthlyBill).where(
            MonthlyBill.customer_id == customer_id,
            MonthlyBill.year == year,
            MonthlyBill.month == month,
        )
    )
    if bill is None:
        bill = MonthlyBill(customer_id=customer_id, year=year, month=month)
        db.add(bill)

    bill.total_qty = total_qty
    bill.total_amount = total_amount
    # Don't clobber a paid status on a re-roll unless the bill is now empty.
    if bill.status != PaymentStatus.paid:
        bill.status = PaymentStatus.pending
    db.flush()
    return bill
