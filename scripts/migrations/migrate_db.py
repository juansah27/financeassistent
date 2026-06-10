from sqlalchemy import text
from app.db.session import engine

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE user_preferences ADD COLUMN start_of_month INTEGER DEFAULT 1"))
            conn.commit()
            print("Migration successful: Added start_of_month column")
        except Exception as e:
            print(f"Migration failed (might already exist): {e}")

if __name__ == "__main__":
    migrate()
