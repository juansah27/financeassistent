"""
Migration script to add new columns to existing tables
Run this once to update database schema
"""
from sqlalchemy import text
from app.db.session import engine

def migrate():
    """Add new columns to existing tables"""
    with engine.connect() as conn:
        # Check if columns exist before adding
        try:
            # Add recurring_id to transactions
            conn.execute(text("""
                ALTER TABLE transactions 
                ADD COLUMN IF NOT EXISTS recurring_id INTEGER 
                REFERENCES recurring_transactions(id)
            """))
            print("✓ Added recurring_id to transactions")
        except Exception as e:
            print(f"Note: recurring_id might already exist: {e}")
        
        # Create new tables if they don't exist
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    category VARCHAR NOT NULL,
                    amount FLOAT NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            print("✓ Created budgets table")
        except Exception as e:
            print(f"Note: budgets table might already exist: {e}")
        
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS goals (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name VARCHAR NOT NULL,
                    target_amount FLOAT NOT NULL,
                    current_amount FLOAT DEFAULT 0.0,
                    target_date TIMESTAMP WITH TIME ZONE,
                    is_achieved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            print("✓ Created goals table")
        except Exception as e:
            print(f"Note: goals table might already exist: {e}")
        
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS transaction_photos (
                    id SERIAL PRIMARY KEY,
                    transaction_id INTEGER NOT NULL,
                    filename VARCHAR NOT NULL,
                    file_path VARCHAR NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
                )
            """))
            print("✓ Created transaction_photos table")
        except Exception as e:
            print(f"Note: transaction_photos table might already exist: {e}")
        
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR NOT NULL,
                    message TEXT NOT NULL,
                    notification_type VARCHAR NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✓ Created notifications table")
        except Exception as e:
            print(f"Note: notifications table might already exist: {e}")
        
        # Add foreign key constraint if not exists
        try:
            conn.execute(text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'transactions_recurring_id_fkey'
                    ) THEN
                        ALTER TABLE transactions 
                        ADD CONSTRAINT transactions_recurring_id_fkey 
                        FOREIGN KEY (recurring_id) REFERENCES recurring_transactions(id);
                    END IF;
                END $$;
            """))
            print("✓ Added foreign key constraint for recurring_id")
        except Exception as e:
            print(f"Note: Foreign key might already exist: {e}")
        
        # Add new columns to transactions table
        try:
            conn.execute(text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='transactions' AND column_name='family_member_id'
                    ) THEN
                        ALTER TABLE transactions ADD COLUMN family_member_id INTEGER;
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='transactions' AND column_name='currency_code'
                    ) THEN
                        ALTER TABLE transactions ADD COLUMN currency_code VARCHAR(3) DEFAULT 'IDR';
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='transactions' AND column_name='amount_in_base_currency'
                    ) THEN
                        ALTER TABLE transactions ADD COLUMN amount_in_base_currency FLOAT;
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='transactions' AND column_name='notes'
                    ) THEN
                        ALTER TABLE transactions ADD COLUMN notes TEXT;
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='transactions' AND column_name='is_deleted'
                    ) THEN
                        ALTER TABLE transactions ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='transactions' AND column_name='deleted_at'
                    ) THEN
                        ALTER TABLE transactions ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
                    END IF;
                END $$;
            """))
            print("✓ Added new columns to transactions")
        except Exception as e:
            print(f"Note: Columns might already exist: {e}")
        
        # Create new tables
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS currencies (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(3) UNIQUE NOT NULL,
                    name VARCHAR NOT NULL,
                    symbol VARCHAR NOT NULL,
                    exchange_rate_to_base FLOAT DEFAULT 1.0,
                    is_base BOOLEAN DEFAULT FALSE,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            print("✓ Created currencies table")
        except Exception as e:
            print(f"Note: currencies table might already exist: {e}")
        
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS family_members (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name VARCHAR NOT NULL,
                    role VARCHAR,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✓ Created family_members table")
        except Exception as e:
            print(f"Note: family_members table might already exist: {e}")
        
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS transaction_edits (
                    id SERIAL PRIMARY KEY,
                    transaction_id INTEGER NOT NULL REFERENCES transactions(id),
                    edited_by_user_id INTEGER NOT NULL,
                    old_amount FLOAT,
                    new_amount FLOAT,
                    old_category VARCHAR,
                    new_category VARCHAR,
                    old_description VARCHAR,
                    new_description VARCHAR,
                    edit_reason VARCHAR,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✓ Created transaction_edits table")
        except Exception as e:
            print(f"Note: transaction_edits table might already exist: {e}")
        
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS receipt_ocr (
                    id SERIAL PRIMARY KEY,
                    transaction_id INTEGER NOT NULL REFERENCES transactions(id),
                    photo_id INTEGER NOT NULL REFERENCES transaction_photos(id),
                    extracted_text TEXT,
                    merchant_name VARCHAR,
                    total_amount FLOAT,
                    date_detected TIMESTAMP WITH TIME ZONE,
                    items TEXT,
                    confidence_score FLOAT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✓ Created receipt_ocr table")
        except Exception as e:
            print(f"Note: receipt_ocr table might already exist: {e}")
        
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER UNIQUE NOT NULL,
                    dark_mode BOOLEAN DEFAULT FALSE,
                    base_currency_code VARCHAR(3) DEFAULT 'IDR',
                    language VARCHAR(10) DEFAULT 'id',
                    date_format VARCHAR(20) DEFAULT 'DD/MM/YYYY',
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            print("✓ Created user_preferences table")
        except Exception as e:
            print(f"Note: user_preferences table might already exist: {e}")
        
        # Initialize default currencies
        try:
            conn.execute(text("""
                INSERT INTO currencies (code, name, symbol, exchange_rate_to_base, is_base)
                VALUES ('IDR', 'Indonesian Rupiah', 'Rp', 1.0, TRUE)
                ON CONFLICT (code) DO NOTHING;
            """))
            conn.execute(text("""
                INSERT INTO currencies (code, name, symbol, exchange_rate_to_base, is_base)
                VALUES ('USD', 'US Dollar', '$', 15000.0, FALSE)
                ON CONFLICT (code) DO NOTHING;
            """))
            print("✓ Initialized default currencies")
        except Exception as e:
            print(f"Note: Currencies might already exist: {e}")
        
        # Create assets tables
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS assets (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    asset_type VARCHAR NOT NULL,
                    name VARCHAR NOT NULL,
                    current_value FLOAT NOT NULL,
                    acquisition_date TIMESTAMP WITH TIME ZONE,
                    acquisition_value FLOAT,
                    quantity FLOAT,
                    unit VARCHAR(50),
                    notes TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            print("✓ Created assets table")
        except Exception as e:
            print(f"Note: assets table might already exist: {e}")
        
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS asset_history (
                    id SERIAL PRIMARY KEY,
                    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
                    old_value FLOAT NOT NULL,
                    new_value FLOAT NOT NULL,
                    updated_by_user_id INTEGER NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✓ Created asset_history table")
        except Exception as e:
            print(f"Note: asset_history table might already exist: {e}")
        
        conn.commit()
        print("\n✅ Migration completed!")


if __name__ == "__main__":
    migrate()

