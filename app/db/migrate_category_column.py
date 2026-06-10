"""
Migration script to update category column in transactions table
Changes from PostgreSQL ENUM to VARCHAR for flexibility
"""
from sqlalchemy import text
from app.db.session import engine

def migrate_category_column():
    """Convert category column from ENUM to VARCHAR"""
    with engine.connect() as conn:
        try:
            # Check current column type
            result = conn.execute(text("""
                SELECT data_type, udt_name 
                FROM information_schema.columns 
                WHERE table_name = 'transactions' AND column_name = 'category';
            """))
            col_info = result.fetchone()
            
            if col_info:
                data_type, udt_name = col_info
                print(f"Current category column type: {data_type} ({udt_name})")
                
                # If it's an ENUM (user-defined type), convert to VARCHAR
                if udt_name and udt_name not in ['varchar', 'text', 'character varying']:
                    print(f"\nConverting category column from ENUM ({udt_name}) to VARCHAR...")
                    
                    # Step 1: Add new VARCHAR column
                    conn.execute(text("""
                        ALTER TABLE transactions 
                        ADD COLUMN category_new VARCHAR;
                    """))
                    print("✓ Added temporary column category_new")
                    
                    # Step 2: Copy data from old column to new column
                    conn.execute(text("""
                        UPDATE transactions 
                        SET category_new = category::text;
                    """))
                    print("✓ Copied data to category_new")
                    
                    # Step 3: Drop old column
                    conn.execute(text("""
                        ALTER TABLE transactions 
                        DROP COLUMN category;
                    """))
                    print("✓ Dropped old category column")
                    
                    # Step 4: Rename new column to category
                    conn.execute(text("""
                        ALTER TABLE transactions 
                        RENAME COLUMN category_new TO category;
                    """))
                    print("✓ Renamed category_new to category")
                    
                    # Step 5: Add NOT NULL constraint if needed
                    # (We'll keep it nullable for safety, but you can add NOT NULL if needed)
                    
                    conn.commit()
                    print("\n✅ Category column successfully converted to VARCHAR!")
                    
                else:
                    print(f"\nCategory column is already {data_type} (not ENUM)")
                    print("No migration needed.")
            else:
                print("Category column not found!")
                
        except Exception as e:
            conn.rollback()
            print(f"Error during category column migration: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate_category_column()

