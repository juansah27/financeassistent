"""
Update WhatsApp report schedule time for testing
"""
import sys
sys.path.insert(0, '/app')

from app.db import session, crud_whatsapp_report
from datetime import datetime

def main():
    db = next(session.get_db())
    try:
        # Get the enabled schedule
        schedules = crud_whatsapp_report.get_enabled_schedules(db)
        
        if not schedules:
            print("❌ No enabled schedules found")
            return
        
        schedule = schedules[0]
        print(f"Current schedule:")
        print(f"  - Report Time: {schedule.report_time}")
        print(f"  - Last Sent: {schedule.last_sent_at}")
        print()
        
        # Update to 20:00 (8 PM) for testing
        new_time = "20:00"
        updated = crud_whatsapp_report.update_report_schedule(
            db,
            user_id=schedule.user_id,
            report_time=new_time
        )
        
        print(f"✅ Updated report time to: {new_time}")
        print()
        print("Scheduler will check every hour at :05")
        print(f"Next check: 20:05")
        print(f"Report will be sent around: 20:05 (if current time < 20:00)")
        print()
        print("Current time:", datetime.now().strftime("%H:%M:%S"))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
