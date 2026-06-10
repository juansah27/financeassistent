"""
Quick fix: Set schedule to 21:00 to trigger at next scheduler check (21:05)
"""
import sys
sys.path.insert(0, '/app')

from app.db import session, crud_whatsapp_report
from datetime import datetime
from zoneinfo import ZoneInfo

def main():
    db = next(session.get_db())
    try:
        schedules = crud_whatsapp_report.get_enabled_schedules(db)
        if not schedules:
            print("❌ No enabled schedules")
            return
        
        schedule = schedules[0]
        tz = ZoneInfo("Asia/Jakarta")
        current_time = datetime.now(tz)
        
        # Set to 21:00 so it triggers at 21:05 scheduler check
        new_time = "21:00"
        
        print(f"Current time: {current_time.strftime('%H:%M:%S')}")
        print(f"Setting schedule to: {new_time}")
        print()
        
        crud_whatsapp_report.update_report_schedule(
            db,
            user_id=schedule.user_id,
            report_time=new_time
        )
        
        db.commit()
        
        print("✅ Schedule updated!")
        print()
        print("=" * 60)
        print("Test Timeline:")
        print("=" * 60)
        print(f"⏰ Current: {current_time.strftime('%H:%M:%S')}")
        print(f"📅 Schedule: {new_time}")
        print(f"🔍 Next scheduler check: 21:05:00 (~{60 - current_time.minute} minutes)")
        print(f"📤 Report will be sent: ~21:05")
        print()
        print("To monitor in real-time:")
        print("  docker-compose logs -f web | findstr /i \"whatsapp\"")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
