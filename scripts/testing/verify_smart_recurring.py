import sys
import os
from datetime import datetime, timedelta, timezone

# Add app to path
sys.path.append(os.getcwd())

from app.db import session, crud_extended, models
from app.services import smart_recurring

def verify():
    db = next(session.get_db())
    print("🚀 Starting Smart Recurring Verification")
    
    # 1. Setup Data
    user = db.query(models.User).first()
    if not user:
        print("❌ No user found")
        return

    print(f"User found: {user.username}")
    
    # Create Recurrence
    test_recur_name = "Test Netflix Subscription"
    initial_due_date = datetime.now(timezone.utc) + timedelta(days=5) # Due is future
    
    recur = models.RecurringTransaction(
        user_id=user.id,
        type=models.TransactionType.EXPENSE,
        amount=100000,
        category="Entertainment",
        description=test_recur_name,
        recurrence_type=models.RecurrenceType.MONTHLY,
        day_of_month=initial_due_date.day,
        next_due_date=initial_due_date,
        is_active=True
    )
    db.add(recur)
    db.commit()
    db.refresh(recur)
    print(f"✅ Created Mock Recurring: {recur.description} (Due: {recur.next_due_date})")

    try:
        # 2. Test Smart Match
        print("\nTesting Smart Match...")
        # Exact match
        match1 = smart_recurring.find_recurring_match(db, user.id, "#bayar Test Netflix Subscription 100k", 100000)
        assert match1 and match1.id == recur.id, "Exact match failed"
        print("✅ Exact match found")

        # Fuzzy match
        match2 = smart_recurring.find_recurring_match(db, user.id, "#bayar Netflix 100k", 100000)
        assert match2 and match2.id == recur.id, "Fuzzy match failed"
        print("✅ Fuzzy match found")
        
        # 3. Test Confirmation Flow
        print("\nTesting Confirmation...")
        # Create Pending
        pending = smart_recurring.create_pending_confirmation(db, user.id, transaction_id=None, recurring_id=recur.id)
        assert pending.id, "Pending confirmation creation failed"
        print(f"✅ Pending confirmation created ID: {pending.id}")
        
        # Confirm
        expected_next_due = initial_due_date + timedelta(days=30) # Approx
        success, msg = smart_recurring.confirm_recurring_update(db, pending.id)
        assert success, f"Confirmation failed: {msg}"
        print(f"✅ Confirmation executed: {msg}")
        
        # Verify Update
        db.refresh(recur)
        print(f"Updated Next Due: {recur.next_due_date}")
        assert recur.next_due_date > initial_due_date, "Next due date did not advance"
        assert recur.last_paid_at is not None, "Last paid at not set"
        print("✅ Recursive schedule updated successfully!")

    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\nCleaning up...")
        db.delete(recur)
        db.commit()
        print("✅ Cleanup done")

if __name__ == "__main__":
    verify()
