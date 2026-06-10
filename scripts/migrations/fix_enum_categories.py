"""
Fix PostgreSQL ENUM type by adding new category values

PostgreSQL ENUMs are strict and need explicit additions of new values.
This script adds the new categories to the existing enum type.
"""
import psycopg2
import os

def fix_enum_categories():
    """Add new category values to PostgreSQL ENUM type"""
    
    # Database connection from environment
    db_host = os.getenv("DATABASE_HOST", "db")
    db_port = os.getenv("DATABASE_PORT", "5432")
    db_name = os.getenv("DB_NAME", "finance_db")
    db_user = os.getenv("DB_USER", "finance_user")
    db_password = os.getenv("DB_PASSWORD", "finance_pass")
    
    print("🔄 Starting PostgreSQL ENUM fix...")
    print(f"📡 Connecting to PostgreSQL at {db_host}:{db_port}/{db_name}...")
    
    # New categories to add
    new_categories = [
        'KONSUMSI',      # Renamed from MAKAN
        'UTILITAS',      # Renamed from TAGIHAN
        'KESEHATAN',     # New
        'RUMAH_TANGGA',  # New
        'PULSA',         # New
        'DONASI'         # New
    ]
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        conn.autocommit = True  # ENUM alterations require autocommit
        cursor = conn.cursor()
        
        print("✅ Connected to database successfully!")
        
        # Check current enum values
        cursor.execute("""
            SELECT e.enumlabel 
            FROM pg_type t 
            JOIN pg_enum e ON t.oid = e.enumtypid 
            WHERE t.typname = 'category'
            ORDER BY e.enumsortorder;
        """)
        current_values = [row[0] for row in cursor.fetchall()]
        print(f"\n📋 Current enum values: {', '.join(current_values)}")
        
        # Add new enum values if they don't exist
        added_count = 0
        for category in new_categories:
            if category not in current_values:
                try:
                    cursor.execute(f"ALTER TYPE category ADD VALUE '{category}'")
                    print(f"✅ Added enum value: {category}")
                    added_count += 1
                except psycopg2.Error as e:
                    if "already exists" in str(e):
                        print(f"⚠️ Skipped {category}: already exists")
                    else:
                        raise
            else:
                print(f"⏭️ Skipped {category}: already exists")
        
        # Verify final enum values
        cursor.execute("""
            SELECT e.enumlabel 
            FROM pg_type t 
            JOIN pg_enum e ON t.oid = e.enumtypid 
            WHERE t.typname = 'category'
            ORDER BY e.enumsortorder;
        """)
        final_values = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📊 Final enum values ({len(final_values)} total):")
        for val in final_values:
            print(f"  • {val}")
        
        cursor.close()
        conn.close()
        
        print(f"\n✅ ENUM fix completed! Added {added_count} new values.")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if 'conn' in locals():
            conn.close()
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    fix_enum_categories()
