from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db import session, crud_extended, models, crud
from app.auth import auth
from app.db.models import TransactionType, RecurrenceType

router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

@router.get("/recurring", response_class=HTMLResponse)
async def recurring_page(
    request: Request,
    search: str = None,
    category: str = None,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    recurring_list = crud_extended.get_recurring_transactions(
        db, 
        current_user.id, 
        active_only=False, # Show all so user can search inactive ones too, or keep active_only=False to show both states in table
        search_term=search,
        category=category
    )
    unread_notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True, limit=5)
    
    # Get user categories (active only)
    user_cats = db.query(models.UserCategory).filter(
        models.UserCategory.user_id == current_user.id,
        models.UserCategory.is_active == True
    ).order_by(models.UserCategory.type, models.UserCategory.name).all()
    
    return templates.TemplateResponse(
        "recurring.html",
        {
            "request": request,
            "user": current_user,
            "recurring": recurring_list,
            "categories": [c.name for c in user_cats],
            "transaction_types": [t.value for t in TransactionType],
            "unread_notifications": unread_notifications or [],
            "search": search,
            "category": category
        }
    )

@router.post("/recurring")
async def create_recurring(
    request: Request,
    description: str = Form(...),
    amount: float = Form(...),
    category: str = Form(...),
    transaction_type: str = Form(...),
    recurrence_type: str = Form(...),
    day_of_month: int = Form(None),
    next_due_date: str = Form(...),
    total_occurrences: int = Form(None),
    interval_days: int = Form(None),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    try:
        # Category is now a string
        rec_type = RecurrenceType[recurrence_type.upper()]
        # Map transaction type string to enum
        trans_type_map = {
            "Pemasukan": TransactionType.INCOME,
            "Pengeluaran": TransactionType.EXPENSE,
            "Tabungan": TransactionType.SAVING,
            "Investasi": TransactionType.INVESTMENT,
            "Hutang": TransactionType.DEBT
        }
        trans_type = trans_type_map.get(transaction_type, TransactionType.EXPENSE)
        due_date = datetime.fromisoformat(next_due_date.replace('Z', '+00:00'))
        
        crud_extended.create_recurring_transaction(
            db, current_user.id, trans_type,
            amount, category, description, rec_type, day_of_month, due_date,
            total_occurrences=total_occurrences,
            interval_days=interval_days
        )
        
        # Trigger processing immediately to handle past due dates (e.g. user inputs salary for yesterday)
        # This ensures the balance updates instantly without waiting for the daily scheduler
        from app.tasks.recurring import process_recurring_transactions
        process_recurring_transactions(db)

        return RedirectResponse(url="/recurring", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating recurring transaction: {str(e)}")

@router.post("/recurring/{recurring_id}/toggle")
async def toggle_recurring(
    recurring_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    crud_extended.toggle_recurring_active(db, recurring_id, current_user.id)
    return RedirectResponse(url="/recurring", status_code=303)

@router.post("/recurring/{recurring_id}/delete")
async def delete_recurring_route(
    recurring_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    crud_extended.delete_recurring(db, recurring_id, current_user.id)
    return RedirectResponse(url="/recurring", status_code=303)

