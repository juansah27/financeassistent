"""
Migration script to create transaction_keywords table and populate initial keywords
"""
from sqlalchemy import text
from app.db.session import engine

def migrate_keywords():
    """Create transaction_keywords table and populate with initial keywords"""
    with engine.connect() as conn:
        try:
            # Create table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS transaction_keywords (
                    id SERIAL PRIMARY KEY,
                    keyword VARCHAR UNIQUE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                );
                
                CREATE INDEX IF NOT EXISTS idx_transaction_keywords_keyword ON transaction_keywords(keyword);
                CREATE INDEX IF NOT EXISTS idx_transaction_keywords_active ON transaction_keywords(is_active);
            """))
            print("✓ Created transaction_keywords table")
            
            # Initial keywords (same as in bot.js)
            initial_keywords = [
                'beli', 'bayar', 'terima', 'gaji', 'transfer', 
                'debit', 'kredit', 'ribu', 'juta', 'rb', 'jt',
                'pemasukan', 'pengeluaran', 'expense', 'income',
                'tabung', 'simpan', 'invest', 'cicil', 'hutang',
                'saham', 'emas', 'bonus', 'usaha', 'tagihan'
            ]
            
            # Insert initial keywords if they don't exist
            for keyword in initial_keywords:
                try:
                    conn.execute(text("""
                        INSERT INTO transaction_keywords (keyword, is_active)
                        VALUES (:keyword, TRUE)
                        ON CONFLICT (keyword) DO NOTHING
                    """), {"keyword": keyword})
                    print(f"✓ Added keyword: {keyword}")
                except Exception as e:
                    print(f"⚠ Could not add keyword {keyword}: {e}")
            
            conn.commit()
            print("\n✅ Keywords migration completed!")
            
        except Exception as e:
            conn.rollback()
            print(f"Error during keywords migration: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate_keywords()

