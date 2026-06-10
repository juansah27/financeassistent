from app.db import session, crud, models
from app.db.models import TransactionType
from datetime import datetime

def test_deleted_filter():
    db = next(session.get_db())
    try:
        # 1. Get a user
        user = db.query(models.User).first()
        if not user:
            print("No user found.")
            return

        print(f"Testing for user: {user.username} (ID: {user.id})")

        # 2. Add a dummy transaction
        tx = crud.create_transaction(
            db, user_id=user.id,
            transaction_type=TransactionType.EXPENSE,
            amount=999999,
            category="Test",
            description="Verification Phase 1",
            raw_input="test 999999"
        )
        print(f"Created transaction ID: {tx.id}, Amount: {tx.amount}")

        # 3. Check stats (should include it)
        stats = crud.get_monthly_stats(db, user.id)
        print(f"Stats after creation (Expenses): {stats['expenses']}")
        
        if stats['expenses'] < 999999:
             print("ERROR: Transaction not found in stats.")
             return

        # 4. Soft delete
        from app.db.crud_new_features import delete_transaction
        delete_transaction(db, tx.id, user.id)
        print(f"Soft deleted transaction {tx.id}")

        # 5. Check stats again (should NOT include it)
        stats_after = crud.get_monthly_stats(db, user.id)
        print(f"Stats after deletion (Expenses): {stats_after['expenses']}")

        if stats_after['expenses'] == stats['expenses']:
            print("❌ FAILED: Deleted transaction is still counted in stats!")
        else:
            print("✅ SUCCESS: Deleted transaction is correctly excluded from stats.")

        # Cleanup: Actually delete from DB to keep it clean
        db.delete(tx)
        db.commit()
        print("Cleanup done.")

    finally:
        db.close()

if __name__ == "__main__":
    test_deleted_filter()
