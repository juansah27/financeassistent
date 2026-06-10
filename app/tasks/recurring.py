"""
Background task to process recurring transactions
Run this periodically (e.g., daily) to create transactions from recurring items

Logic:
- INCOME type: auto-create transaction when due (salary, etc.)
- Non-INCOME type: NEVER auto-create. Send hourly alerts until user pays via WhatsApp.
  User must manually pay via WA to create transaction.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.db import session, crud_extended, models, crud
from app.db.models import RecurrenceType, TransactionType

def process_recurring_transactions(db: Session):
    """Process all due recurring transactions.
    
    Returns: (created_count, pending_list)
    - created_count: number of auto-created transactions (INCOME only)
    - pending_list: list of non-INCOME recurring that are due/past due for alerting
    """
    now = datetime.now(timezone.utc)
    
    # Get all active recurring transactions
    recurring_list = crud_extended.get_recurring_transactions(db, user_id=None, active_only=True)
    
    created_count = 0
    pending_list = []
    
    for recurring in recurring_list:
        # Ensure both datetimes are timezone-aware
        next_due = recurring.next_due_date
        if next_due.tzinfo is None:
            next_due = next_due.replace(tzinfo=timezone.utc)
        
        # Check if due (past or on due date)
        if next_due <= now:
            is_income = recurring.type == TransactionType.INCOME
            
            if is_income:
                # INCOME: auto-create transaction (gaji, pemasukan rutin)
                crud.create_transaction(
                    db=db,
                    user_id=recurring.user_id,
                    transaction_type=recurring.type,
                    amount=recurring.amount,
                    category=recurring.category,
                    description=recurring.description or f"Auto: {recurring.description}",
                    raw_input=None,
                    recurring_id=recurring.id,
                    tags=None
                )
                
                # Calculate next due date
                next_due = calculate_next_due_date(
                    recurring.next_due_date, 
                    recurring.recurrence_type, 
                    recurring.day_of_month,
                    recurring.interval_days
                )
                crud_extended.update_recurring_next_due(db, recurring.id, next_due)
                
                # Handle remaining occurrences (stop if limited)
                if recurring.remaining_occurrences is not None:
                    recurring.remaining_occurrences -= 1
                    if recurring.remaining_occurrences <= 0:
                        recurring.is_active = False
                    db.commit()
                
                created_count += 1
            else:
                # Non-INCOME: NEVER auto-create
                # Add to pending list for hourly alerting via WhatsApp
                # User must manually pay via WA to create transaction
                days_overdue = (now - next_due).days
                pending_list.append({
                    "recurring": recurring,
                    "next_due": next_due,
                    "days_overdue": days_overdue,
                    "user_id": recurring.user_id
                })
    
    return created_count, pending_list


def get_pending_recurring_for_alerts(db: Session):
    """Get all due/overdue non-INCOME recurring transactions for hourly alerting.
    
    Returns list of pending items with user info.
    These are recurring that need user to pay via WhatsApp.
    """
    now = datetime.now(timezone.utc)
    recurring_list = crud_extended.get_recurring_transactions(db, user_id=None, active_only=True)
    
    pending_list = []
    
    for recurring in recurring_list:
        # Skip INCOME type - those are auto-created
        if recurring.type == TransactionType.INCOME:
            continue
            
        next_due = recurring.next_due_date
        if next_due.tzinfo is None:
            next_due = next_due.replace(tzinfo=timezone.utc)
        
        # Check if due or overdue (past or on due date)
        if next_due <= now:
            days_overdue = (now - next_due).days
            pending_list.append({
                "recurring": recurring,
                "next_due": next_due,
                "days_overdue": days_overdue,
                "user_id": recurring.user_id
            })
    
    return pending_list

from dateutil.relativedelta import relativedelta

def calculate_next_due_date(current_date: datetime, recurrence_type: RecurrenceType, day_of_month: int = None, interval_days: int = None) -> datetime:
    """Calculate next due date based on recurrence type"""
    if recurrence_type == RecurrenceType.DAILY:
        return current_date + timedelta(days=1)
    elif recurrence_type == RecurrenceType.WEEKLY:
        return current_date + timedelta(weeks=1)
    elif recurrence_type == RecurrenceType.MONTHLY:
        # Move to next month, preserving day of month automatically
        return current_date + relativedelta(months=1)
    elif recurrence_type == RecurrenceType.YEARLY:
        return current_date + relativedelta(years=1)
    elif recurrence_type == RecurrenceType.CUSTOM:
        # Every X days
        interval = interval_days if interval_days and interval_days > 0 else 1
        return current_date + timedelta(days=interval)
    return current_date

