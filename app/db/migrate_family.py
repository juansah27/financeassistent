"""
Migration script to add Family Group support
"""
from sqlalchemy import text
from app.db.session import engine

def migrate_family():
    """Add families table and modify users table"""
    with engine.connect() as conn:
        print("Migrating Family Group Schema...")
        
        # 1. Create families table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS families (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    join_code VARCHAR(10) UNIQUE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✓ Created families table")
        except Exception as e:
            print(f"Error creating families table: {e}")
            
        # 2. Add family_id to users
        try:
            # Check if column exists first
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='family_id'
            """))
            
            if not result.fetchone():
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN family_id INTEGER REFERENCES families(id)
                """))
                print("✓ Added family_id to users table")
            else:
                print("Note: family_id column already exists in users table")
                
        except Exception as e:
            print(f"Error adding family_id column: {e}")
            
        conn.commit()
        print("\n✅ Family Migration completed!")

if __name__ == "__main__":
    migrate_family()
