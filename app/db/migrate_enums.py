"""
Migration script to update TransactionType and Category enums
Run this once to update database schema
"""
from sqlalchemy import text
from app.db.session import engine

def migrate_enums():
    """Update enum values in database (they're stored as VARCHAR, so this is safe)"""
    with engine.connect() as conn:
        # Map old category values to new ones (if needed)
        # Since categories changed significantly, we'll map old values to new ones
        
        try:
            # Update old transaction types to new enum values
            # "Pemasukan" stays "Pemasukan", "Pengeluaran" stays "Pengeluaran"
            # No changes needed for existing transaction types
            
            # Update old categories to new categories
            # Map old categories to new ones or "Lain-lain"
            conn.execute(text("""
                UPDATE transactions 
                SET category = 'Lain-lain'
                WHERE category NOT IN (
                    'Gaji', 'Usaha', 'Bonus', 'Makan', 'Transport', 'Tagihan', 'Hiburan',
                    'Dana Darurat', 'Pendidikan', 'Saham', 'Emas', 'Cicilan Rumah', 'Kredit', 'Lain-lain'
                );
            """))
            print("✓ Updated old categories to new schema")
        except Exception as e:
            print(f"Note: Category update might have issues: {e}")
        
        # Map specific old categories to new ones
        category_mapping = {
            'Pemasukan': 'Gaji',  # Default income category
            'Kebutuhan Bayi': 'Lain-lain',
            'Rumah Tangga': 'Lain-lain',
            'Tabungan': 'Dana Darurat',  # Map old Tabungan to new saving category
        }
        
        for old_cat, new_cat in category_mapping.items():
            try:
                conn.execute(text(f"""
                    UPDATE transactions 
                    SET category = :new_cat
                    WHERE category = :old_cat
                """), {"old_cat": old_cat, "new_cat": new_cat})
                print(f"✓ Mapped '{old_cat}' to '{new_cat}'")
            except Exception as e:
                print(f"Note: Could not map {old_cat}: {e}")
        
        conn.commit()
        print("\n✅ Enum migration completed!")
        print("\nNote: Transaction type enum values are stored as VARCHAR,")
        print("so new values (Saving, Investment, Debt) can be used immediately.")

if __name__ == "__main__":
    migrate_enums()


