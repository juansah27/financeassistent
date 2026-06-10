import sys
import os
from datetime import datetime, timedelta
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import session, models
from app.services.financial_qna import FinancialQnAService
from app.db.models import Transaction, TransactionType, RecurringTransaction, RecurringIncome, RecurrenceType, RecurringIncomeStatus

def run_test():
    db = session.SessionLocal()
    try:
        print("="*60)
        print("🧪 Testing Financial QnA Service")
        print("="*60)

        # 1. Create Test User
        print("\nCreating Test User...")
        test_user = models.User(username="test_qna_user", pin_hash="dummy")
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        user_id = test_user.id
        print(f"User created with ID: {user_id}")
        
        # 2. Add Dummy Data
        print("Adding dummy transactions...")
        
        # Income: 10,000,000
        t_inc = Transaction(
            user_id=user_id,
            type=TransactionType.INCOME,
            amount=10000000,
            category="Gaji",
            description="Gaji Bulanan",
            created_at=datetime.now()
        )
        db.add(t_inc)
        
        # Expense: 5,000,000
        t_exp = Transaction(
            user_id=user_id,
            type=TransactionType.EXPENSE,
            amount=5000000,
            category="Makan",
            description="Makan sebulan",
            created_at=datetime.now()
        )
        db.add(t_exp)
        
        # Next Month Recurring Bill: 2,000,000
        next_month = datetime.now() + timedelta(days=32)
        r_bill = RecurringTransaction(
            user_id=user_id,
            type=TransactionType.EXPENSE,
            amount=2000000,
            category="Listrik",
            recurrence_type=RecurrenceType.MONTHLY,
            next_due_date=next_month,
            is_active=True
        )
        db.add(r_bill)
        
        # Recurring Income: 10,000,000
        r_inc = RecurringIncome(
            user_id=user_id,
            name="Gaji",
            amount=10000000,
            category="Gaji",
            status=RecurringIncomeStatus.ACTIVE
        )
        db.add(r_inc)
        
        db.commit()
        
        # 3. Test Service
        service = FinancialQnAService(db, user_id)
        
        print("\n" + "-"*30)
        print("Test 1: Cek Saldo")
        print("-" * 30)
        print(service.process_question("cek saldo"))
        
        print("\n" + "-"*30)
        print("Test 2: Cek Tagihan Bulan Depan")
        print("-" * 30)
        print(service.process_question("ada tagihan apa bulan depan"))
        
        print("\n" + "-"*30)
        print("Test 3: Analisa Pengeluaran")
        print("-" * 30)
        print(service.process_question("analisa pengeluaran bulan ini"))
        
        print("\n" + "-"*30)
        print("Test 4: Analisa Boros (Top Kategori)")
        print("-" * 30)
        print(service.process_question("apa yang paling boros"))
        
        # 4. Clean up
        print("\nCleaning up test data...")
        db.query(Transaction).filter(Transaction.user_id == user_id).delete()
        db.query(RecurringTransaction).filter(RecurringTransaction.user_id == user_id).delete()
        db.query(RecurringIncome).filter(RecurringIncome.user_id == user_id).delete()
        db.delete(test_user)
        db.commit()
        print("Cleanup complete.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
