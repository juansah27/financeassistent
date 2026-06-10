from sqlalchemy.orm import Session
from sqlalchemy import func, extract, cast, Date
from datetime import datetime, timedelta
from app.db.models import User, Transaction, TransactionType, UserPreference
from app.db import crud_extended, models
import bcrypt

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verify PIN using bcrypt"""
    try:
        return bcrypt.checkpw(plain_pin.encode('utf-8'), hashed_pin.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(pin: str) -> str:
    """Hash PIN using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pin.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_all_users(db: Session):
    return db.query(User).all()

def create_user(db: Session, username: str, pin: str):
    hashed_pin = get_password_hash(pin)
    db_user = User(username=username, pin_hash=hashed_pin)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.refresh(db_user)
    return db_user

# Family CRUD
def create_family(db: Session, name: str):
    import random, string
    # Generate unique 6-char code
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choice(chars) for _ in range(6))
        if not db.query(models.Family).filter(models.Family.join_code == code).first():
            break
            
    family = models.Family(name=name, join_code=code)
    db.add(family)
    db.commit()
    db.refresh(family)
    return family

def get_family_by_code(db: Session, code: str):
    return db.query(models.Family).filter(models.Family.join_code == code).first()

def get_family_users(db: Session, family_id: int):
    return db.query(User).filter(User.family_id == family_id).all()

def get_family_user_ids(db: Session, user_id: int):
    """Get list of user_ids in the same family (including self)"""
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.family_id:
        family_users = db.query(User.id).filter(User.family_id == user.family_id).all()
        return [u.id for u in family_users]
    return [user_id]

def create_transaction(db: Session, user_id: int, transaction_type: TransactionType, 
                        amount: float, category: str, description: str = None, raw_input: str = None,
                        recurring_id: int = None, account_id: int = None, destination_account_id: int = None,
                        tags: str = None):
    db_transaction = Transaction(
        user_id=user_id,
        type=transaction_type,
        amount=amount,
        category=category,
        description=description,
        raw_input=raw_input,
        recurring_id=recurring_id,
        account_id=account_id,
        destination_account_id=destination_account_id,
        tags=tags,
        is_deleted=False,
        currency_code="IDR"
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    
    # Auto-update account balances
    if account_id:
        account_updated_at = db_transaction.created_at
        if transaction_type == TransactionType.TRANSFER and destination_account_id:
            # TRANSFER: source -, destination +
            update_account_balance(db, account_id, -amount, account_updated_at)
            update_account_balance(db, destination_account_id, amount, account_updated_at)
        elif transaction_type in [TransactionType.EXPENSE, TransactionType.SAVING, TransactionType.INVESTMENT, TransactionType.DEBT]:
            # Uang keluar: kurangi balance akun
            update_account_balance(db, account_id, -amount, account_updated_at)
        elif transaction_type == TransactionType.INCOME:
            # Uang masuk: tambah balance akun
            update_account_balance(db, account_id, amount, account_updated_at)
    
    return db_transaction


def update_account_balance(db: Session, account_id: int, amount_change: float, updated_at=None):
    """Update account balance by adding amount_change (positive or negative)."""
    from sqlalchemy import text
    db.execute(
        text("""
            UPDATE accounts
            SET balance = COALESCE(balance, 0) + :change,
                updated_at = COALESCE(:updated_at, NOW())
            WHERE id = :id
        """),
        {"change": amount_change, "id": account_id, "updated_at": updated_at}
    )
    db.commit()


def get_user_transactions(db: Session, user_id: int = None, limit: int = 100):
    query = db.query(Transaction).filter(Transaction.is_deleted == False)
    if user_id is not None:
        # Check family
        family_ids = get_family_user_ids(db, user_id)
        if len(family_ids) > 1:
            query = query.filter(Transaction.user_id.in_(family_ids))
        else:
            query = query.filter(Transaction.user_id == user_id)
            
    return query.order_by(Transaction.created_at.desc()).limit(limit).all()

def get_current_period(db: Session, user_id: int):
    """
    Get current period (year, month) and start_day based on user preference.
    """
    start_day = 1
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if pref:
        start_day = pref.start_of_month

    now = datetime.now()
    year = now.year
    month = now.month
    
    if start_day > 1 and now.day >= start_day:
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
            
    return year, month, start_day

def get_monthly_stats(db: Session, user_id: int = None, year: int = None, month: int = None):
    
    # Determine period and start_day
    start_day = 1
    if year is None:
        if user_id:
            year, month, start_day = get_current_period(db, user_id)
        else:
            now = datetime.now()
            year = now.year
            month = now.month
    elif user_id:
        pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        if pref:
            start_day = pref.start_of_month

    # Determine date range based on start_day
    # If start_day=1: Period matches calendar month (e.g. Feb 1 - Mar 1)
    # If start_day=25: Period for Feb ends in Feb. Start is Jan 25, End is Feb 25.
    
    # If current date is before start_day, we are effectively in the previous calendar month's cycle?
    # No, let's stick to the definition: "Month X" period ends in Month X.
    # So range is: [Month-1 Day=start_day, Month Day=start_day)
    
    if start_day == 1:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
    else:
        # Range ends at Year-Month-StartDay
        try:
            end_date = datetime(year, month, start_day)
        except ValueError:
            # Fallback for invalid dates (e.g. Feb 30), use last day of month + time
            # Simplification: use the 1st of next month for now until robust logic needed
             if month == 12:
                end_date = datetime(year + 1, 1, 1)
             else:
                end_date = datetime(year, month + 1, 1)

        # Start is previous month
        if month == 1:
            start_year = year - 1
            start_month = 12
        else:
            start_year = year
            start_month = month - 1
            
        try:
            start_date = datetime(start_year, start_month, start_day)
        except ValueError:
             start_date = datetime(start_year, start_month, 1) # Fallback

    # Determine period if using defaults (which default to simple calendar now() year/month)
    # If I am on Feb 1, and start_day is 25.
    # passed year=2026, month=2.
    # Computed Range: Jan 25 - Feb 25.
    # This correctly covers Feb 1.
    
    # If I am on Feb 26.
    # passed year=2026, month=2.
    # Range: Jan 25 - Feb 25.
    # My date (Feb 26) is NOT in this range.
    # So dashboard showing "Month 2" would show OLD data (Jan-Feb).
    # BUT "Current status" should show "Mar" period.
    # So if defaults were used, we need to adjust year/month to the CURRENT PERIOD.
    
    # Determine date range base query
    base_query = db.query(Transaction).filter(
        Transaction.is_deleted == False,
        Transaction.created_at >= start_date,
        Transaction.created_at < end_date
    )
    
    if user_id is not None:
        family_ids = get_family_user_ids(db, user_id)
        if len(family_ids) > 1:
            base_query = base_query.filter(Transaction.user_id.in_(family_ids))
        else:
            base_query = base_query.filter(Transaction.user_id == user_id)
            
    # 1. Total by Type Aggregation
    type_totals = db.query(
        Transaction.type,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).filter(
        Transaction.id.in_(base_query.with_entities(Transaction.id))
    ).group_by(Transaction.type).all()
    
    # Map results
    res_map = {t.value: float(amt or 0) for t, amt, count in type_totals}
    transaction_count = sum(count for t, amt, count in type_totals)
    
    income = res_map.get(TransactionType.INCOME.value, 0.0)
    expenses = res_map.get(TransactionType.EXPENSE.value, 0.0)
    saving = res_map.get(TransactionType.SAVING.value, 0.0)
    investment = res_map.get(TransactionType.INVESTMENT.value, 0.0)
    debt = res_map.get(TransactionType.DEBT.value, 0.0)
    balance = income - (expenses + saving + investment + debt)
    
    # 2. Category Breakdown Aggregation (Expenses only)
    cat_totals = db.query(
        Transaction.category,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.id.in_(base_query.with_entities(Transaction.id)),
        Transaction.type == TransactionType.EXPENSE
    ).group_by(Transaction.category).all()
    
    category_breakdown = {cat: float(total or 0) for cat, total in cat_totals}
    
    return {
        "income": float(income or 0),
        "expenses": float(expenses or 0),
        "saving": float(saving or 0),
        "investment": float(investment or 0),
        "debt": float(debt or 0),
        "balance": float(balance or 0),
        "category_breakdown": category_breakdown,
        "transaction_count": transaction_count
    }

def get_monthly_period_dates(year: int, month: int, start_day: int = 1):
    """
    Calculate start and end dates for a monthly period.
    Returns (start_date, end_date) where end_date is exclusive.
    """
    if start_day == 1:
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
    else:
        # Range ends at Year-Month-StartDay
        try:
            end_date = datetime(year, month, start_day)
        except ValueError:
            # Fallback for invalid dates logic
             if month == 12:
                end_date = datetime(year + 1, 1, 1)
             else:
                end_date = datetime(year, month + 1, 1)

        # Start is previous month
        if month == 1:
            start_year = year - 1
            start_month = 12
        else:
            start_year = year
            start_month = month - 1
            
        try:
            start_date = datetime(start_year, start_month, start_day)
        except ValueError:
             start_date = datetime(start_year, start_month, 1) 
             
    return start_date, end_date

def get_weekly_stats(db: Session, user_id: int = None, days: int = 7):
    """Get daily stats for the last N days"""
    now = datetime.now()
    start_date = now - timedelta(days=days)
    
    # 1. Aggregation by Date and Type
    results = db.query(
        cast(Transaction.created_at, Date).label('tx_date'),
        Transaction.type,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.is_deleted == False,
        Transaction.created_at >= start_date
    )
    
    if user_id is not None:
        family_ids = get_family_user_ids(db, user_id)
        if len(family_ids) > 1:
            results = results.filter(Transaction.user_id.in_(family_ids))
        else:
            results = results.filter(Transaction.user_id == user_id)
            
    results = results.group_by('tx_date', Transaction.type).all()
    
    # Initialize daily totals
    daily_stats = {}
    for i in range(days):
        day = (now - timedelta(days=i)).date()
        daily_stats[day] = {"income": 0, "expense": 0, "saving": 0}
    
    # 2. Map Results to Stats
    for tx_date, tx_type, total in results:
        if tx_date in daily_stats:
            val = float(total or 0)
            if tx_type == TransactionType.INCOME:
                daily_stats[tx_date]["income"] += val
            elif tx_type == TransactionType.EXPENSE:
                daily_stats[tx_date]["expense"] += val
            elif tx_type == TransactionType.SAVING:
                daily_stats[tx_date]["saving"] += val
    
    # Convert to list format (oldest first)
    result = []
    for i in range(days - 1, -1, -1):
        day = (now - timedelta(days=i)).date()
        day_name = day.strftime('%a')  # Mon, Tue, etc.
        result.append({
            "day": day_name,
            "income": daily_stats[day]["income"],
            "expense": daily_stats[day]["expense"],
            "saving": daily_stats[day]["saving"]
        })
    
    return result

