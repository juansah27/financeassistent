from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_, String, cast
from datetime import datetime, timedelta
from typing import Optional, List
from app.db.models import (
    User, Transaction, TransactionType, Budget, 
    RecurringTransaction, RecurrenceType, Goal, TransactionPhoto, Notification
)
from app.db import crud

# ========== BUDGET CRUD ==========
def create_budget(db: Session, user_id: int, category: str, amount: float, year: int, month: int, percentage: float = None):
    # Check if budget exists for this month/category
    existing = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.category == category,
        Budget.year == year,
        Budget.month == month
    ).first()
    
    if existing:
        existing.amount = amount
        existing.percentage = percentage
        db.commit()
        db.refresh(existing)
        return existing
    
    budget = Budget(
        user_id=user_id,
        category=category,
        amount=amount,
        percentage=percentage,
        year=year,
        month=month
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget

def get_budgets(db: Session, user_id: int, year: int = None, month: int = None):
    query = db.query(Budget).filter(Budget.user_id == user_id)
    
    if year:
        query = query.filter(Budget.year == year)
    if month:
        query = query.filter(Budget.month == month)
    
    return query.order_by(Budget.month.desc(), Budget.year.desc()).all()

def get_budget_by_category(db: Session, user_id: int, category: str, year: int, month: int):
    return db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.category == category,
        Budget.year == year,
        Budget.month == month
    ).first()

def delete_budget(db: Session, budget_id: int, user_id: int):
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user_id).first()
    if budget:
        db.delete(budget)
        db.commit()
        return True
    return False

# ========== RECURRING TRANSACTIONS CRUD ==========
def create_recurring_transaction(
    db: Session, user_id: int, transaction_type: TransactionType,
    amount: float, category: str, description: str,
    recurrence_type: RecurrenceType, day_of_month: int = None, next_due_date: datetime = None,
    total_occurrences: int = None, interval_days: int = None,
    account_id: int = None
):
    if next_due_date is None:
        next_due_date = datetime.now()
    
    recurring = RecurringTransaction(
        user_id=user_id,
        type=transaction_type,
        amount=amount,
        category=category,
        description=description,
        recurrence_type=recurrence_type,
        day_of_month=day_of_month,
        interval_days=interval_days,
        next_due_date=next_due_date,
        remaining_occurrences=total_occurrences,
        is_active=True,
        account_id=account_id
    )
    db.add(recurring)
    db.commit()
    db.refresh(recurring)
    return recurring

def get_recurring_transactions(
    db: Session, 
    user_id: int = None, 
    active_only: bool = True,
    search_term: str = None,
    category: str = None
):
    query = db.query(RecurringTransaction)
    if user_id:
        query = query.filter(RecurringTransaction.user_id == user_id)
    if active_only:
        query = query.filter(RecurringTransaction.is_active == True)
        
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                RecurringTransaction.description.ilike(search_pattern),
                cast(RecurringTransaction.amount, String).ilike(search_pattern)
            )
        )
        
    if category:
        query = query.filter(RecurringTransaction.category.ilike(category))
        
    return query.order_by(RecurringTransaction.next_due_date.asc()).all()

def update_recurring_next_due(db: Session, recurring_id: int, next_due_date: datetime):
    recurring = db.query(RecurringTransaction).filter(RecurringTransaction.id == recurring_id).first()
    if recurring:
        recurring.next_due_date = next_due_date
        db.commit()
        db.refresh(recurring)
        return recurring
    return None

def toggle_recurring_active(db: Session, recurring_id: int, user_id: int):
    recurring = db.query(RecurringTransaction).filter(
        RecurringTransaction.id == recurring_id,
        RecurringTransaction.user_id == user_id
    ).first()
    if recurring:
        recurring.is_active = not recurring.is_active
        db.commit()
        db.refresh(recurring)
        return recurring
    return None

def delete_recurring(db: Session, recurring_id: int, user_id: int):
    recurring = db.query(RecurringTransaction).filter(
        RecurringTransaction.id == recurring_id,
        RecurringTransaction.user_id == user_id
    ).first()
    if recurring:
        db.delete(recurring)
        db.commit()
        return True
    return False

# ========== GOALS CRUD ==========
def create_goal(db: Session, user_id: int, name: str, target_amount: float, target_date: datetime = None):
    goal = Goal(
        user_id=user_id,
        name=name,
        target_amount=target_amount,
        current_amount=0.0,
        target_date=target_date,
        is_achieved=False
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal

def get_goals(db: Session, user_id: int, include_achieved: bool = True):
    query = db.query(Goal).filter(Goal.user_id == user_id)
    if not include_achieved:
        query = query.filter(Goal.is_achieved == False)
    return query.order_by(Goal.created_at.desc()).all()

def update_goal_progress(db: Session, goal_id: int, user_id: int, amount: float):
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()
    if goal:
        goal.current_amount = amount
        if goal.current_amount >= goal.target_amount:
            goal.is_achieved = True
        db.commit()
        db.refresh(goal)
        return goal
    return None

def delete_goal(db: Session, goal_id: int, user_id: int):
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()
    if goal:
        db.delete(goal)
        db.commit()
        return True
    return False

# ========== TRANSACTION SEARCH & FILTER ==========
def search_transactions(
    db: Session, user_id: int = None,
    search_term: str = None,
    category: str = None,
    transaction_type: TransactionType = None,
    start_date: datetime = None,
    end_date: datetime = None,
    min_amount: float = None,
    max_amount: float = None,
    limit: int = 100,
    offset: int = 0
):
    query = db.query(Transaction).filter(Transaction.is_deleted == False)
    
    if user_id is not None:
        # Check family
        from app.db.crud import get_family_user_ids
        family_ids = get_family_user_ids(db, user_id)
        if len(family_ids) > 1:
            query = query.filter(Transaction.user_id.in_(family_ids))
        else:
            query = query.filter(Transaction.user_id == user_id)
    
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                Transaction.description.ilike(search_pattern),
                Transaction.raw_input.ilike(search_pattern),
                cast(Transaction.amount, String).ilike(search_pattern)
            )
        )
    
    if category:
        query = query.filter(Transaction.category.ilike(category))
    
    if transaction_type:
        query = query.filter(or_(
            Transaction.type == transaction_type,
            cast(Transaction.type, String).ilike(transaction_type.value),
            cast(Transaction.type, String).ilike(transaction_type.name)
        ))
    
    if start_date:
        query = query.filter(Transaction.created_at >= start_date)
    
    if end_date:
        query = query.filter(Transaction.created_at < end_date)
    
    if min_amount:
        query = query.filter(Transaction.amount >= min_amount)
    
    if max_amount:
        query = query.filter(Transaction.amount <= max_amount)
    
    # Return both the query (for counting) and the limited results
    total = query.count()
    results = query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
    
    return results, total

# ========== MULTI-MONTH REPORTS ==========
def get_multi_month_stats(db: Session, user_id: int = None, months: int = 6):
    """Get stats for last N months - shared family view"""
    now = datetime.now()
    
    # Adjust for custom start day
    start_day = 1
    if user_id:
        from app.db.models import UserPreference
        pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        if pref:
            start_day = pref.start_of_month
            
    current_year = now.year
    current_month = now.month
    
    if start_day > 1 and now.day >= start_day:
        # We are in next month's period
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1

    results = []
    
    for i in range(months):
        target_month = current_month - i
        target_year = current_year
        
        while target_month <= 0:
            target_month += 12
            target_year -= 1
            
        month_date = datetime(target_year, target_month, 1)
        
        stats = crud.get_monthly_stats(db, user_id, target_year, target_month)
        results.append({
            "year": target_year,
            "month": target_month,
            "month_name": month_date.strftime("%B"),
            **stats
        })
    
    # Reverse to show oldest first (for better chart visualization)
    return list(reversed(results))

def compare_months(db: Session, user_id: int, year1: int, month1: int, year2: int, month2: int):
    """Compare two months"""
    stats1 = get_monthly_stats(db, user_id, year1, month1)
    stats2 = get_monthly_stats(db, user_id, year2, month2)
    
    return {
        "month1": {"year": year1, "month": month1, **stats1},
        "month2": {"year": year2, "month": month2, **stats2},
        "income_diff": stats2["income"] - stats1["income"],
        "expenses_diff": stats2["expenses"] - stats1["expenses"],
        "balance_diff": stats2["balance"] - stats1["balance"]
    }

# ========== PROJECTED EXPENSES (NEW) ==========
def get_projected_expenses(db: Session, user_id: int):
    """
    Calculate projected expenses for the next month based on:
    1. Active recurring transactions (bills, etc.)
    2. Average variable expenses (non-recurring) from last 3 months
    """
    # 1. Calculate Recurring Component
    recurring_txs = get_recurring_transactions(db, user_id, active_only=True)
    recurring_total = 0 # Use int 0 to allow Decimal addition
    
    from app.db.models import TransactionType
    
    for tx in recurring_txs:
        # Skip Income
        if tx.type == TransactionType.INCOME:
            continue
            
        # Normalize to monthly amount
        if tx.recurrence_type == RecurrenceType.DAILY:
            recurring_total += tx.amount * 30
        elif tx.recurrence_type == RecurrenceType.WEEKLY:
            recurring_total += tx.amount * 4
        elif tx.recurrence_type == RecurrenceType.MONTHLY:
            recurring_total += tx.amount
        elif tx.recurrence_type == RecurrenceType.YEARLY:
            # We only include yearly if it's due next month? 
            # OR we prorate it? The user wants "Minimum money to prepare Next Month".
            # So proration might be misleading if the bill is actually 5 months away.
            # Let's include it ONLY if next_due_date is within the next 30-40 days.
            today = datetime.now().date()
            if tx.next_due_date:
                days_until = (tx.next_due_date.date() - today).days
                if 0 <= days_until <= 35: # Broad next month window
                    recurring_total += tx.amount

    # 2. Calculate Variable Component
    # Use last 90 days rolling window to include recent data (since user might be new)
    now = datetime.now()
    start_date = now - timedelta(days=90)
    
    # Query expenses excluding recurring ones
    # We identify recurring-generated transactions by 'recurring_id' IS NOT NULL
    # To prevent double counting manually entered recurring payments, we also exclude
    # transactions that look like they belong to active recurring rules.
    
    recurring_descriptions = [r.description.lower() for r in recurring_txs if r.description]
    recurring_amounts = [r.amount for r in recurring_txs] # NEW: List of recurring amounts

    # Base query for variable expenses
    query = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.type == TransactionType.EXPENSE,
        Transaction.recurring_id == None, # Non-recurring only
        Transaction.created_at >= start_date,
        Transaction.created_at <= now,
        Transaction.is_deleted == False
    )
    
    candidate_txs = query.all()
    
    variable_sum = 0 # Use int 0 to allow Decimal addition
    for tx in candidate_txs:
        is_duplicate = False
        
        # 1. Check description similarity (existing logic)
        if tx.description:
            desc_lower = tx.description.lower()
            for rec_desc in recurring_descriptions:
                if rec_desc in desc_lower or desc_lower in rec_desc:
                    is_duplicate = True
                    break
        
        # 2. NEW: Check EXACT amount match
        # If a manual transaction has the exact same amount as a recurring rule, 
        # assume it IS that recurring payment (e.g. 607350 vs 607350).
        if not is_duplicate and tx.amount in recurring_amounts:
            is_duplicate = True
            
        if not is_duplicate:
            variable_sum += tx.amount
        # else:
            # print(f"Excluded potential duplicate: {tx.description} ({tx.amount})")

    variable_expenses = variable_sum
    
    # Calculate daily average over the actual period
    # If using less than 90 days of data (new user), we should average over the actual days used
    # But for simplicity, let's just use 90 days normalization if the account is old enough, 
    # or finding the first transaction date.
    
    # For now, let's stick to a simple "Average Monthly based on 90 days window"
    # If the user has data for less than 90 days, this might underestimate (dividing by 3 months).
    # Improved logic: Get the date of the first transaction in this period.
    first_tx_date = db.query(func.min(Transaction.created_at)).filter(
        Transaction.user_id == user_id,
        Transaction.type == TransactionType.EXPENSE,
        Transaction.created_at >= start_date
    ).scalar()
    
    if first_tx_date:
        # Calculate days since first transaction
        days_active = (now - first_tx_date.replace(tzinfo=None)).days + 1
        days_active = max(1, days_active) # Avoid division by zero
        
        if days_active < 14:
            # New user protection: safe fallback
            variable_monthly_avg = float(variable_sum)
        else:
            # If active long enough, normalize to monthly
            daily_average = float(variable_sum) / days_active
            variable_monthly_avg = daily_average * 30
    else:
        variable_monthly_avg = 0.0
    
    # 3. Apply Buffer (10%)
    total_projected = float(recurring_total) + (variable_monthly_avg * 1.1)
    
    return {
        "recurring": float(recurring_total),
        "variable": variable_monthly_avg,
        "total": total_projected
    }

# ========== TRANSACTION PHOTOS ==========
def add_transaction_photo(db: Session, transaction_id: int, filename: str, file_path: str):
    photo = TransactionPhoto(
        transaction_id=transaction_id,
        filename=filename,
        file_path=file_path
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo

def get_transaction_photos(db: Session, transaction_id: int):
    return db.query(TransactionPhoto).filter(TransactionPhoto.transaction_id == transaction_id).all()

def delete_transaction_photo(db: Session, photo_id: int):
    photo = db.query(TransactionPhoto).filter(TransactionPhoto.id == photo_id).first()
    if photo:
        db.delete(photo)
        db.commit()
        return True
    return False

# ========== NOTIFICATIONS ==========
def create_notification(
    db: Session, user_id: int, title: str, message: str, notification_type: str
):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        is_read=False
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification

def get_notifications(db: Session, user_id: int, unread_only: bool = False, limit: int = 50):
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()

def mark_notification_read(db: Session, notification_id: int, user_id: int):
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if notification:
        notification.is_read = True
        db.commit()
        db.refresh(notification)
        return notification
    return None

def mark_all_notifications_read(db: Session, user_id: int):
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()

# ========== ASSETS CRUD ==========
def create_asset(
    db: Session, user_id: int, asset_type, name: str,
    current_value: float, acquisition_date: datetime = None,
    acquisition_value: float = None, quantity: float = None,
    unit: str = None, notes: str = None
):
    from app.db.models import Asset
    
    asset = Asset(
        user_id=user_id,
        asset_type=asset_type,
        name=name,
        current_value=current_value,
        acquisition_date=acquisition_date,
        acquisition_value=acquisition_value,
        quantity=quantity,
        unit=unit,
        notes=notes,
        is_active=True
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset

def get_assets(db: Session, user_id: int = None, asset_type=None, active_only: bool = True):
    from app.db.models import Asset
    
    query = db.query(Asset)
    if user_id:
        query = query.filter(Asset.user_id == user_id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if active_only:
        query = query.filter(Asset.is_active == True)
    return query.order_by(Asset.created_at.desc()).all()

def get_asset_by_id(db: Session, asset_id: int, user_id: int = None):
    from app.db.models import Asset
    
    query = db.query(Asset).filter(Asset.id == asset_id)
    if user_id:
        query = query.filter(Asset.user_id == user_id)
    return query.first()

def update_asset(
    db: Session, asset_id: int, user_id: int,
    name: str = None, current_value: float = None,
    acquisition_date: datetime = None, acquisition_value: float = None,
    quantity: float = None, unit: str = None, notes: str = None,
    create_history: bool = True
):
    from app.db.models import Asset, AssetHistory
    
    asset = get_asset_by_id(db, asset_id, user_id)
    if not asset:
        return None
    
    # Track value change
    if current_value is not None and current_value != asset.current_value and create_history:
        history = AssetHistory(
            asset_id=asset_id,
            old_value=asset.current_value,
            new_value=current_value,
            updated_by_user_id=user_id,
            notes="Value updated"
        )
        db.add(history)
    
    # Update fields
    if name is not None:
        asset.name = name
    if current_value is not None:
        asset.current_value = current_value
    if acquisition_date is not None:
        asset.acquisition_date = acquisition_date
    if acquisition_value is not None:
        asset.acquisition_value = acquisition_value
    if quantity is not None:
        asset.quantity = quantity
    if unit is not None:
        asset.unit = unit
    if notes is not None:
        asset.notes = notes
    
    db.commit()
    db.refresh(asset)
    return asset

def update_asset_value(db: Session, asset_id: int, user_id: int, new_value: float, notes: str = None):
    """Update only the value of an asset and create history entry"""
    from app.db.models import Asset, AssetHistory
    
    asset = get_asset_by_id(db, asset_id, user_id)
    if not asset:
        return None
    
    # Create history entry
    history = AssetHistory(
        asset_id=asset_id,
        old_value=asset.current_value,
        new_value=new_value,
        updated_by_user_id=user_id,
        notes=notes or "Value updated"
    )
    db.add(history)
    
    # Update asset
    asset.current_value = new_value
    db.commit()
    db.refresh(asset)
    return asset

def delete_asset(db: Session, asset_id: int, user_id: int):
    """Soft delete an asset"""
    from app.db.models import Asset
    
    asset = get_asset_by_id(db, asset_id, user_id)
    if asset:
        asset.is_active = False
        db.commit()
        return True
    return False

def get_asset_total_value(db: Session, user_id: int):
    """Get total value of all active assets"""
    from app.db.models import Asset
    
    total = db.query(func.sum(Asset.current_value)).filter(
        Asset.user_id == user_id,
        Asset.is_active == True
    ).scalar()
    return float(total or 0)

def get_asset_breakdown(db: Session, user_id: int):
    """Get asset value grouped by type"""
    from app.db.models import Asset
    
    results = db.query(
        Asset.asset_type,
        func.sum(Asset.current_value).label('total_value'),
        func.count(Asset.id).label('count')
    ).filter(
        Asset.user_id == user_id,
        Asset.is_active == True
    ).group_by(Asset.asset_type).all()
    
    breakdown = []
    for asset_type, total_value, count in results:
        breakdown.append({
            'type': asset_type.value,
            'type_enum': asset_type,
            'total_value': float(total_value or 0),
            'count': count
        })
    
    return breakdown

def get_asset_history(db: Session, asset_id: int, limit: int = 50):
    """Get value change history for an asset"""
    from app.db.models import AssetHistory
    
    return db.query(AssetHistory).filter(
        AssetHistory.asset_id == asset_id
    ).order_by(AssetHistory.created_at.desc()).limit(limit).all()
