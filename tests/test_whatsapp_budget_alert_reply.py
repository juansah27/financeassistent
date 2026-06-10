from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
whatsapp_route = (ROOT / "app/routes/whatsapp.py").read_text()
notifications = (ROOT / "app/tasks/notifications.py").read_text()

assert "send_whatsapp: bool = True" in notifications
assert "return alerts" in notifications
assert "check_budget_alerts(db, default_user.id, transaction.category, send_whatsapp=False)" in whatsapp_route
assert "budget_alerts" in whatsapp_route
assert "reply_message +=" in whatsapp_route

print("whatsapp budget alert reply regression passed")
