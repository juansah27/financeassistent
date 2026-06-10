from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def calculate_next_due_date_old(current_date):
    # This matches the current implementation in app/tasks/recurring.py
    return current_date + timedelta(days=30)

def calculate_next_due_date_new(current_date):
    # This uses relativedelta to correctly handle months
    return current_date + relativedelta(months=1)

start_date = datetime(2026, 2, 20)
print(f"Start Date: {start_date}")
print(f"Old Logic (+30 days): {calculate_next_due_date_old(start_date)}")
print(f"New Logic (+1 month): {calculate_next_due_date_new(start_date)}")
