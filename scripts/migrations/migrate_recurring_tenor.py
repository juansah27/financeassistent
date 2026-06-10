import sys
import os
from sqlalchemy import text

# Add root directory to path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import session

def migrate():
    print("Starting migration...")
    with session.engine.connect() as connection:
        # 1. Add remaining_occurrences column
        try:
            print("Adding remaining_occurrences column...")
            connection.execute(text("ALTER TABLE recurring_transactions ADD COLUMN IF NOT EXISTS remaining_occurrences INTEGER NULL"))
            print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")

        # 2. Drop Debt tables
        try:
            print("Dropping debt_payments table...")
            connection.execute(text("DROP TABLE IF EXISTS debt_payments CASCADE"))
            print("debt_payments dropped.")
            
            print("Dropping debts table...")
            connection.execute(text("DROP TABLE IF EXISTS debts CASCADE"))
            print("debts dropped.")
        except Exception as e:
            print(f"Error dropping tables: {e}")

        # 3. Drop Debt Enums (Postgres specific usually)
        try:
            print("Dropping enum types...")
            # Note: The enum name in Postgres is usually the lowercase of the python Enum name or explicit name
            # Checking models.py, it was likely 'debttype' and 'debtstatus'
            connection.execute(text("DROP TYPE IF EXISTS debttype"))
            connection.execute(text("DROP TYPE IF EXISTS debtstatus"))
            print("Enums dropped.")
        except Exception as e:
            print(f"Error dropping enums (might be fine if not using Postgres types): {e}")
            
        connection.commit()
    print("Migration finished.")

if __name__ == "__main__":
    migrate()
