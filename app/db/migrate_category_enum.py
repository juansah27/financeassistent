"""
Migration script to update PostgreSQL category enum type with new values
"""
from sqlalchemy import text
from app.db.session import engine

def migrate_category_enum():
    """Add new category enum values to PostgreSQL enum type"""
    with engine.connect() as conn:
        # New category values that need to be added
        new_categories = [
            "GAJI",
            "USAHA", 
            "BONUS",
            "DANA_DARURAT",
            "PENDIDIKAN",
            "SAHAM",
            "EMAS",
            "CICILAN_RUMAH",
            "KREDIT"
        ]
        
        try:
            # Check which values already exist
            existing_result = conn.execute(text("""
                SELECT unnest(enum_range(NULL::category)) AS category_value;
            """))
            existing_values = {row[0] for row in existing_result}
            
            print(f"Existing enum values: {sorted(existing_values)}")
            
            # Add new values that don't exist yet
            for category in new_categories:
                if category not in existing_values:
                    try:
                        # Use IF NOT EXISTS pattern - check first
                        conn.execute(text(f"""
                            DO $$ 
                            BEGIN
                                IF NOT EXISTS (
                                    SELECT 1 FROM pg_enum 
                                    WHERE enumlabel = '{category}' 
                                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'category')
                                ) THEN
                                    ALTER TYPE category ADD VALUE '{category}';
                                END IF;
                            END $$;
                        """))
                        print(f"✓ Added enum value: {category}")
                        existing_values.add(category)  # Track it so we don't try again
                    except Exception as e:
                        # Try alternative syntax (some PostgreSQL versions)
                        try:
                            conn.execute(text(f"ALTER TYPE category ADD VALUE IF NOT EXISTS '{category}';"))
                            print(f"✓ Added enum value: {category}")
                            existing_values.add(category)
                        except Exception as e2:
                            print(f"⚠ Could not add {category}: {e2}")
            
            conn.commit()
            print("\n✅ Category enum migration completed!")
            
            # Show final enum values
            final_result = conn.execute(text("""
                SELECT unnest(enum_range(NULL::category)) AS category_value ORDER BY category_value;
            """))
            final_values = [row[0] for row in final_result]
            print(f"\nFinal enum values: {final_values}")
            
        except Exception as e:
            conn.rollback()
            print(f"Error during enum migration: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate_category_enum()


