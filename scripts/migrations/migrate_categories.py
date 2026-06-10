"""
Database migration script to update old category values to new ones
- MAKAN -> KONSUMSI
- TAGIHAN -> UTILITAS

Run this script once to migrate existing data.
"""
import psycopg2
import os

def migrate_categories():
    """Migrate old category values to new ones"""
    
    # Database connection from environment
    db_host = os.getenv("DATABASE_HOST", "db")
    db_port = os.getenv("DATABASE_PORT", "5432")
    db_name = os.getenv("DB_NAME", "finance_db")
    db_user = os.getenv("DB_USER", "finance_user")
    db_password = os.getenv("DB_PASSWORD", "finance_pass")
    
    print("🔄 Starting category migration...")
    print(f"📡 Connecting to PostgreSQL at {db_host}:{db_port}/{db_name}...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        cursor = conn.cursor()
        
        print("✅ Connected to database successfully!")
        
        # Update MAKAN to KONSUMSI in transactions
        cursor.execute("UPDATE transactions SET category = 'KONSUMSI' WHERE category = 'MAKAN'")
        makan_count = cursor.rowcount
        print(f"✅ Updated {makan_count} transactions: MAKAN → KONSUMSI")
        
        # Update TAGIHAN to UTILITAS in transactions
        cursor.execute("UPDATE transactions SET category = 'UTILITAS' WHERE category = 'TAGIHAN'")
        tagihan_count = cursor.rowcount
        print(f"✅ Updated {tagihan_count} transactions: TAGIHAN → UTILITAS")
        
        # Commit transaction updates
        conn.commit()
        print("✅ Transaction updates committed!")
        
        # Try to update budgets table separately (don't fail if error)
        try:
            cursor.execute("UPDATE budgets SET category = 'KONSUMSI' WHERE category = 'MAKAN'")
            budget_makan_count = cursor.rowcount
            
            cursor.execute("UPDATE budgets SET category = 'UTILITAS' WHERE category = 'TAGIHAN'")
            budget_tagihan_count = cursor.rowcount
            
            conn.commit()
            print(f"✅ Updated {budget_makan_count} budgets: MAKAN → KONSUMSI")
            print(f"✅ Updated {budget_tagihan_count} budgets: TAGIHAN → UTILITAS")
        except psycopg2.Error as e:
            print(f"⚠️ Budgets table update skipped (error: {str(e).split(chr(10))[0]})")
            conn.rollback()  # Rollback only budget changes
        
        # Verify changes
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE category IN ('MAKAN', 'TAGIHAN')")
        remaining = cursor.fetchone()[0]
        
        if remaining > 0:
            print(f"⚠️ Warning: {remaining} transactions still have old categories")
        else:
            print("✅ All old categories successfully migrated!")
        
        # Show summary of categories
        cursor.execute("SELECT category, COUNT(*) FROM transactions GROUP BY category ORDER BY COUNT(*) DESC")
        categories = cursor.fetchall()
        
        print("\n📊 Current category distribution:")
        for cat, count in categories:
            print(f"  {cat}: {count} transactions")
        
        cursor.close()
        conn.close()
        print("\n✅ Migration completed successfully!")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    migrate_categories()
