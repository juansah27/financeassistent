"""
Quick script to create users for Family Finance Assistant.
Run: python create_users.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.session import SessionLocal, engine
from app.db import models, crud
import getpass

def create_users():
    """Create default users"""
    # Create tables
    models.Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("=== Family Finance Assistant - User Creation ===\n")
        
        # User 1
        print("User 1:")
        username1 = input("Username (default: suami): ").strip() or "suami"
        
        # Check if user exists
        if crud.get_user_by_username(db, username1):
            print(f"User '{username1}' already exists!")
            choice = input("Create another user? (y/n): ").strip().lower()
            if choice != 'y':
                return
        
        pin1 = getpass.getpass("6-digit PIN: ").strip()
        while len(pin1) != 6 or not pin1.isdigit():
            print("PIN must be exactly 6 digits!")
            pin1 = getpass.getpass("6-digit PIN: ").strip()
        
        user1 = crud.create_user(db, username1, pin1)
        print(f"✓ Created user: {username1}\n")
        
        # User 2
        print("User 2:")
        username2 = input("Username (default: istri): ").strip() or "istri"
        
        if crud.get_user_by_username(db, username2):
            print(f"User '{username2}' already exists! Skipping...")
        else:
            pin2 = getpass.getpass("6-digit PIN: ").strip()
            while len(pin2) != 6 or not pin2.isdigit():
                print("PIN must be exactly 6 digits!")
                pin2 = getpass.getpass("6-digit PIN: ").strip()
            
            user2 = crud.create_user(db, username2, pin2)
            print(f"✓ Created user: {username2}\n")
        
        print("Done! You can now login at http://localhost:8000")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_users()

