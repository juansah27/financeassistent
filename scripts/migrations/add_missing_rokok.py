from app.db import session, models
from app.auth import auth

def add_rokok_category():
    db = session.SessionLocal()
    try:
        users = db.query(models.User).all()
        print(f"Found {len(users)} users.")

        for user in users:
            print(f"\nChecking for user: {user.username} (ID: {user.id})")
            
            # Check if Rokok exists
            exists = db.query(models.UserCategory).filter(
                models.UserCategory.user_id == user.id,
                models.UserCategory.name.ilike("Rokok"),
                models.UserCategory.is_active == True
            ).first()

            if exists:
                print(f"✅ Category 'Rokok' already exists for {user.username}.")
            else:
                print(f"❌ Category 'Rokok' NOT found for {user.username}. Creating...")
                
                new_cat = models.UserCategory(
                    user_id=user.id,
                    name="Rokok",
                    type="Pengeluaran",  # Assuming it's an expense
                    icon="cigarette",    # Lucide icon name if available, else generic
                    color="gray",
                    is_active=True,
                    is_default=False
                )
                db.add(new_cat)
                db.commit()
                print(f"✨ Created 'Rokok' category for {user.username}!")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_rokok_category()
