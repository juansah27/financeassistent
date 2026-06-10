import sys
import os

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.db.models import RecurringTransaction, RecurringIncome, TransactionType

def check_gaji():
    db = SessionLocal()
    try:
        print("--- Searching for 'Gaji' ---")
        items = db.query(RecurringTransaction).filter(RecurringTransaction.description.ilike("%Gaji%")).all()
        for i in items:
            print(f"RT ID: {i.id}, Desc: {i.description}, Type: {i.type}")
        
        incomes = db.query(RecurringIncome).filter(RecurringIncome.name.ilike("%Gaji%")).all()
        for i in incomes:
            print(f"RI ID: {i.id}, Name: {i.name}, Status: {i.status}")
            
        print("\n--- Searching for 'Income' Type in RecurringTransaction ---")
        income_trans = db.query(RecurringTransaction).filter(RecurringTransaction.type == TransactionType.INCOME).all()
        for i in income_trans:
            print(f"RT ID: {i.id}, Desc: {i.description}, Type: {i.type}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_gaji()
