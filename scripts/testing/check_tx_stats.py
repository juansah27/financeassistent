import sys
import os
from datetime import datetime

# Add the project root to sys.path so we can import app modules
sys.path.insert(0, r"d:\Project\financeassistent")

from app.db import session, models

db = session.SessionLocal()

user_id = 1
u = db.query(models.User).filter(models.User.id == user_id).first()
print(f"User: {u.username}")

pref = db.query(models.UserPreference).filter(models.UserPreference.user_id == user_id).first()
start_day = pref.start_of_month if pref else 1
print(f"Start day: {start_day}")

txs = db.query(models.Transaction).filter(models.Transaction.user_id == user_id).order_by(models.Transaction.created_at.desc()).limit(20).all()
print("Recent Transactions:")
for t in txs:
    print(f"  - Date: {t.created_at}, Type: {t.type}, Category: {t.category}, Amount: {t.amount}")

# Check current period stats manually
now = datetime.now()
year = now.year
month = now.month
if start_day > 1 and now.day >= start_day:
    month += 1
    if month > 12:
        month = 1
        year += 1

print(f"Current Period for stats: {year}-{month}")

from app.db import crud
stats = crud.get_monthly_stats(db, user_id)
print(f"Stats: {stats}")
