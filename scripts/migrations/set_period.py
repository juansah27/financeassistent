from sqlalchemy import text
from app.db.session import engine

def set_period():
    with engine.connect() as conn:
        try:
            conn.execute(text("UPDATE user_preferences SET start_of_month = 25"))
            conn.commit()
            print("Updated all users start_of_month to 25")
        except Exception as e:
            print(f"Update failed: {e}")

if __name__ == "__main__":
    set_period()
