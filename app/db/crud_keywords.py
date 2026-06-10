"""
CRUD operations for transaction keywords
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.db.models import TransactionKeyword, Transaction 
from sqlalchemy import or_

def resync_all_transactions(db: Session) -> int:
    """
    Re-evaluate all transactions against active keywords and update categories.
    Longest matching keyword wins.
    """
    # 1. Load active keywords
    keywords = db.query(TransactionKeyword).filter(
        TransactionKeyword.is_active == True,
        TransactionKeyword.category != None
    ).all()
    # Sort by length desc
    keywords.sort(key=lambda x: len(x.keyword), reverse=True)
    
    if not keywords:
        return 0

    # 2. Process transactions
    transactions = db.query(Transaction).all()
    updated_count = 0
    
    for t in transactions:
        text_sources = []
        if t.description: text_sources.append(t.description.lower())
        if t.raw_input: text_sources.append(t.raw_input.lower())
        text = " ".join(text_sources)
        
        if not text:
            continue
            
        original_category = t.category
        matched_category = None
        
        for k in keywords:
            if k.keyword.lower() in text:
                matched_category = k.category
                break 
        
        # Update if match found and distinct from current (or if we want to fill empty ones)
        # Assuming we override existing categories if keyword matches
        if matched_category and matched_category != original_category:
            t.category = matched_category
            updated_count += 1
            
    if updated_count > 0:
        db.commit()
        
    return updated_count


def get_all_keywords(db: Session, active_only: bool = False) -> List[TransactionKeyword]:
    """Get all keywords, optionally filter by active status"""
    query = db.query(TransactionKeyword)
    if active_only:
        query = query.filter(TransactionKeyword.is_active == True)
    return query.order_by(TransactionKeyword.keyword).all()

def get_all_keywords_with_category(db: Session) -> List[TransactionKeyword]:
    """Get all keywords with their categories"""
    return db.query(TransactionKeyword).filter(TransactionKeyword.is_active == True).all()

def get_keyword_list(db: Session, active_only: bool = True) -> List[str]:
    """Get list of keyword strings (for bot.js)"""
    keywords = get_all_keywords(db, active_only=active_only)
    return [kw.keyword for kw in keywords]

def get_keyword(db: Session, keyword_id: int) -> Optional[TransactionKeyword]:
    """Get keyword by ID"""
    return db.query(TransactionKeyword).filter(TransactionKeyword.id == keyword_id).first()

def get_keyword_by_name(db: Session, keyword: str) -> Optional[TransactionKeyword]:
    """Get keyword by name"""
    return db.query(TransactionKeyword).filter(TransactionKeyword.keyword == keyword).first()

def create_keyword(db: Session, keyword: str, category: str = None, is_active: bool = True) -> TransactionKeyword:
    """Create a new keyword"""
    # Check if keyword already exists
    existing = get_keyword_by_name(db, keyword)
    if existing:
        # Update existing keyword
        existing.is_active = is_active
        if category is not None:
             existing.category = category
        db.commit()
        db.refresh(existing)
        return existing
    
    db_keyword = TransactionKeyword(keyword=keyword, category=category, is_active=is_active)
    db.add(db_keyword)
    db.commit()
    db.refresh(db_keyword)
    return db_keyword

def update_keyword(db: Session, keyword_id: int, keyword: str = None, category: str = None, is_active: bool = None) -> Optional[TransactionKeyword]:
    """Update keyword"""
    db_keyword = get_keyword(db, keyword_id)
    if not db_keyword:
        return None
    
    # Check if new keyword name conflicts with existing
    if keyword and keyword != db_keyword.keyword:
        existing = get_keyword_by_name(db, keyword)
        if existing:
            return None  # Keyword already exists
    
    if keyword is not None:
        db_keyword.keyword = keyword
    if category is not None:
        db_keyword.category = category
    if is_active is not None:
        db_keyword.is_active = is_active
    
    db.commit()
    db.refresh(db_keyword)
    return db_keyword

def delete_keyword(db: Session, keyword_id: int) -> bool:
    """Delete keyword (soft delete by setting is_active=False)"""
    db_keyword = get_keyword(db, keyword_id)
    if db_keyword:
        db_keyword.is_active = False
        db.commit()
        return True
    return False

def hard_delete_keyword(db: Session, keyword_id: int) -> bool:
    """Permanently delete keyword"""
    db_keyword = get_keyword(db, keyword_id)
    if db_keyword:
        db.delete(db_keyword)
        db.commit()
        return True
    return False

def toggle_keyword(db: Session, keyword_id: int) -> Optional[TransactionKeyword]:
    """Toggle keyword active status"""
    db_keyword = get_keyword(db, keyword_id)
    if db_keyword:
        db_keyword.is_active = not db_keyword.is_active
        db.commit()
        db.refresh(db_keyword)
        return db_keyword
    return None

