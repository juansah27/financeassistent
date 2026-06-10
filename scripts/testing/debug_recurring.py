"""
Debug script untuk melihat semua recurring transactions
"""
from app.db.session import SessionLocal
from app.db.models import RecurringTransaction, TransactionType
from datetime import datetime

db = SessionLocal()

print("=== SEMUA RECURRING TRANSACTIONS (ACTIVE, EXPENSE) ===\n")

bills = db.query(RecurringTransaction).filter(
    RecurringTransaction.is_active == True,
    RecurringTransaction.type == TransactionType.EXPENSE
).order_by(RecurringTransaction.next_due_date).all()

for b in bills:
    print(f"ID: {b.id}")
    print(f"Description: {b.description or b.category}")
    print(f"Amount: Rp {b.amount:,.0f}")
    print(f"Next Due Date: {b.next_due_date}")
    print(f"Type: {b.type}")
    print(f"Is Active: {b.is_active}")
    print("-" * 50)

print(f"\nTotal: {len(bills)} recurring bills")

# Test date comparison
start_date = datetime(2026, 2, 22)
end_date = datetime(2026, 3, 20, 23, 59, 59)

print(f"\n=== FILTERING FOR PERIOD: {start_date.date()} to {end_date.date()} ===\n")

from sqlalchemy import cast, Date

filtered_bills = db.query(RecurringTransaction).filter(
    RecurringTransaction.is_active == True,
    RecurringTransaction.type == TransactionType.EXPENSE,
    cast(RecurringTransaction.next_due_date, Date) >= start_date.date(),
    cast(RecurringTransaction.next_due_date, Date) <= end_date.date()
).all()

for b in filtered_bills:
    print(f"✓ {b.description or b.category}: Rp {b.amount:,.0f} - Due: {b.next_due_date.strftime('%Y-%m-%d')}")

print(f"\nFiltered Total: {len(filtered_bills)} bills")

db.close()
