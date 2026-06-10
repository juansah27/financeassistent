from app.db.session import engine
import sqlalchemy

def fix_schema():
    with engine.connect() as conn:
        try:
            conn.execute(sqlalchemy.text("ALTER TABLE transaction_keywords ADD COLUMN category VARCHAR"))
            conn.commit()
            print("Successfully added 'category' column to 'transaction_keywords' table.")
        except Exception as e:
            print(f"Error adding column: {e}")

if __name__ == "__main__":
    fix_schema()
