import sys
import os
from datetime import datetime
# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import session, models
from app.services.financial_qna import FinancialQnAService

def run_test():
    db = session.SessionLocal()
    try:
        print("="*60)
        print("🧪 Reproducing Crash")
        print("="*60)
        
        service = FinancialQnAService(db, 999) 
        
        crash_cases = [
            "pengeluaran 26 january - 27 january",
            "pengeluaran 26 january sampai 27 january",
            "26 januari sampai 31 januari"
        ]
        
        for q in crash_cases:
            print(f"\nProcessing: '{q}'")
            try:
                # 1. Test Parse Period
                start, end, label = service._parse_period(q.lower())
                print(f"Parsed: {start}, {end}, {label}")
                
                # 2. Test Process Question
                ans = service.process_question(q)
                print(f"Answer: {ans[:50]}...")
            except Exception as e:
                print(f"❌ CRASHED: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Setup Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
