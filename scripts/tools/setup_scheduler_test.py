"""
Test Auto Scheduler - Reset and Schedule for Near Future
"""
import sys
sys.path.insert(0, '/app')

from app.db import session, crud_whatsapp_report
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def main():
    db = next(session.get_db())
    try:
        print("=" * 60)
        print("Scheduler Test Setup")
        print("=" * 60)
        print()
        
        # Get schedule
        schedules = crud_whatsapp_report.get_enabled_schedules(db)
        if not schedules:
            print("❌ No enabled schedules")
            return
        
        schedule = schedules[0]
        tz = ZoneInfo("Asia/Jakarta")
        current_time = datetime.now(tz)
        
        print(f"Current time (WIB): {current_time.strftime('%H:%M:%S')}")
        print(f"Current schedule: {schedule.report_time}")
        print(f"Last sent: {schedule.last_sent_at}")
        print()
        
        # Calculate test time: 3 minutes from now
        test_time = current_time + timedelta(minutes=3)
        test_time_str = test_time.strftime("%H:%M")
        
        print(f"📝 Setting up test:")
        print(f"  1. Reset last_sent_at to yesterday")
        print(f"  2. Set report time to: {test_time_str} (3 minutes from now)")
        print()
        
        # Reset last_sent_at to yesterday
        yesterday = current_time - timedelta(days=1)
        from app.db.models import WhatsAppReportSchedule
        db.query(WhatsAppReportSchedule).filter(
            WhatsAppReportSchedule.id == schedule.id
        ).update({
            "last_sent_at": yesterday
        })
        
        # Update schedule time
        crud_whatsapp_report.update_report_schedule(
            db,
            user_id=schedule.user_id,
            report_time=test_time_str
        )
        
        db.commit()
        
        print("✅ Test setup complete!")
        print()
        print("=" * 60)
        print("What happens next:")
        print("=" * 60)
        print(f"⏰ Scheduler checks every hour at :05")
        print(f"📅 Next check: {test_time.strftime('%H:05:00')}")
        print(f"📤 Report will be sent at: ~{test_time.strftime('%H:05')} (if current hour = {test_time.hour})")
        print()
        print("To monitor:")
        print("  docker-compose logs -f web | findstr /i \"whatsapp report sent\"")
        print()
        print(f"⚠️  NOTE: You have ~3 minutes to wait until {test_time_str}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
