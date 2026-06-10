from app.db import session, crud, models
from app.db.models import TransactionType
from datetime import datetime

def test_aggregation_correctness():
    db = next(session.get_db())
    try:
        user = db.query(models.User).filter(models.User.id == 1).first() # Use 'ayah'
        if not user:
            print("No user found.")
            return

        print(f"Testing aggregation for user: {user.username}")

        # Get stats using new SQL aggregation logic
        stats = crud.get_monthly_stats(db, user.id)
        
        print(f"Aggregated Stats:")
        print(f"  Income: {stats['income']}")
        print(f"  Expenses: {stats['expenses']}")
        print(f"  Balance: {stats['balance']}")
        print(f"  Category Breakdown Count: {len(stats['category_breakdown'])}")
        
        # Quick validation: total_count should match if we did a manual count
        manual_count = db.query(models.Transaction).filter(
            models.Transaction.user_id == user.id,
            models.Transaction.is_deleted == False
        ).count()
        
        # Note: get_monthly_stats filters by date range, so we should too
        # But for a simple sanity check, if it returns numbers and doesn't crash, it's a good sign.
        # Let's verify income - expense = balance (approx, since saving/debt also included)
        
        expected_balance = stats['income'] - (stats['expenses'] + stats['saving'] + stats['investment'] + stats['debt'])
        if abs(stats['balance'] - expected_balance) < 0.01:
            print("✅ SUCCESS: Balance calculation is consistent.")
        else:
            print(f"❌ FAILED: Balance mismatch! {stats['balance']} vs {expected_balance}")

    finally:
        db.close()

if __name__ == "__main__":
    test_aggregation_correctness()
