"""
Initialize database with default users.
Run this script once to create initial users.
"""
from app.db.session import SessionLocal, engine
from app.db import models, crud
import getpass

def init_db():
    """Create tables and add default users"""
    # Create tables
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if users already exist
        existing_users = db.query(models.User).count()
        if existing_users > 0:
            print("Users already exist. Skipping initialization.")
            return
        
        print("=== Family Finance Assistant - Database Initialization ===\n")
        print("Creating default users (husband & wife)...\n")
        
        # Create husband user
        print("User 1: Husband")
        username1 = input("Enter username for husband (default: suami): ").strip() or "suami"
        pin1 = getpass.getpass("Enter 6-digit PIN for husband: ").strip()
        while len(pin1) != 6 or not pin1.isdigit():
            print("PIN must be exactly 6 digits!")
            pin1 = getpass.getpass("Enter 6-digit PIN for husband: ").strip()
        
        user1 = crud.create_user(db, username1, pin1)
        print(f"✓ Created user: {username1}\n")
        
        # Create wife user
        print("User 2: Wife")
        username2 = input("Enter username for wife (default: istri): ").strip() or "istri"
        pin2 = getpass.getpass("Enter 6-digit PIN for wife: ").strip()
        while len(pin2) != 6 or not pin2.isdigit():
            print("PIN must be exactly 6 digits!")
            pin2 = getpass.getpass("Enter 6-digit PIN for wife: ").strip()
        
        user2 = crud.create_user(db, username2, pin2)
        print(f"✓ Created user: {username2}\n")
        
        print("Database initialization completed!")
        print("\nYou can now start the application with: docker-compose up")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()

