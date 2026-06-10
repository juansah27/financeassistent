"""
Migration script to fix old category values in database
Updates old category 'PEMASUKAN' to new valid categories
"""
from sqlalchemy import text
from app.db.session import engine

def fix_old_categories():
    """Fix old category values in transactions table"""
    with engine.connect() as conn:
        try:
            # Check for old 'PEMASUKAN' category
            result = conn.execute(text("SELECT COUNT(*) FROM transactions WHERE category = 'PEMASUKAN'"))
            count = result.scalar()
            
            if count > 0:
                print(f"Found {count} transactions with old category 'PEMASUKAN'")
                print("Updating to 'GAJI' (default income category)...")
                
                # Update PEMASUKAN to GAJI (default income category)
                conn.execute(text("""
                    UPDATE transactions 
                    SET category = 'GAJI'
                    WHERE category = 'PEMASUKAN'
                """))
                print(f"✓ Updated {count} transactions from 'PEMASUKAN' to 'GAJI'")
            else:
                print("No transactions with old category 'PEMASUKAN' found")
            
            # Check for any other invalid categories
            # Skip validation against old Enum as we now support dynamic categories
            print("\nSkipping validation against defunct Category Enum.")
            
            conn.commit()
            print("\n✅ Category migration completed!")
            
        except Exception as e:
            conn.rollback()
            print(f"Error during category migration: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    fix_old_categories()

