"""
CRUD operations for WhatsApp report schedules
"""
from sqlalchemy.orm import Session
from app.db.models import WhatsAppReportSchedule
from datetime import datetime
from typing import Optional

def get_report_schedule(db: Session, user_id: int) -> Optional[WhatsAppReportSchedule]:
    """Get report schedule configuration for a user"""
    return db.query(WhatsAppReportSchedule).filter(
        WhatsAppReportSchedule.user_id == user_id
    ).first()

def create_report_schedule(
    db: Session, 
    user_id: int, 
    report_time: str = "10:00",
    group_name: Optional[str] = None,
    group_id: Optional[str] = None,
    is_enabled: bool = True
) -> WhatsAppReportSchedule:
    """Create a new report schedule"""
    schedule = WhatsAppReportSchedule(
        user_id=user_id,
        report_time=report_time,
        group_name=group_name,
        group_id=group_id,
        is_enabled=is_enabled
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule

def update_report_schedule(
    db: Session,
    user_id: int,
    **kwargs
) -> Optional[WhatsAppReportSchedule]:
    """Update report schedule configuration"""
    schedule = get_report_schedule(db, user_id)
    if not schedule:
        # Create if doesn't exist
        return create_report_schedule(db, user_id, **kwargs)
    
    # Update fields
    for key, value in kwargs.items():
        if hasattr(schedule, key):
            setattr(schedule, key, value)
    
    db.commit()
    db.refresh(schedule)
    return schedule

def get_enabled_schedules(db: Session) -> list[WhatsAppReportSchedule]:
    """Get all enabled report schedules"""
    return db.query(WhatsAppReportSchedule).filter(
        WhatsAppReportSchedule.is_enabled == True
    ).all()

def update_last_sent(db: Session, schedule_id: int) -> None:
    """Update last_sent_at timestamp"""
    schedule = db.query(WhatsAppReportSchedule).filter(
        WhatsAppReportSchedule.id == schedule_id
    ).first()
    if schedule:
        schedule.last_sent_at = datetime.now()
        db.commit()
