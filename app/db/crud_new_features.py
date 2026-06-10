"""
CRUD operations for new features
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_
from datetime import datetime, timedelta
from typing import Optional, List
import calendar
import math
from app.db.models import (
    Transaction, TransactionType, Currency, FamilyMember,
    TransactionEdit, ReceiptOCR, UserPreference, RecurringTransaction,
    RecurrenceType, User
)

# ========== TRANSACTION EDIT & DELETE ==========
# ========== TRANSACTION EDIT & DELETE ==========
def update_transaction(
    db: Session, transaction_id: int, user_id: int,
    amount: float = None, category: str = None,
    description: str = None, notes: str = None
):
    """Update transaction and log edit history"""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
        Transaction.is_deleted == False
    ).first()
    
    if not transaction:
        return None
    
    # Create edit record
    edit = TransactionEdit(
        transaction_id=transaction_id,
        edited_by_user_id=user_id,
        old_amount=transaction.amount,
        new_amount=amount if amount else transaction.amount,
        old_category=transaction.category if transaction.category else None,
        new_category=category if category else (transaction.category if transaction.category else None),
        old_description=transaction.description,
        new_description=description if description else transaction.description
    )
    
    # Update transaction
    if amount is not None:
        transaction.amount = amount
    if category is not None:
        transaction.category = category
    if description is not None:
        transaction.description = description
    if notes is not None:
        transaction.notes = notes
    
    db.add(edit)
    db.commit()
    db.refresh(transaction)
    return transaction

def delete_transaction(db: Session, transaction_id: int, user_id: int):
    """Soft delete a transaction"""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    ).first()
    
    if not transaction:
        return False
        
    transaction.is_deleted = True
    transaction.deleted_at = datetime.now()
    db.commit()
    return True

def restore_transaction(db: Session, transaction_id: int, user_id: int):
    """Restore a soft-deleted transaction"""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    ).first()
    
    if not transaction:
        return None
        
    transaction.is_deleted = False
    transaction.deleted_at = None
    db.commit()
    db.refresh(transaction)
    return transaction

def create_receipt_ocr(
    db: Session, transaction_id: int, photo_id: int,
    extracted_text: str = None, merchant_name: str = None,
    total_amount: float = None, date_detected: datetime = None,
    items: str = None, confidence_score: float = 0.0
):
    """Create a new receipt OCR record"""
    ocr_record = ReceiptOCR(
        transaction_id=transaction_id,
        photo_id=photo_id,
        extracted_text=extracted_text,
        merchant_name=merchant_name,
        total_amount=total_amount,
        date_detected=date_detected,
        items=items,
        confidence_score=confidence_score
    )
    db.add(ocr_record)
    db.commit()
    db.refresh(ocr_record)
    return ocr_record

# ========== SPENDING PATTERNS ==========


# NOTE: The template expects 'patterns' to be a time series for the main chart, NOT a category breakdown.
# But I implemented a category breakdown above. This is the mismatch.
# I need to change this function to return monthly TOTALS for the line chart.

def get_spending_patterns(db: Session, user_id: int, months: int = 12):
    """
    Get total spending trend over the last N months (for Line Chart).
    """
    now = datetime.now()
    trends = []
    
    
    # Get user start day
    start_day = 1
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if pref:
        start_day = pref.start_of_month
        
    # Adjust starting point if in next period
    current_year = now.year
    current_month = now.month
    
    if start_day > 1 and now.day >= start_day:
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1

    from app.db.crud import get_monthly_period_dates

    for i in range(months):
        target_month = current_month - i
        target_year = current_year
        
        while target_month <= 0:
            target_month += 12
            target_year -= 1
            
        start_date, end_date = get_monthly_period_dates(target_year, target_month, start_day)
        
        total = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_date,
            Transaction.created_at < end_date
        ).scalar() or 0
        
        trends.append({
            "year": target_year,
            "month": target_month,
            "total": float(total)
        })
    
    # Return reversed (oldest to newest) for chart
    trends.reverse()
    return trends

# ========== CATEGORY TRENDS ==========

def get_category_trends(db: Session, category: str, user_id: int = None, months: int = 6):
    """Get spending trends for a specific category - shared family view"""
    now = datetime.now()
    trends = []
    
    for i in range(months):
        month_date = now.replace(day=1) - timedelta(days=30 * i)
        year = month_date.year
        month = month_date.month
        
        transactions = db.query(Transaction).filter(
            Transaction.category == category,
            Transaction.is_deleted == False,
            extract('year', Transaction.created_at) == year,
            extract('month', Transaction.created_at) == month
        ).all()
        
        total = sum(float(t.amount) for t in transactions)
        trends.append({
            "year": year,
            "month": month,
            "amount": total
        })
    
    return trends

    return trends

def get_category_breakdown(db: Session, user_id: int, start_date: datetime, end_date: datetime):
    """
    Get aggregated spending by category for a specific date range.
    Returns: List of dicts sorted by total amount (desc).
    """
    # Group by category and sum amounts
    results = db.query(
        Transaction.category,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count")
    ).filter(
        Transaction.user_id == user_id,
        Transaction.type == TransactionType.EXPENSE,
        Transaction.is_deleted == False,
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date
    ).group_by(Transaction.category).all()
    
    # Format and sort
    breakdown = []
    total_period_expenses = 0
    
    for cat, total, count in results:
        total = float(total or 0)
        breakdown.append({
            "category": cat,
            "total": total,
            "count": count
        })
        total_period_expenses += total
        
    # Sort by total amount descending
    breakdown.sort(key=lambda x: x["total"], reverse=True)
    
    # Calculate percentages
    for item in breakdown:
        item["percentage"] = (item["total"] / total_period_expenses * 100) if total_period_expenses > 0 else 0
        
    return breakdown


def get_monthly_summary(db: Session, user_id: int, months: int = 12):
    """
    Get monthly Income vs Expense summary for the last N months.
    """
    now = datetime.now()
    summary = []
    
    # Use existing helper for period calculation logic if needed, 
    # but here we can iterate standard months for simplicity or use the user's start day.
    # For consistency with other charts, let's respect user start_day.
    
    start_day = 1
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if pref:
        start_day = pref.start_of_month
        
    current_year = now.year
    current_month = now.month
    
    if start_day > 1 and now.day >= start_day:
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1
            
    from app.db.crud import get_monthly_period_dates

    for i in range(months):
        target_month = current_month - i
        target_year = current_year
        
        while target_month <= 0:
            target_month += 12
            target_year -= 1
            
        start_date, end_date = get_monthly_period_dates(target_year, target_month, start_day)
        
        # Get Expenses
        expense_total = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_date,
            Transaction.created_at < end_date
        ).scalar() or 0
        expense_total = float(expense_total)
        
        # Get Income
        income_total = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.INCOME,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_date,
            Transaction.created_at < end_date
        ).scalar() or 0
        income_total = float(income_total)
        
        summary.append({
            "year": target_year,
            "month": target_month,
            "expense": expense_total,
            "income": income_total,
            "net": income_total - expense_total
        })
    
    summary.reverse()
    return summary

def get_family_member_spending(db: Session, user_id: int, months: int = 1):
    """
    Get spending breakdown by family member for the last N months.
    """
    now = datetime.now()
    start_date = (now.replace(day=1) - timedelta(days=30 * months)).replace(day=1)
    
    # Query expenses joined with family members (if applicable)
    # Note: Transaction model has family_member_id
    
    expenses = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.type == TransactionType.EXPENSE,
        Transaction.is_deleted == False,
        Transaction.created_at >= start_date,
        Transaction.created_at <= now
    ).all()
    
    member_spending = {}
    
    # Initialize with "Me" (Owner)
    member_spending[0] = {"name": "Saya (Pribadi)", "total": 0.0, "count": 0}
    
    # Fetch all family members name map
    members = db.query(FamilyMember).filter(
        FamilyMember.user_id == user_id
    ).all()
    
    member_map = {m.id: m.name for m in members}
    
    for tx in expenses:
        mid = tx.family_member_id
        if mid and mid in member_map:
            member_name = member_map[mid]
            key = mid
        else:
            member_name = "Saya (Pribadi)"
            key = 0
            
        if key not in member_spending:
            member_spending[key] = {"name": member_name, "total": 0.0, "count": 0}
            
        member_spending[key]["total"] += float(tx.amount)
        member_spending[key]["count"] += 1
        
    return list(member_spending.values())

def get_spending_trends_by_category(db: Session, months: int = 6):
    """Get spending trends grouped by category over time - shared family view"""
    now = datetime.now()
    category_trends = {}
    
    for i in range(months):
        month_date = now.replace(day=1) - timedelta(days=30 * i)
        year = month_date.year
        month = month_date.month
        
        transactions = db.query(Transaction).filter(
            Transaction.type == TransactionType.EXPENSE,
            Transaction.is_deleted == False,
            extract('year', Transaction.created_at) == year,
            extract('month', Transaction.created_at) == month
        ).all()
        
        for t in transactions:
            cat_name = t.category
            if cat_name not in category_trends:
                category_trends[cat_name] = []
            category_trends[cat_name].append({
                "year": year,
                "month": month,
                "amount": t.amount,
                "date": t.created_at
            })
    
    # Aggregate by month per category
    aggregated = {}
    for cat_name, transactions_list in category_trends.items():
        monthly_totals = {}
        for t in transactions_list:
            key = f"{t['year']}-{t['month']:02d}"
            if key not in monthly_totals:
                monthly_totals[key] = {"year": t['year'], "month": t['month'], "amount": 0.0}
            monthly_totals[key]["amount"] += float(t["amount"])
        
        aggregated[cat_name] = sorted(monthly_totals.values(), key=lambda x: (x["year"], x["month"]))
    
    return aggregated

# ... (skip to predict_category_spending)

def predict_category_spending(db: Session, category: str, months_history: int = 6):
    """Predict next month spending for a specific category - shared family view"""
    now = datetime.now()
    
    # Get historical data for this category
    historical = []
    for i in range(months_history):
        month_date = now.replace(day=1) - timedelta(days=30 * i)
        year = month_date.year
        month = month_date.month
        
        transactions = db.query(Transaction).filter(
            Transaction.category == category,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.is_deleted == False,
            extract('year', Transaction.created_at) == year,
            extract('month', Transaction.created_at) == month
        ).all()
        
        total = sum(float(t.amount) for t in transactions)
        historical.append({
            "year": year,
            "month": month,
            "total": total,
            "count": len(transactions)
        })
    
    if len(historical) < 2:
        return {
            "predicted_total": 0,
            "predicted_count": 0,
            "confidence": "low",
            "method": "insufficient_data"
        }
    
    # Simple Moving Average
    historical.reverse()
    recent_months = historical[-3:] if len(historical) >= 3 else historical
    avg_total = sum(m["total"] for m in recent_months) / len(recent_months)
    avg_count = sum(m["count"] for m in recent_months) / len(recent_months)
    
    # Trend calculation
    recent_values = [m["total"] for m in recent_months]
    if len(recent_values) >= 2:
        trend = (recent_values[-1] - recent_values[0]) / len(recent_values)
        predicted_total = avg_total + trend
    else:
        predicted_total = avg_total
    
    # Confidence
    values = [m["total"] for m in recent_months]
    if len(values) > 1 and avg_total > 0:
        variance = sum((v - avg_total) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        cv = (std_dev / avg_total * 100)
        confidence = "high" if cv < 20 else ("medium" if cv < 40 else "low")
    else:
        confidence = "low"
    
    return {
        "predicted_total": max(0, predicted_total),
        "predicted_count": int(avg_count),
        "confidence": confidence,
        "method": "moving_average",
        "historical_average": avg_total,
        "trend": trend if len(historical) >= 2 else 0
    }

# ========== SPENDING PATTERNS BY DAY ==========
def get_spending_pattern_by_day_of_week(db: Session, months: int = 3):
    """
    Analyze spending by day of the week (Monday-Sunday)
    Returns list of dicts for template iteration.
    """
    now = datetime.now()
    start_date = (now.replace(day=1) - timedelta(days=30 * months)).replace(day=1)
    
    expenses = db.query(Transaction).filter(
        Transaction.type == TransactionType.EXPENSE,
        Transaction.is_deleted == False,
        Transaction.created_at >= start_date,
        Transaction.created_at <= now
    ).all()
    
    # Initialize data structure
    # 0=Monday, 6=Sunday
    days_data = {i: {"total": 0.0, "count": 0} for i in range(7)}
    
    for tx in expenses:
        weekday = tx.created_at.weekday()
        days_data[weekday]["total"] += float(tx.amount)
        days_data[weekday]["count"] += 1
        
    day_names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    pattern_list = []
    
    # Calculate actual active weeks to get accurate average
    # If user has only been active for 2 weeks, dividing by 12 (3 months) is wrong.
    first_tx_date = db.query(func.min(Transaction.created_at)).filter(
        Transaction.type == TransactionType.EXPENSE,
        Transaction.created_at >= start_date,
        Transaction.created_at <= now
    ).scalar()
    
    if first_tx_date:
        # Ensure naive datetime for subtraction
        if first_tx_date.tzinfo:
            first_tx_date = first_tx_date.replace(tzinfo=None)
            
        days_active = (now - first_tx_date).days
        # Minimum 1 week to avoid division by zero or huge numbers
        weeks = max(1, days_active / 7)
    else:
        weeks = max(1, months * 4) # Fallback if no data
    
    for i in range(7):
        total = days_data[i]["total"]
        avg = total / weeks
        
        pattern_list.append({
            "name": day_names[i],
            "total": total,
            "average": avg,
            "count": days_data[i]["count"],
            "id": i
        })
        
    return pattern_list

# ========== OVERALL PREDICTION ==========
def predict_next_month_spending(db: Session, user_id: int, months_history: int = 6):
    """
    Predict overall spending for next month using Simple Moving Average + Trend
    """
    now = datetime.now()
    historical = []
    
    # Get user preference
    start_day = 1
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if pref:
        start_day = pref.start_of_month 
    
    # Strict iteration logic
    
    # Strict iteration logic
    current_year = now.year
    current_month = now.month
    # Warning: Without user_id I can't know start_day.
    
    from app.db.crud import get_monthly_period_dates

    for i in range(months_history):
        target_month = current_month - i
        target_year = current_year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
            
        start_date, end_date = get_monthly_period_dates(target_year, target_month, start_day)
            
        total = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_date,
            Transaction.created_at < end_date
        ).scalar() or 0
        total = float(total)
        
        count = db.query(func.count(Transaction.id)).filter(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.is_deleted == False,
            Transaction.created_at >= start_date,
            Transaction.created_at < end_date
        ).scalar() or 0
        
        historical.append({
            "year": target_year,
            "month": target_month,
            "total": total,
            "count": count
        })
        
    if len(historical) < 2:
         return {
            "predicted_total": 0.0,
            "predicted_count": 0,
            "confidence": "low",
            "trend": 0,
            "historical_average": 0
        }
        
    historical.reverse()
    
    # Calculate SMA
    recent = historical[-3:] if len(historical) >= 3 else historical
    avg_spending = sum(m["total"] for m in recent) / len(recent)
    avg_count = int(sum(m["count"] for m in recent) / len(recent))
    
    # Calculate Trend
    last_month = historical[-1]["total"]
    if len(historical) >= 2:
        prev_month = historical[-2]["total"]
        trend_val = last_month - prev_month
        trend_pct = (trend_val / prev_month * 100) if prev_month > 0 else 0
    else:
        trend_pct = 0
        
    prediction = avg_spending + (avg_spending * (trend_pct / 100) * 0.5)
    
    return {
        "predicted_total": max(0, prediction),
        "predicted_count": avg_count,
        "confidence": "medium" if len(historical) >= 3 else "low",
        "trend": trend_pct, # Template expects 'trend' -> >0 up, <0 down
        "historical_average": avg_spending
    }


# ========== USER PREFERENCES ==========
def get_user_preference(db: Session, user_id: int):
    """Get user preferences (or create default if not exists)"""
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not pref:
        pref = UserPreference(user_id=user_id, base_currency_code="IDR", dark_mode=False)
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref

def update_user_preference(db: Session, user_id: int, dark_mode: bool = None, base_currency_code: str = None):
    """Update user preferences"""
    pref = get_user_preference(db, user_id)
    
    if dark_mode is not None:
        pref.dark_mode = dark_mode
        
    if base_currency_code:
        pref.currency = base_currency_code
        # Also update User model currency for backward compatibility if needed
        # user = db.query(User).get(user_id)
        # user.currency = base_currency_code
        
    db.commit()
    db.refresh(pref)
    return pref

# ========== FAMILY MEMBERS ==========
def get_family_members(db: Session, user_id: int):
    """Get all family members for a user"""
    return db.query(FamilyMember).filter(FamilyMember.user_id == user_id).all()

def create_family_member(db: Session, user_id: int, name: str, role: str = None):
    """Create a new family member"""
    member = FamilyMember(user_id=user_id, name=name, role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

def delete_family_member(db: Session, member_id: int, user_id: int):
    """Delete a family member"""
    member = db.query(FamilyMember).filter(
        FamilyMember.id == member_id, 
        FamilyMember.user_id == user_id
    ).first()
    
    if member:
        db.delete(member)
        db.commit()
        return True
    return False

# ========== CURRENCY ==========
def get_all_currencies(db: Session):
    """Get all available currencies"""
    return db.query(Currency).all()

def calculate_custom_projection(db: Session, user_id: int):
    """
    Calculate next month projection with improved logic:
    1. Recurring: Sum of active recurring transactions converted by frequency
    2. Non-Recurring: Rolling 90-day window average, extrapolated with buffer
    """
    now = datetime.now()
    
    # --- Calculate days_next_month (handle year rollover) ---
    if now.month == 12:
        next_month_year = now.year + 1
        next_month_num = 1
    else:
        next_month_year = now.year
        next_month_num = now.month + 1
    
    days_next_month = calendar.monthrange(next_month_year, next_month_num)[1]
    
    # --- 1. RUTIN (Recurring) — frequency-based conversion ---
    recurring_items = db.query(RecurringTransaction).filter(
        RecurringTransaction.user_id == user_id,
        RecurringTransaction.is_active == True,
        RecurringTransaction.type == TransactionType.EXPENSE
    ).all()
    
    recurring_total = 0.0
    recurring_details = []
    
    for r in recurring_items:
        amount_projected = 0.0
        r_amount = float(r.amount)
        if r.recurrence_type == RecurrenceType.DAILY:
            amount_projected = r_amount * days_next_month
        elif r.recurrence_type == RecurrenceType.WEEKLY:
            amount_projected = r_amount * (days_next_month / 7)
        elif r.recurrence_type == RecurrenceType.MONTHLY:
            amount_projected = r_amount
        elif r.recurrence_type == RecurrenceType.YEARLY:
            amount_projected = r_amount * (days_next_month / 365.25)
        elif r.recurrence_type == RecurrenceType.CUSTOM:
            interval = r.interval_days if r.interval_days and r.interval_days >= 1 else 30
            amount_projected = r_amount * (days_next_month / interval)
            
        amount_projected = round(amount_projected)
        recurring_total += amount_projected
        
        recurring_details.append({
            "name": r.description or r.category,
            "category": r.category,
            "recurrence_type": r.recurrence_type.value,
            "base_amount": r_amount,
            "projected_amount": amount_projected
        })
    
    # --- 2. NON-RUTIN (Non-Recurring) — rolling 90-day window ---
    BUFFER_FULL = 0.10       # 10% buffer when data >= 30 days
    BUFFER_LIMITED = 0.05    # Max 5% buffer when data < 30 days
    
    # Dynamic baseline: max(user.created_at, today - 90 days)
    user_obj = db.query(User).filter(User.id == user_id).first()
    ninety_days_ago = now - timedelta(days=90)
    
    # Timezone-safe comparison: strip tzinfo for comparison
    user_created = user_obj.created_at if user_obj else now
    if hasattr(user_created, 'tzinfo') and user_created.tzinfo is not None:
        user_created = user_created.replace(tzinfo=None)
    
    start_date = max(user_created, ninety_days_ago)
    
    days_active = (now - start_date).days + 1  # +1 to include today
    if days_active < 1:
        days_active = 1
    
    allowed_categories = [
        "Rumah Tangga", "Konsumsi", "Rokok", "Donasi", "Childcare",
        "Utilitas", "Internet", "Transport", "Kesehatan",
        "Beauty & Personal Care", "Hiburan", "Lain - Lain"
    ]
    
    non_recurring_total = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == TransactionType.EXPENSE,
        Transaction.category.in_(allowed_categories),
        Transaction.recurring_id == None,
        Transaction.is_deleted == False,
        Transaction.created_at >= start_date,
        Transaction.created_at <= now
    ).scalar() or 0
    non_recurring_total = float(non_recurring_total)
    
    # Breakdown by category for non-recurring
    non_rec_breakdown_results = db.query(
        Transaction.category,
        func.sum(Transaction.amount).label("total")
    ).filter(
        Transaction.user_id == user_id,
        Transaction.type == TransactionType.EXPENSE,
        Transaction.category.in_(allowed_categories),
        Transaction.recurring_id == None,
        Transaction.is_deleted == False,
        Transaction.created_at >= start_date,
        Transaction.created_at <= now
    ).group_by(Transaction.category).all()
    
    non_recurring_breakdown = [
        {"category": cat, "total": float(total or 0)} 
        for cat, total in non_rec_breakdown_results
    ]
    non_recurring_breakdown.sort(key=lambda x: x["total"], reverse=True)
    
    # --- Tiered buffer logic ---
    # < 7 days  : no extrapolation, no buffer, is_low_data
    # 7-29 days : extrapolate, scaled buffer 0-5%, is_limited_data
    # >= 30 days: extrapolate, full 10% buffer
    is_low_data = days_active < 7
    is_limited_data = 7 <= days_active < 30
    
    if is_low_data:
        avg_daily = non_recurring_total / days_active if days_active > 0 else 0
        projected_non_recurring = round(non_recurring_total)  # Use actual total
        buffer_percent = 0.0
        buffer_amount = 0.0
    elif is_limited_data:
        avg_daily = non_recurring_total / days_active
        # Scale buffer linearly: 0% at 7 days → 5% at 30 days
        buffer_percent = round(BUFFER_LIMITED * (days_active / 30), 3)
        projected_raw = avg_daily * days_next_month
        buffer_amount = round(projected_raw * buffer_percent)
        projected_non_recurring = round(projected_raw + buffer_amount)
    else:
        avg_daily = non_recurring_total / days_active
        buffer_percent = BUFFER_FULL
        projected_raw = avg_daily * days_next_month
        buffer_amount = round(projected_raw * buffer_percent)
        projected_non_recurring = round(projected_raw + buffer_amount)
    
    total_projection = float(recurring_total) + float(projected_non_recurring)
    
    return {
        "recurring_total": recurring_total,
        "recurring_details": recurring_details,
        "non_recurring_actual": non_recurring_total,
        "non_recurring_breakdown": non_recurring_breakdown,
        "days_active": days_active,
        "avg_daily": round(avg_daily),
        "projected_non_recurring": projected_non_recurring,
        "total_projection": total_projection,
        "start_date": start_date,
        "days_next_month": days_next_month,
        "buffer_percent": buffer_percent,
        "buffer_amount": buffer_amount,
        "is_low_data": is_low_data,
        "is_limited_data": is_limited_data,
    }

# ========== DEBT CRUD ==========
def create_debt(
    db: Session, user_id: int, type: str, creditor: str, 
    total_amount: float, name: str = None, tenor: int = None,
    interest_rate: float = None, installment_amount: float = None,
    due_date: datetime = None, notes: str = None
):
    from app.db.models import Debt, DebtType
    
    # Map string type to Enum
    debt_type = DebtType.PERSONAL
    try:
        debt_type = DebtType(type.lower())
    except:
        pass
        
    debt = Debt(
        user_id=user_id,
        type=debt_type,
        creditor=creditor,
        name=name,
        total_amount=total_amount,
        remaining_amount=total_amount,
        interest_rate=interest_rate,
        tenor=tenor,
        installment_amount=installment_amount,
        due_date=due_date,
        is_active=True,
        notes=notes
    )
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return debt

def get_debts(db: Session, user_id: int, active_only: bool = True):
    from app.db.models import Debt
    query = db.query(Debt).filter(Debt.user_id == user_id)
    if active_only:
        query = query.filter(Debt.is_active == True)
    
    results = query.order_by(Debt.due_date.asc(), Debt.created_at.desc()).all()
    
    # Enrich with calculated fields for the bot
    enriched = []
    now = datetime.now()
    for d in results:
        debt_dict = {c.name: getattr(d, c.name) for c in d.__table__.columns}
        
        # Calculate days_until_due
        if d.due_date:
            delta = d.due_date - now
            days_until_due = delta.days + (1 if delta.seconds > 0 else 0)
            debt_dict["days_until_due"] = days_until_due
            debt_dict["is_overdue"] = days_until_due < 0
        else:
            debt_dict["days_until_due"] = None
            debt_dict["is_overdue"] = False
            
        # Calculate paid count if installments exist
        # Simplified: (Total - Remaining) / Installment
        if d.installment_amount and d.installment_amount > 0:
            paid_amount = float(d.total_amount) - float(d.remaining_amount)
            debt_dict["paid_count"] = int(paid_amount / float(d.installment_amount))
        else:
            debt_dict["paid_count"] = 0
            
        enriched.append(debt_dict)
        
    return enriched

def record_debt_payment(db: Session, debt_id: int, user_id: int, amount: float, transaction_id: int = None, notes: str = None):
    from app.db.models import Debt, DebtPayment
    
    debt = db.query(Debt).filter(Debt.id == debt_id, Debt.user_id == user_id).first()
    if not debt:
        return None
        
    payment = DebtPayment(
        debt_id=debt_id,
        transaction_id=transaction_id,
        amount=amount,
        notes=notes
    )
    
    debt.remaining_amount -= amount
    if debt.remaining_amount <= 0:
        debt.remaining_amount = 0
        debt.is_active = False
        
    db.add(payment)
    db.commit()
    db.refresh(debt)
    return debt

def get_debt_summary(db: Session, user_id: int):
    from app.db.models import Debt
    debts = get_debts(db, user_id)
    
    total_remaining = sum(float(d.remaining_amount) for d in debts)
    total_original = sum(float(d.total_amount) for d in debts)
    
    # Overdue
    now = datetime.now()
    overdue_count = sum(1 for d in debts if d.due_date and d.due_date < now)
    overdue_amount = sum(float(d.remaining_amount) for d in debts if d.due_date and d.due_date < now)
    
    return {
        "total_debts": len(debts),
        "total_remaining": total_remaining,
        "total_original": total_original,
        "overdue_count": overdue_count,
        "overdue_amount": overdue_amount,
        "debts": debts
    }

