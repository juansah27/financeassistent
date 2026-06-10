"""
Scheduler for background tasks
Handles periodic execution of recurring transactions and notifications
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.db import session
from app.db.models import User
from app.tasks import recurring, notifications
import logging
import os
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)

scheduler = None

def process_recurring_job():
    """Job to process recurring transactions - runs daily at midnight"""
    db = next(session.get_db())
    try:
        count, overdue_list = recurring.process_recurring_transactions(db)
        logger.info(f"Processed {count} recurring transactions (INCOME auto-created)")
        if overdue_list:
            logger.info(f"Found {len(overdue_list)} overdue non-INCOME recurring for alerting")
    except Exception as e:
        logger.error(f"Error processing recurring transactions: {e}")
    finally:
        db.close()


def send_recurring_overdue_alerts_job():
    """Job to send hourly alerts for overdue non-INCOME recurring transactions"""
    db = next(session.get_db())
    try:
        from app.tasks.notifications import send_recurring_overdue_alerts
        sent_count = send_recurring_overdue_alerts(db)
        if sent_count > 0:
            logger.info(f"Sent {sent_count} recurring overdue alerts")
    except Exception as e:
        logger.error(f"Error sending recurring overdue alerts: {e}")
    finally:
        db.close()

def check_notifications_job():
    """Job to check and create notifications for all users - runs daily at 8 AM"""
    db = next(session.get_db())
    try:
        # Get all users
        users = db.query(User).all()
        for user in users:
            try:
                notifications.run_all_checks(db, user.id)
                logger.info(f"Checked notifications for user: {user.username}")
            except Exception as e:
                logger.error(f"Error checking notifications for user {user.username}: {e}")
    except Exception as e:
        logger.error(f"Error in notification check job: {e}")
    finally:
        db.close()

def update_gold_prices_job():
    """Job to update all gold assets' prices - runs daily at 9 AM"""
    db = next(session.get_db())
    try:
        from app.services import gold_price
        from app.db.models import AssetType
        from app.db import crud_extended
        
        # Get all active gold assets
        gold_assets = crud_extended.get_assets(db, asset_type=AssetType.GOLD, active_only=True)
        
        if not gold_assets:
            logger.info("No gold assets to update")
            return
        
        updated_count = 0
        failed_count = 0
        
        for asset in gold_assets:
            try:
                # Only update if asset has quantity
                if not asset.quantity or asset.quantity <= 0:
                    logger.debug(f"Skipping asset {asset.id} ({asset.name}) - no quantity")
                    continue
                
                # Update price
                result = gold_price.update_gold_asset_price(db, asset.id, asset.user_id)
                
                if result["success"]:
                    updated_count += 1
                    logger.info(f"Updated gold asset {asset.id} ({asset.name}): {result['new_value']:,.0f}")
                else:
                    failed_count += 1
                    logger.warning(f"Failed to update asset {asset.id}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error updating gold asset {asset.id}: {e}")
        
        logger.info(f"Gold price update completed: {updated_count} updated, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"Error in gold price update job: {e}")
    finally:
        db.close()

def send_whatsapp_daily_report_job():
    """Job to send WhatsApp daily reports - runs every hour to check schedules"""
    db = next(session.get_db())
    try:
        from app.db import crud_whatsapp_report
        from app.services import report_generator
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        import httpx
        import os
        
        # Get all enabled schedules
        schedules = crud_whatsapp_report.get_enabled_schedules(db)
        
        if not schedules:
            logger.debug("No enabled WhatsApp report schedules")
            return
        
        # Use Jakarta timezone
        tz = ZoneInfo("Asia/Jakarta")
        current_time = datetime.now(tz)
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        logger.info(f"WhatsApp report job running - Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        sent_count = 0
        failed_count = 0
        
        for schedule in schedules:
            try:
                # Parse schedule time (format: "HH:MM")
                schedule_hour, schedule_minute = map(int, schedule.report_time.split(':'))
                
                # Scheduled time for TODAY
                today_scheduled = current_time.replace(hour=schedule_hour, minute=schedule_minute, second=0, microsecond=0)
                
                # Determine the most recent scheduled window (could be today or yesterday)
                if current_time < today_scheduled:
                    most_recent_scheduled = today_scheduled - timedelta(days=1)
                else:
                    most_recent_scheduled = today_scheduled
                
                logger.debug(f"Checking schedule {schedule.id}: report_time={schedule.report_time}, "
                             f"most_recent_scheduled={most_recent_scheduled.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Check if already sent for the most recent window
                if schedule.last_sent_at:
                    last_sent_tz = schedule.last_sent_at.astimezone(tz)
                    if last_sent_tz >= most_recent_scheduled:
                        logger.debug(f"Report already sent for the current window for schedule {schedule.id}")
                        continue
                
                # Generate report
                logger.info(f"Generating daily report for user {schedule.user_id}")
                report_message = report_generator.generate_daily_report(db, schedule.user_id)
                
                # Send via WhatsApp bot API
                BOT_API_URL = os.getenv("WHATSAPP_BOT_API_URL", "http://whatsapp-bot:3000")
                WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-change-this")
                
                logger.info(f"Sending WhatsApp report to {schedule.group_name}")
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
                
                if response.status_code == 200:
                    # Update last_sent_at
                    crud_whatsapp_report.update_last_sent(db, schedule.id)
                    sent_count += 1
                    logger.info(f"WhatsApp daily report sent successfully for schedule {schedule.id}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to send WhatsApp report: {response.text}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending WhatsApp report for schedule {schedule.id}: {e}")
        
        if sent_count > 0 or failed_count > 0:
            logger.info(f"WhatsApp daily report job completed: {sent_count} sent, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"Error in WhatsApp daily report job: {e}")
    finally:
        db.close()


def database_backup_job():
    """Job to backup the database - runs daily at 3 AM"""
    try:
        # Get DB credentials from env
        db_user = os.getenv("DB_USER", "finance_user")
        db_password = os.getenv("DB_PASSWORD", "finance_pass")
        db_name = os.getenv("DB_NAME", "finance_db")
        db_host = os.getenv("DB_HOST", "db")
        
        # Determine backup path
        backup_dir = "/app/backup"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}.sql.gz"
        filepath = os.path.join(backup_dir, filename)
        
        logger.info(f"Starting database backup to {filepath}")
        
        # Use pg_dump with compression
        # PGPASSWORD environment variable is used by pg_dump for authentication
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        
        cmd = [
            "pg_dump",
            "-h", db_host,
            "-U", db_user,
            "-Z", "9", # Maximum compression
            "-f", filepath,
            db_name
        ]
        
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            logger.info(f"Database backup completed successfully: {filename}")
            # Keep only last 7 days of backups (optional cleanup logic could go here)
        else:
            logger.error(f"Database backup failed with return code {process.returncode}: {stderr}")
            
    except Exception as e:
        logger.error(f"Error in database backup job: {e}")


def start_scheduler():
    """Start the background scheduler"""
    global scheduler
    if scheduler and scheduler.running:
        logger.warning("Scheduler is already running")
        return
    
    scheduler = BackgroundScheduler()
    
    # Process recurring transactions daily at 00:00 (midnight)
    scheduler.add_job(
        process_recurring_job,
        trigger=CronTrigger(hour=0, minute=0),
        id='process_recurring_transactions',
        name='Process Recurring Transactions',
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
        max_instances=1
    )
    
    # Check notifications daily at 08:00 (8 AM)
    scheduler.add_job(
        check_notifications_job,
        trigger=CronTrigger(hour=8, minute=0),
        id='check_notifications',
        name='Check Notifications',
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
        max_instances=1
    )
    
    # Update gold prices daily at 09:00 (9 AM)
    scheduler.add_job(
        update_gold_prices_job,
        trigger=CronTrigger(hour=9, minute=0),
        id='update_gold_prices',
        name='Update Gold Prices',
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
        max_instances=1
    )
    
    # Send WhatsApp daily reports - check every 2 minutes for precision.
    # WSL/Docker timers can drift a few seconds; keep a generous misfire window
    # so the 2-minute checker still runs instead of being skipped as "missed".
    scheduler.add_job(
        send_whatsapp_daily_report_job,
        trigger=CronTrigger(minute='*/2'),  # Run every 2 minutes
        id='send_whatsapp_daily_report',
        name='Send WhatsApp Daily Report',
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
        max_instances=1
    )
    
    # Database backup daily at 03:00 (3 AM)
    scheduler.add_job(
        database_backup_job,
        trigger=CronTrigger(hour=3, minute=0),
        id='database_backup',
        name='Daily Database Backup',
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
        max_instances=1
    )
    
    # Send recurring overdue alerts every hour
    scheduler.add_job(
        send_recurring_overdue_alerts_job,
        trigger=CronTrigger(minute=0),  # Every hour at :00
        id='recurring_overdue_alerts',
        name='Recurring Overdue Alerts',
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
        max_instances=1
    )
    

    
    scheduler.start()
    logger.info("Background scheduler started")
    logger.info("  - Process recurring transactions: Daily at 00:00")
    logger.info("  - Check notifications: Daily at 08:00")
    logger.info("  - Update gold prices: Daily at 09:00")
    logger.info("  - Send WhatsApp daily reports: Every 2 minutes")
    logger.info("  - Database backup: Daily at 03:00")
    logger.info("  - Recurring overdue alerts: Every hour")



def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
    scheduler = None

