import sys
import os

# Add the project root to sys.path so we can import app modules
sys.path.insert(0, r"d:\Project\financeassistent")

from app.db import session, crud_extended, models

db = session.SessionLocal()

users = db.query(models.User).all()
for u in users:
    print(f"User: {u.id} - {u.username}")
    pref = db.query(models.UserPreference).filter(models.UserPreference.user_id == u.id).first()
    start_day = pref.start_of_month if pref else 1
    print(f"  Start day: {start_day}")
    
    budgets = db.query(models.Budget).filter(models.Budget.user_id == u.id).all()
    print("  Budgets:")
    for b in budgets:
        print(f"    - ID: {b.id}, Category: {b.category}, Year: {b.year}, Month: {b.month}, Amount: {b.amount}, Pct: {b.percentage}")

print("Done")
