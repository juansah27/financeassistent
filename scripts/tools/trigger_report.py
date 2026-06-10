"""
Trigger WhatsApp report job manually to see errors
"""
import sys
sys.path.insert(0, '/app')

from app.tasks.scheduler import send_whatsapp_daily_report_job

def main():
    print("=" * 60)
    print("Manually Triggering WhatsApp Report Job")
    print("=" * 60)
    print()
    
    try:
        send_whatsapp_daily_report_job()
        print()
        print("✅ Job completed - check logs above for results")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
