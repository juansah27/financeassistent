import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db import session

def add_custom_enum_value():
    """Manual migration to add 'CUSTOM' to recurrencetype enum"""
    db = next(session.get_db())
    try:
        print("Adding 'CUSTOM' to 'recurrencetype' enum...")
        # Postgres specific command to add value to enum
        # We use a transaction because ALTER TYPE cannot run inside a transaction block 
        # normally, but with SQLAlchemy execute it might be wrapped.
        # However, ADD VALUE must be committed immediately.
        
        # Check if value exists manually or just try adding it (Postgres 9.1+ supports IF NOT EXISTS for some things but not always for enum values in older versions easily)
        # Safe way: try execute and catch error if exists
        
        try:
            db.execute(text("ALTER TYPE recurrencetype ADD VALUE 'CUSTOM';"))
            db.commit()
            print("Enum value 'CUSTOM' added successfully!")
        except Exception as e:
            if "duplicate value" in str(e) or "already exists" in str(e):
                print("Enum value 'CUSTOM' already exists.")
            else:
                raise e
        
    except Exception as e:
        print(f"Error adding enum value: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_custom_enum_value()
