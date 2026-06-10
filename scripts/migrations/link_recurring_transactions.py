
import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.db.models import Transaction, RecurringTransaction, TransactionType

def link_recurring_transactions():
    db = SessionLocal()
    try:
        # Get active recurring rules
        recurring_rules = db.query(RecurringTransaction).filter(RecurringTransaction.is_active == True).all()
        print(f"Found {len(recurring_rules)} active recurring rules.")

        # Get expenses with no recurring_id
        expenses = db.query(Transaction).filter(
            Transaction.type == TransactionType.EXPENSE,
            Transaction.recurring_id == None
        ).all()
        
        print(f"Scanning {len(expenses)} manual expenses...")
        
        linked_count = 0
        
        for tx in expenses:
            matched_rule = None
            
            # 1. Exact Amount Match
            for rule in recurring_rules:
                if tx.amount == rule.amount:
                    matched_rule = rule
                    break
            
            # 2. Fuzzy Description Match (if no exact amount match)
            if not matched_rule and tx.description:
                tx_desc_lower = tx.description.lower()
                for rule in recurring_rules:
                    rule_desc_lower = rule.description.lower() if rule.description else ""
                    if rule_desc_lower and (rule_desc_lower in tx_desc_lower or tx_desc_lower in rule_desc_lower):
                        matched_rule = rule
                        break
            
            if matched_rule:
                print(f"[LINKED] Transaction '{tx.description}' ({tx.amount}) -> Rule '{matched_rule.description}' (ID: {matched_rule.id})")
                tx.recurring_id = matched_rule.id
                linked_count += 1
        
        if linked_count > 0:
            db.commit()
            print(f"\nSuccessfully linked {linked_count} transactions to their recurring rules.")
        else:
            print("\nNo matching transactions found to link.")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    link_recurring_transactions()
