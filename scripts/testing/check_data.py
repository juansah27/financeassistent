from app.db import session
from app.db.models import RecurringIncome

db = next(session.get_db())
try:
    count = db.query(RecurringIncome).count()
    print(f"RecurringIncome Count: {count}")
    
    if count > 0:
        print("Data found:")
        incomes = db.query(RecurringIncome).all()
        for i in incomes:
            print(f"- {i.name}: {i.amount}")
finally:
    db.close()
