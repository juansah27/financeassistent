from sqlalchemy import text
from app.db.session import engine

def migrate():
    print("🚀 Starting Manual Migration")
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Add last_paid_at to recurring_transactions
            try:
                print("Checking recurring_transactions.last_paid_at...")
                conn.execute(text("ALTER TABLE recurring_transactions ADD COLUMN last_paid_at TIMESTAMPTZ;"))
                print("✅ Added column last_paid_at to recurring_transactions")
            except Exception as e:
                if "already exists" in str(e):
                    print("ℹ️ Column last_paid_at already exists")
                else:
                    print(f"⚠️ Error adding column: {e}")

            # 2. Create pending_confirmations (if not exists)
            # SQLAlchemy create_all usually handles this, but forcing it here just in case,
            # or relying on app restart. But let's verify connectivity first.
            try:
                conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pending_confirmations (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    transaction_id INTEGER,
                    recurring_id INTEGER NOT NULL,
                    action_type VARCHAR NOT NULL DEFAULT 'update_recurring',
                    data TEXT,
                    expires_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
                """))
                print("✅ Checked/Created pending_confirmations table")
                
                # Index
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pending_confirmations_user_id ON pending_confirmations (user_id);"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_pending_confirmations_id ON pending_confirmations (id);"))
                
            except Exception as e:
                 print(f"⚠️ Error creating table: {e}")

            trans.commit()
            print("✅ Migration Completed")
        except Exception as e:
            trans.rollback()
            print(f"❌ Migration Failed: {e}")

if __name__ == "__main__":
    migrate()
