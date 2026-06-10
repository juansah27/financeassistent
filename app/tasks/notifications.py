"""
Background task to create notifications for budgets, goals, and recurring transactions
"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from app.db import session, crud_extended, models, crud


def check_budget_alerts(db: Session, user_id: int, specific_category: str = None, send_whatsapp: bool = True):
    """
    Check if budgets are exceeded and create notifications.
    If specific_category is provided, only check that budget.
    Returns newly-created alert messages. Set send_whatsapp=False when the caller will embed alerts in its own reply.
    """
    alerts = []
    now = datetime.now()
    stats = crud.get_monthly_stats(db, user_id)
    category_breakdown = stats.get("category_breakdown", {})
    
    # Get relevant budgets
    if specific_category:
        budget = crud_extended.get_budget_by_category(db, user_id, specific_category, now.year, now.month)
        budgets = [budget] if budget else []
    else:
        budgets = crud_extended.get_budgets(db, user_id, now.year, now.month)
    
    for budget in budgets:
        actual = category_breakdown.get(budget.category, 0)
        percentage = (float(actual) / float(budget.amount) * 100) if budget.amount > 0 else 0
        
        notification_title = None
        notification_message = None
        current_type = None

        # Alert at 80% and 100%
        if percentage >= 100:
            notification_title = f"Limit {budget.category} Jebol! 🚨"
            notification_message = f"Pengeluaran {budget.category} Rp {actual:,.0f} telah melebihi budget Rp {budget.amount:,.0f} ({percentage:.0f}%)"
            current_type = "100_percent"
        elif percentage >= 80:
            notification_title = f"Budget {budget.category} Menipis ⚠️"
            notification_message = f"Hati-hati! Pengeluaran {budget.category} sudah {percentage:.0f}% (Rp {actual:,.0f} / Rp {budget.amount:,.0f})"
            current_type = "80_percent"
            
        if notification_title and notification_message:
            alert_message = f"*{notification_title}*\n{notification_message}"

            # Check if recently notified for this specific milestone
            # We use a unique marker in the title or message content implicitly, 
            # but to be robust, we check if we already sent THIS specific type of alert this month.

            # Logic: 
            # - If 100% reached, check if we already sent a "100%" or "Jebol" alert for this category this month.
            # - If 80% reached (and not 100%), check if matching alert sent.

            start_of_month = datetime(now.year, now.month, 1)

            # Search partial match in title to identify the alert type
            keywords_to_check = []
            if current_type == "100_percent":
                keywords_to_check = [f"Limit {budget.category} Jebol", f"Budget {budget.category} Melebihi"]
            elif current_type == "80_percent":
                keywords_to_check = [f"Budget {budget.category} Menipis", f"Budget {budget.category} Hampir"]

            already_sent = False
            for kw in keywords_to_check:
                existing = db.query(models.Notification).filter(
                    models.Notification.user_id == user_id,
                    models.Notification.notification_type == "budget",
                    models.Notification.title.contains(kw),
                    models.Notification.created_at >= start_of_month
                ).first()
                if existing:
                    already_sent = True
                    break

            if not already_sent:
                # Create In-App Notification (only once per month)
                crud_extended.create_notification(
                    db, user_id,
                    notification_title,
                    notification_message,
                    "budget"
                )

                # Lookup schedule for WhatsApp
                schedule = db.query(models.WhatsAppReportSchedule).filter(
                    models.WhatsAppReportSchedule.user_id == user_id,
                    models.WhatsAppReportSchedule.is_enabled == True
                ).first()

                group_id = schedule.group_id if schedule else None
                group_name = schedule.group_name if schedule else None

                # Send standalone WhatsApp notification (only for cron/schedule callers)
                if send_whatsapp:
                    send_whatsapp_notification_async(alert_message, group_name, group_id)

            # For WhatsApp webhook replies: always include alert
            # For cron/schedule: only include if it's a new alert
            if not send_whatsapp or not already_sent:
                alerts.append(alert_message)

    return alerts

def check_goal_progress(db: Session, user_id: int):
    """Update goal progress based on savings and create notifications"""
    stats = crud.get_monthly_stats(db, user_id)
    total_savings = stats.get("category_breakdown", {}).get("Tabungan", 0)
    
    goals = crud_extended.get_goals(db, user_id, include_achieved=False)
    
    for goal in goals:
        # Update progress (assuming savings contribute to goals)
        # In real app, you'd have more sophisticated logic
        if goal.current_amount < total_savings:
            old_progress = float(goal.current_amount) / float(goal.target_amount) if goal.target_amount > 0 else 0
            crud_extended.update_goal_progress(db, goal.id, user_id, total_savings)
            new_progress = float(total_savings) / float(goal.target_amount) if goal.target_amount > 0 else 0
            
            # Notify on milestones
            if new_progress >= 1.0 and old_progress < 1.0:
                crud_extended.create_notification(
                    db, user_id,
                    f"🎉 Goal '{goal.name}' Tercapai!",
                    f"Selamat! Anda telah mencapai target goal '{goal.name}'",
                    "goal"
                )
            elif new_progress >= 0.5 and old_progress < 0.5:
                crud_extended.create_notification(
                    db, user_id,
                    f"Goal '{goal.name}' Setengah Jalan",
                    f"Anda sudah mencapai 50% dari goal '{goal.name}'",
                    "goal"
                )

def check_recurring_reminders(db: Session, user_id: int):
    """Create reminders for upcoming recurring transactions"""
    recurring_list = crud_extended.get_recurring_transactions(db, user_id, active_only=True)
    now = datetime.now(timezone.utc)
    
    for recurring in recurring_list:
        # Ensure both datetimes are timezone-aware
        next_due = recurring.next_due_date
        if next_due.tzinfo is None:
            # If next_due_date is naive, assume it's UTC
            next_due = next_due.replace(tzinfo=timezone.utc)
        days_until_due = (next_due - now).days
        
        # Remind 3 days before and 1 day before
        # Remind 3 days before and 1 day before
        if days_until_due == 3 or days_until_due == 1:
            is_income = recurring.type == models.TransactionType.INCOME
            
            if days_until_due == 3:
                if is_income:
                    notification_title = f"Penerimaan {recurring.description} Akan Datang"
                    notification_message = f"Penerimaan '{recurring.description}' sebesar Rp {recurring.amount:,.0f} dijadwalkan dalam 3 hari"
                else:
                    notification_title = f"Tagihan {recurring.description} Akan Jatuh Tempo"
                    notification_message = f"Tagihan '{recurring.description}' sebesar Rp {recurring.amount:,.0f} akan jatuh tempo dalam 3 hari"
            else:
                if is_income:
                    notification_title = f"Penerimaan {recurring.description} Besok"
                    notification_message = f"Jangan lupa, besok ada pemasukan '{recurring.description}' sebesar Rp {recurring.amount:,.0f}"
                else:
                    notification_title = f"Tagihan {recurring.description} Besok Jatuh Tempo"
                    notification_message = f"Jangan lupa bayar tagihan '{recurring.description}' sebesar Rp {recurring.amount:,.0f} besok"
            
            # Deduplication: Check if notification already sent today
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            existing_notif = db.query(models.Notification).filter(
                models.Notification.user_id == user_id,
                models.Notification.notification_type == "recurring",
                models.Notification.message == notification_message,
                models.Notification.created_at >= today_start
            ).first()
            
            if not existing_notif:
                crud_extended.create_notification(
                    db, user_id,
                    notification_title,
                    notification_message,
                    "recurring"
                )
                # Send WhatsApp notification
                # Look up group_id from WhatsAppReportSchedule
                schedule = db.query(models.WhatsAppReportSchedule).filter(
                    models.WhatsAppReportSchedule.user_id == user_id,
                    models.WhatsAppReportSchedule.is_enabled == True
                ).first()
                
                group_id = None
                group_name = None
                if schedule:
                    group_id = schedule.group_id
                    group_name = schedule.group_name
                
                send_whatsapp_notification_async(notification_message, group_name, group_id)

def send_whatsapp_notification_async(message: str, group_name: str = None, group_id: str = None):
    """
    Send WhatsApp notification asynchronously (non-blocking)
    """
    try:
        import os
        import requests
        
        WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-change-this")
        BOT_API_URL = os.getenv("WHATSAPP_BOT_API_URL", "http://whatsapp-bot:3000")
        API_URL = os.getenv("API_URL", "http://web:8000")
        
        # Use FastAPI endpoint which will forward to bot
        requests.post(
            f"{API_URL}/api/whatsapp/send-notification",
            json={
                "group_name": group_name,
                "group_id": group_id,
                "message": message
            },
            headers={
                "X-Webhook-Secret": WEBHOOK_SECRET,
                "Content-Type": "application/json"
            },
            timeout=5
        )
    except Exception as e:
        # Don't fail the notification creation if WhatsApp send fails
        print(f"⚠️ Failed to send WhatsApp notification: {e}")

def run_all_checks(db: Session, user_id: int):
    """Run all notification checks for a user"""
    check_budget_alerts(db, user_id)
    check_goal_progress(db, user_id)
    check_recurring_reminders(db, user_id)


def send_recurring_overdue_alerts(db: Session) -> int:
    """
    Send hourly WhatsApp alerts for due/overdue non-INCOME recurring transactions.
    
    Logic:
    - Non-INCOME recurring yang sudah jatuh tempo tapi belum dibayar
    - User WA manual untuk bayar → baru buat transaksi
    - Kirim alert tiap 1 jam ke WhatsApp
    
    Returns: number of alerts sent
    """
    from app.tasks.recurring import get_pending_recurring_for_alerts
    from datetime import datetime, timezone
    
    pending_items = get_pending_recurring_for_alerts(db)
    
    if not pending_items:
        return 0
    
    sent_count = 0
    now = datetime.now(timezone.utc)
    
    for item in pending_items:
        recurring = item["recurring"]
        days_overdue = item["days_overdue"]
        user_id = item["user_id"]
        
        # Build alert message
        if days_overdue == 0:
            urgency = "⚠️ *Jatuh Tempo Hari Ini*"
            detail = "Tagihan ini sudah jatuh tempo hari ini."
        elif days_overdue == 1:
            urgency = "🚨 *Terlambat 1 Hari*"
            detail = "Tagihan ini sudah melewati jatuh tempo kemarin."
        else:
            urgency = f"🚨 *Terlambat {days_overdue} Hari*"
            detail = f"Tagihan ini sudah melewati jatuh tempo {days_overdue} hari lalu."
        
        # Format due date in WIB
        from zoneinfo import ZoneInfo
        tz_jakarta = ZoneInfo("Asia/Jakarta")
        due_wib = item["next_due"].astimezone(tz_jakarta)
        due_str = due_wib.strftime("%d %b %Y")
        
        alert_message = (
            f"{urgency}\n\n"
            f"📋 *{recurring.description}*\n"
            f"• Nominal: Rp {recurring.amount:,.0f}\n"
            f"• Jatuh tempo: {due_str}\n"
            f"• Kategori: {recurring.category}\n\n"
            f"{detail}\n\n"
            f"💡 Ketik *bayar {recurring.description.lower()}* untuk catat pembayaran."
        )
        
        # Deduplication: check if we already sent this exact alert in the last hour
        one_hour_ago = now - timedelta(hours=1)
        existing_notif = db.query(models.Notification).filter(
            models.Notification.user_id == user_id,
            models.Notification.notification_type == "recurring_overdue",
            models.Notification.message == alert_message,
            models.Notification.created_at >= one_hour_ago
        ).first()
        
        if existing_notif:
            # Already sent this alert recently, skip
            continue
        
        # Create in-app notification
        crud_extended.create_notification(
            db, user_id,
            f"Tagihan Overdue: {recurring.description}",
            alert_message,
            "recurring_overdue"
        )
        
        # Send WhatsApp notification
        schedule = db.query(models.WhatsAppReportSchedule).filter(
            models.WhatsAppReportSchedule.user_id == user_id,
            models.WhatsAppReportSchedule.is_enabled == True
        ).first()
        
        group_id = schedule.group_id if schedule else None
        group_name = schedule.group_name if schedule else None
        
        send_whatsapp_notification_async(alert_message, group_name, group_id)
        sent_count += 1
    
    return sent_count

