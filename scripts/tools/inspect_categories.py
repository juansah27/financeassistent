from app.db.session import SessionLocal
from app.db.models import UserCategory

def list_categories():
    db = SessionLocal()
    try:
        categories = db.query(UserCategory.name).distinct().all()
        print("Existing Categories:")
        for cat in categories:
            print(f"- {cat[0]}")
    finally:
        db.close()

if __name__ == "__main__":
    list_categories()
