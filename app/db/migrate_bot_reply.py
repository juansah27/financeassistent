"""
Migration script to create bot_reply_templates table and populate default template
"""
from sqlalchemy import text
from app.db.session import engine

def migrate_bot_reply():
    """Create bot_reply_templates table and populate with default template"""
    with engine.connect() as conn:
        try:
            # Create table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bot_reply_templates (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    template TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_default BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                );
                
                CREATE INDEX IF NOT EXISTS idx_bot_reply_templates_active ON bot_reply_templates(is_active);
                CREATE INDEX IF NOT EXISTS idx_bot_reply_templates_default ON bot_reply_templates(is_default);
            """))
            print("✓ Created bot_reply_templates table")
            
            # Default template
            default_template = """✓ {type_label} berhasil ditambahkan!
Jumlah: {amount_formatted}
Kategori: {category}"""
            
            # Check if default template already exists
            result = conn.execute(text("""
                SELECT COUNT(*) FROM bot_reply_templates WHERE name = 'default'
            """))
            count = result.scalar()
            
            if count == 0:
                conn.execute(text("""
                    INSERT INTO bot_reply_templates (name, template, is_active, is_default)
                    VALUES ('default', :template, TRUE, TRUE)
                """), {"template": default_template})
                print("✓ Added default reply template")
            else:
                print("⚠ Default template already exists")
            
            conn.commit()
            print("\n✅ Bot reply templates migration completed!")
            
        except Exception as e:
            conn.rollback()
            print(f"Error during bot reply templates migration: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    migrate_bot_reply()

