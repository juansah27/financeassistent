import sys
import os
import time

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.db.session import engine
from app.db.models import Base, Category
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_categories():
    """
    Migrate database to support dynamic categories:
    1. Create user_categories table
    2. Convert existing Enum columns to VARCHAR
    3. Seed user_categories with default data
    """
    print("Starting migration...")
    
    # Check database type
    if 'sqlite' in str(engine.url):
        print("WARNING: SQLite detected. Full ALTER COLUMN not supported directly.")
        print("For SQLite, we will only create the new table and index.")
        # SQLite is loosely typed, so the Enum constraint (CHECK) might persist or be ignored.
        # We'll proceed with creating the new table.
    
    try:
        # 1. Create user_categories table
        print("Creating user_categories table...")
        Base.metadata.create_all(bind=engine)
        print("✓ Tables created/verified")
        
        with engine.connect() as conn:
            # Enable autocommit for valid transaction handling in some drivers
            if 'sqlite' not in str(engine.url):
                 conn = conn.execution_options(isolation_level="AUTOCOMMIT")

            # 2. Modify columns (Postgres specific mainly)
            if 'postgresql' in str(engine.url):
                print("Converting columns to VARCHAR (PostgreSQL)...")
                tables = ['transactions', 'budgets', 'recurring_transactions', 'recurring_income']
                
                for table in tables:
                    try:
                        # Check current type
                        result = conn.execute(text(f"""
                            SELECT data_type, udt_name 
                            FROM information_schema.columns 
                            WHERE table_name = '{table}' AND column_name = 'category';
                        """))
                        col_info = result.fetchone()
                        
                        if col_info and col_info[1] != 'varchar':
                            print(f"converting {table}.category (was {col_info[1]})...")
                            conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN category TYPE VARCHAR USING category::VARCHAR;"))
                            print(f"✓ {table}.category converted")
                        else:
                            print(f"- {table}.category is already {col_info[0] if col_info else 'unknown'}")
                            
                    except Exception as e:
                        print(f"Error altering {table}: {e}")
            
            # 3. Seed Data
            print("Seeding user categories...")
            # We need a transaction for inserts
            trans = conn.begin() if 'sqlite' in str(engine.url) else conn
            
            try:
                # Get users
                users = conn.execute(text("SELECT id FROM users")).fetchall()
                
                # Define defaults
                defaults = [
                    # INCOME
                    (Category.GAJI.value, 'Pemasukan', 'banknote', 'green'),
                    (Category.USAHA.value, 'Pemasukan', 'briefcase', 'blue'),
                    (Category.BONUS.value, 'Pemasukan', 'gift', 'yellow'),
                    ('Passive Income', 'Pemasukan', 'trending-up', 'green'),
                    ('Investasi', 'Pemasukan', 'bar-chart', 'purple'),
                    
                    # EXPENSE
                    (Category.KONSUMSI.value, 'Pengeluaran', 'coffee', 'orange'),
                    (Category.TRANSPORT.value, 'Pengeluaran', 'car', 'blue'),
                    (Category.UTILITAS.value, 'Pengeluaran', 'zap', 'yellow'),
                    (Category.HIBURAN.value, 'Pengeluaran', 'gamepad-2', 'purple'),
                    (Category.KESEHATAN.value, 'Pengeluaran', 'heart', 'red'),
                    (Category.RUMAH_TANGGA.value, 'Pengeluaran', 'home', 'cyan'),
                    (Category.PULSA.value, 'Pengeluaran', 'smartphone', 'indigo'),
                    (Category.DONASI.value, 'Pengeluaran', 'gift', 'pink'),
                    (Category.CICILAN_RUMAH.value, 'Pengeluaran', 'home', 'rose'),
                    (Category.KREDIT.value, 'Pengeluaran', 'credit-card', 'red'),
                    (Category.LAIN_LAIN.value, 'Pengeluaran', 'circle-help', 'gray'),
                    
                    # SAVING & INVEST
                    (Category.DANA_DARURAT.value, 'Tabungan', 'piggy-bank', 'emerald'),
                    (Category.PENDIDIKAN.value, 'Tabungan', 'graduation-cap', 'blue'),
                    (Category.SAHAM.value, 'Investasi', 'trending-up', 'green'),
                    (Category.EMAS.value, 'Investasi', 'coins', 'yellow'),
                ]
                
                count = 0
                for user in users:
                    user_id = user[0]
                    for name, type_, icon, color in defaults:
                         # Idempotency check
                        exists = conn.execute(text(
                            "SELECT 1 FROM user_categories WHERE user_id=:uid AND name=:name"
                        ), {"uid": user_id, "name": name}).fetchone()
                        
                        if not exists:
                            conn.execute(text("""
                                INSERT INTO user_categories (user_id, name, type, icon, color, is_default, is_active, created_at)
                                VALUES (:uid, :name, :type, :icon, :color, true, true, CURRENT_TIMESTAMP)
                            """), {"uid": user_id, "name": name, "type": type_, "icon": icon, "color": color})
                            count += 1
                
                if 'sqlite' in str(engine.url):
                    trans.commit()
                    
                print(f"✓ Seeded {count} categories for {len(users)} users")

            except Exception as e:
                if 'sqlite' in str(engine.url):
                    trans.rollback()
                print(f"Error seeding data: {e}")
                raise e

    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_categories()
