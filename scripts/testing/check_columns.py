from app.db.session import engine
import sqlalchemy

def check_columns():
    with engine.connect() as conn:
        try:
            result = conn.execute(sqlalchemy.text(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'transaction_keywords'"
            ))
            print("\nColumns in 'transaction_keywords' table:")
            print("-" * 40)
            rows = result.fetchall()
            found = False
            for row in rows:
                print(f"- {row[0]} ({row[1]})")
                if row[0] == 'category':
                    found = True
            print("-" * 40)
            
            if found:
                print("\n✅ Column 'category' FOUND.")
            else:
                print("\n❌ Column 'category' NOT FOUND.")
                
        except Exception as e:
            print(f"Error checking columns: {e}")

if __name__ == "__main__":
    check_columns()
