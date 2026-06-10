import sys
import os
from datetime import datetime, timedelta

# Add the project root to sys.path
sys.path.insert(0, r"d:\Project\financeassistent")

from app.db import session, crud, models, crud_extended

db = session.SessionLocal()

def test_period_logic(user_id, mock_now=None):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    pref = db.query(models.UserPreference).filter(models.UserPreference.user_id == user_id).first()
    start_day = pref.start_of_month if pref else 1
    
    print(f"Testing User: {u.username} (start_day={start_day})")
    
    # Original get_current_period logic (now in crud.py)
    year, month, sday = crud.get_current_period(db, user_id)
    print(f"  Current Period: {year}-{month}")
    
    # Check stats for this period
    stats = crud.get_monthly_stats(db, user_id, year, month)
    print(f"  Stats for {year}-{month}: Income={stats['income']}, Expense={stats['expenses']}")
    
    # Check budgets for this period
    budgets = crud_extended.get_budgets(db, user_id, year, month)
    print(f"  Budgets for {year}-{month}: {len(budgets)} entries")
    for b in budgets:
        print(f"    - {b.category}: {b.amount}")

user_id = 1
test_period_logic(user_id)

print("\nVerification Complete")
