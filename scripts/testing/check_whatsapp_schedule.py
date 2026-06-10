"""
Diagnostic script to check WhatsApp report schedule configuration
"""
import sys
sys.path.insert(0, '/app')

from app.db import session, crud_whatsapp_report
from datetime import datetime

def main():
    db =next(session.get_db())
    try:
        print("=" * 60)
        print("WhatsApp Report Schedule Diagnostic")
        print("=" * 60)
        print()
        
        # Get all schedules
        schedules = crud_whatsapp_report.get_enabled_schedules(db)
        
        if not schedules:
            print("❌ NO ENABLED SCHEDULES FOUND")
            print()
            print("To enable auto reports:")
            print("1. Go to /whatsapp-report page")
            print("2. Enable the schedule toggle")
            print("3. Set report time (e.g., 10:00)")
            print("4. Select WhatsApp group")
            print("5. Click Save")
        else:
            print(f"✅ Found {len(schedules)} enabled schedule(s)")
            print()
            
            current_time = datetime.now()
            print(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            for i, schedule in enumerate(schedules, 1):
                print(f"Schedule #{i}:")
                print(f"  - User ID: {schedule.user_id}")
                print(f"  - Report Time: {schedule.report_time}")
                print(f"  - Group Name: {schedule.group_name}")
                print(f"  - Group ID: {schedule.group_id}")
                print(f"  - Last Sent: {schedule.last_sent_at if schedule.last_sent_at else 'Never'}")
                print(f"  - Enabled: {schedule.is_enabled}")
                print()
                
                # Check if it should send today
                schedule_hour, schedule_minute = map(int, schedule.report_time.split(':'))
                if schedule.last_sent_at:
                    last_sent_date = schedule.last_sent_at.date()
                    today = current_time.date()
                    already_sent = last_sent_date == today
                    print(f"  - Already sent today: {already_sent}")
                else:
                    print(f"  - Already sent today: No")
                    
                print(f"  - Next send time: Today at {schedule.report_time} (if not sent yet)")
                print()
        
        print("=" * 60)
        print("Scheduler Configuration:")
        print("=" * 60)
        print("Job runs: Every hour at :05 minutes")
        print(f"Next check: {current_time.replace(hour=current_time.hour + 1 if current_time.minute >= 5 else current_time.hour, minute=5, second=0).strftime('%H:%M:%S')}")
        print()
        print("To test manually, go to:")
        print("  /whatsapp-report page → Click 'Test Send Report' button")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
