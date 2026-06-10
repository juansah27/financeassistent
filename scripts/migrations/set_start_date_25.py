from app.db import session, models

def update_start_date():
    db = session.SessionLocal()
    try:
        # Get all users
        users = db.query(models.User).all()
        print(f"Found {len(users)} users.")
        
        for user in users:
            pref = db.query(models.UserPreference).filter(models.UserPreference.user_id == user.id).first()
            if not pref:
                print(f"Creating preferences for {user.username}...")
                pref = models.UserPreference(user_id=user.id)
                db.add(pref)
            
            print(f"Updating start_of_month for {user.username}: {pref.start_of_month} -> 25")
            pref.start_of_month = 25
            
        db.commit()
        print("✅ Successfully updated start date to 25th for all users.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_start_date()
