"""
Script to count categories in the database
"""
from app.db.session import SessionLocal
from app.db import models

def count_categories():
    """Count distinct categories from transaction_keywords table"""
    db = SessionLocal()
    try:
        # Get all distinct categories from transaction_keywords
        categories = db.query(models.TransactionKeyword.category).filter(
            models.TransactionKeyword.category.isnot(None),
            models.TransactionKeyword.is_active == True
        ).distinct().all()
        
        category_list = sorted([cat[0] for cat in categories if cat[0]])
        
        print(f"\n=== KATEGORI TRANSAKSI DI DATABASE ===\n")
        print(f"Total Kategori: {len(category_list)}\n")
        print("Daftar Kategori:")
        for i, category in enumerate(category_list, 1):
            print(f"{i}. {category}")
        
        # Also check user categories
        print(f"\n\n=== USER CATEGORIES ===\n")
        user_categories = db.query(models.UserCategory).filter(
            models.UserCategory.is_active == True
        ).all()
        
        if user_categories:
            print(f"Total User Categories: {len(user_categories)}\n")
            for uc in user_categories:
                print(f"- {uc.name} (Type: {uc.type}, Default: {uc.is_default})")
        else:
            print("Tidak ada user categories")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    count_categories()
