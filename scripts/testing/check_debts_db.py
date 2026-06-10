import sys
import os

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.db.models import Debt, TransactionType

def check_debts():
    db = SessionLocal()
    try:
        print("--- Searching for 'Gaji' or 'Gajian' in Debts table ---")
        items = db.query(Debt).filter(Debt.creditor.ilike("%Gaji%")).all()
        for i in items:
            print(f"Debt ID: {i.id}, Creditor: {i.creditor}, Amount: {i.total_amount}")
            
        # search notes too
        items2 = db.query(Debt).filter(Debt.notes.ilike("%Gaji%")).all()
        for i in items2:
            print(f"Debt ID: {i.id}, Creditor: {i.creditor}, Notes: {i.notes}")
            
        print("\n--- All Active Debts ---")
        all_debts = db.query(Debt).filter(Debt.is_active == True).all()
        for i in all_debts:
            print(f"ID: {i.id}, Creditor: {i.creditor}, Amount: {i.remaining_amount}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_debts()
