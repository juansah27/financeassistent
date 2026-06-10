from app.db import session, models
from app.auth import auth

db = session.SessionLocal()

try:
    # First, list all categories to see what exists
    print("ALL CATEGORIES IN DATABASE:")
    categories = db.query(models.UserCategory).all()
    for c in categories:
        print(f"ID: {c.id}, Name: {c.name}, Type: {c.type}, UserID: {c.user_id}, Active: {c.is_active}")

    print("\nSEARCHING FOR 'ROKOK':")
    rokok = db.query(models.UserCategory).filter(models.UserCategory.name.ilike("%rokok%")).all()
    if rokok:
        for r in rokok:
            print(f"FOUND: ID: {r.id}, Name: {r.name}, Type: {r.type}, UserID: {r.user_id}, Active: {r.is_active}")
    else:
        print("Category 'Rokok' NOT FOUND in database.")

finally:
    db.close()
