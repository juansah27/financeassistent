from datetime import datetime
from dateutil.relativedelta import relativedelta
from app.db.models import RecurrenceType
from app.tasks.recurring import calculate_next_due_date

start_date = datetime(2026, 2, 20)
next_date = calculate_next_due_date(start_date, RecurrenceType.MONTHLY)
print(f"Start: {start_date}, Next: {next_date}")

# Test leap year case just in case
leap_start = datetime(2024, 1, 31)
leap_next = calculate_next_due_date(leap_start, RecurrenceType.MONTHLY)
print(f"Leap Start: {leap_start}, Next: {leap_next}")
