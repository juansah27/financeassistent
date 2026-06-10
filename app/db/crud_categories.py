from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.db.models import UserCategory

def get_categories(db: Session, user_id: int) -> List[UserCategory]:
    """Get all categories for a user (including default ones)"""
    return db.query(UserCategory).filter(
        UserCategory.user_id == user_id,
        UserCategory.is_active == True
    ).order_by(UserCategory.name).all()

def get_category_by_name(db: Session, user_id: int, name: str) -> Optional[UserCategory]:
    """Get category by name for a user"""
    return db.query(UserCategory).filter(
        UserCategory.user_id == user_id,
        UserCategory.name == name
    ).first()

def create_category(db: Session, user_id: int, name: str, type: str, icon: str = None, color: str = None) -> UserCategory:
    """Create a new category"""
    category = UserCategory(
        user_id=user_id,
        name=name,
        type=type,
        icon=icon,
        color=color,
        is_default=False,
        is_active=True
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
