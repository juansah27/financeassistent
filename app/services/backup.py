"""
Backup and restore functionality
"""
import json
import csv
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.db import models, crud, crud_extended
from app.db.models import Transaction, TransactionType

BACKUP_DIR = Path("app/static/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def export_transactions_csv(db: Session, user_id: int, filepath: str = None):
    """Export all transactions to CSV"""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.is_deleted == False
    ).order_by(Transaction.created_at.desc()).all()
    
    if not filepath:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = BACKUP_DIR / f"transactions_{user_id}_{timestamp}.csv"
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'ID', 'Tanggal', 'Tipe', 'Kategori', 'Jumlah', 
            'Deskripsi', 'Currency', 'Family Member', 'Notes'
        ])
        
        for t in transactions:
            writer.writerow([
                t.id,
                t.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                t.type.value,
                t.category,
                t.amount,
                t.description or t.raw_input or "",
                t.currency_code or "IDR",
                "",  # family member name would need join
                t.notes or ""
            ])
    
    return filepath

def export_full_backup(db: Session, user_id: int):
    """Export full backup (JSON format)"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = BACKUP_DIR / f"backup_{user_id}_{timestamp}.json"
    
    backup_data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "user_id": user_id,
        "transactions": [],
        "budgets": [],
        "goals": [],
        "recurring": [],
        "family_members": []
    }
    
    # Export transactions
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.is_deleted == False
    ).all()
    
    for t in transactions:
        backup_data["transactions"].append({
            "id": t.id,
            "type": t.type.value,
            "amount": t.amount,
            "category": t.category,
            "description": t.description,
            "raw_input": t.raw_input,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "currency_code": t.currency_code,
            "notes": t.notes
        })
    
    # Export budgets
    budgets = crud_extended.get_budgets(db, user_id)
    for b in budgets:
        backup_data["budgets"].append({
            "category": b.category,
            "amount": b.amount,
            "year": b.year,
            "month": b.month
        })
    
    # Export goals
    goals = crud_extended.get_goals(db, user_id)
    for g in goals:
        backup_data["goals"].append({
            "name": g.name,
            "target_amount": g.target_amount,
            "current_amount": g.current_amount,
            "target_date": g.target_date.isoformat() if g.target_date else None
        })
    
    # Export recurring
    recurring = crud_extended.get_recurring_transactions(db, user_id)
    for r in recurring:
        backup_data["recurring"].append({
            "type": r.type.value,
            "amount": r.amount,
            "category": r.category,
            "description": r.description,
            "recurrence_type": r.recurrence_type.value,
            "next_due_date": r.next_due_date.isoformat() if r.next_due_date else None
        })
    
    # Export family members
    from app.db import crud_new_features
    members = crud_new_features.get_family_members(db, user_id)
    for m in members:
        backup_data["family_members"].append({
            "name": m.name,
            "role": m.role
        })
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    return filepath

def import_backup(db: Session, user_id: int, filepath: str):
    """Import backup from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    imported_count = {
        "transactions": 0,
        "budgets": 0,
        "goals": 0,
        "recurring": 0,
        "family_members": 0
    }
    
    # Import transactions
    for t_data in backup_data.get("transactions", []):
        try:
            from app.db.models import TransactionType
            transaction_type = TransactionType.INCOME if t_data["type"] == "Pemasukan" else TransactionType.EXPENSE
            category = t_data["category"]
            
            crud.create_transaction(
                db, user_id, transaction_type,
                t_data["amount"], category,
                t_data.get("description"), t_data.get("raw_input"),
                tags=t_data.get("tags")
            )
            imported_count["transactions"] += 1
        except Exception as e:
            print(f"Error importing transaction: {e}")
    
    # Import other data similarly...
    
    return imported_count

