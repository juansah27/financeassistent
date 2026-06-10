"""
Verbose test of WhatsApp report sending
"""
import sys
sys.path.insert(0, '/app')

from app.db import session, crud_whatsapp_report
from app.services import report_generator
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
import os

def main():
    db = next(session.get_db())
    try:
        print("=" * 60)
        print("Testing WhatsApp Report Send")
        print("=" * 60)
        print()
        
        # Get enabled schedules
        schedules = crud_whatsapp_report.get_enabled_schedules(db)
        print(f"Found {len(schedules)} enabled schedule(s)")
        print()
        
        if not schedules:
            print("❌ No enabled schedules")
            return
        
        schedule = schedules[0]
        tz = ZoneInfo("Asia/Jakarta")
        current_time = datetime.now(tz)
        
        print(f"Current time (WIB): {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Schedule time: {schedule.report_time}")
        print(f"Group: {schedule.group_name}")
        print()
        
        # Generate report
        print("📝 Generating daily report...")
        report_message = report_generator.generate_daily_report(db, schedule.user_id)
        print(f"✅ Generated {len(report_message)} chars")
        print()
        print("Preview (first 200 chars):")
        print(report_message[:200])
        print()
        
        # Send via WhatsApp bot API
        BOT_API_URL = os.getenv("WHATSAPP_BOT_API_URL", "http://whatsapp-bot:3000")
        WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-change-this")
        
        print(f"📤 Sending to WhatsApp Bot API: {BOT_API_URL}/send-message")
        print(f"   Target group: {schedule.group_name}")
        print(f"   Group ID: {schedule.group_id}")
        print()
        
        try:
            response = httpx.post(
                f"{BOT_API_URL}/send-message",
                json={
                    "group_name": schedule.group_name,
                    "group_id": schedule.group_id,
                    "message": report_message
                },
                headers={
                    "X-Webhook-Secret": WEBHOOK_SECRET,
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            print()
            
            if response.status_code == 200:
                print("✅ Message sent successfully!")
                
                # Update last_sent_at
                crud_whatsapp_report.update_last_sent(db, schedule.id)
                print("✅ Updated last_sent_at timestamp")
            else:
                print(f"❌ Failed to send: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error sending to bot API: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
