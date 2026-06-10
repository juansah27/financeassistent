import sys
import os
from datetime import datetime, timedelta
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import session, models
from app.services.financial_qna import FinancialQnAService
from app.db.models import Transaction, TransactionType

def run_test():
    db = session.SessionLocal()
    try:
        print("="*60)
        print("🧪 Testing Date Parsing")
        print("="*60)
        
        # Mock user
        service = FinancialQnAService(db, 999) # Dummy user ID
        
        test_cases = [
            ("Pengeluaran bulan lalu", "Bulan Lalu"),
            ("Pengeluaran januari 2025", "Januari 2025"),
            ("Pengeluaran 26 januari sampai 31 januari", "26 Januari - 31 Januari"),
            ("Pengeluaran 1 feb - 10 feb", "1 Februari - 10 Februari"),
            ("Pengeluaran minggu ini", "Minggu Ini")
        ]
        
        for question, expected_label in test_cases:
            print(f"\n❓ Question: '{question}'")
            start, end, label = service._parse_period(question.lower())
            
            if start and end:
                print(f"✅ Parsed: {start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')} ({label})")
                if expected_label in label:
                     print("   Match Expected Label: OK")
                else:
                     print(f"   Match Expected Label: FAIL (Got {label})")
            else:
                print("❌ Failed to parse")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
