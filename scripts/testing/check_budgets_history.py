import sys
import os

# Add the project root to sys.path
sys.path.insert(0, r"d:\Project\financeassistent")

from app.db import session, models

db = session.SessionLocal()

users = db.query(models.User).all()
for u in users:
    print(f"User: {u.username} (ID: {u.id})")
    budgets = db.query(models.Budget).filter(models.Budget.user_id == u.id).order_by(models.Budget.year.desc(), models.Budget.month.desc()).all()
    if not budgets:
        print("  No budgets found.")
    for b in budgets:
        print(f"  - {b.year}-{b.month}: {b.category} = {b.amount} (Pct: {b.percentage})")
    print("-" * 20)
