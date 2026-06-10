import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db import session

def add_interval_days_column():
    """Manual migration to add interval_days column"""
    db = next(session.get_db())
    try:
        print("Checking if column exists...")
        # Check if column exists first to avoid error
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='recurring_transactions' AND column_name='interval_days';
        """)
        result = db.execute(check_query).scalar()
        
        if result:
            print("Column 'interval_days' already exists.")
            return

        print("Adding 'interval_days' column to 'recurring_transactions' table...")
        db.execute(text("ALTER TABLE recurring_transactions ADD COLUMN interval_days INTEGER;"))
        db.commit()
        print("Column added successfully!")
        
    except Exception as e:
        print(f"Error adding column: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_interval_days_column()
