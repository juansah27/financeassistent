from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.db import session, crud_extended, models, crud
from app.auth import auth


router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

@router.get("/budget", response_class=HTMLResponse)
async def budget_page(
    request: Request,
    year: int = None,
    month: int = None,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Determine period
    curr_year, curr_month, start_day = crud.get_current_period(db, current_user.id)
    
    if year is None or month is None:
        year = curr_year
        month = curr_month
        is_current = True
    else:
        is_current = (year == curr_year and month == curr_month)

    budgets = crud_extended.get_budgets(db, current_user.id, year, month)
    stats = crud.get_monthly_stats(db, current_user.id, year, month)
    total_income = stats.get("income", 0)
    
    # Check if we should show carry-over option
    has_prev_budgets = False
    if not budgets and is_current:
        prev_year = year
        prev_month = month - 1
        if prev_month == 0:
            prev_month = 12
            prev_year -= 1
        prev_budgets = crud_extended.get_budgets(db, current_user.id, prev_year, prev_month)
        has_prev_budgets = len(prev_budgets) > 0

    # Get user categories
    user_cats = db.query(models.UserCategory).filter(
        models.UserCategory.user_id == current_user.id,
        models.UserCategory.is_active == True
    ).order_by(models.UserCategory.type, models.UserCategory.name).all()
    
    # Calculate budget vs actual
    budget_data = []
    # Only show Expense categories (Pengeluaran)
    expense_cats = [c for c in user_cats if c.type == 'Pengeluaran']
    
    for cat in expense_cats:
        budget = crud_extended.get_budget_by_category(db, current_user.id, cat.name, year, month)
        actual = stats.get("category_breakdown", {}).get(cat.name, 0)
        
        # Calculate budget amount
        budget_amount = 0
        percentage_val = None
        
        if budget:
            if budget.percentage and budget.percentage > 0:
                # Dynamic calculation based on income
                budget_amount = (float(budget.percentage) / 100) * float(total_income)
                percentage_val = float(budget.percentage)
            else:
                budget_amount = float(budget.amount)
        
        percentage = (float(actual) / float(budget_amount) * 100) if budget_amount > 0 else 0
        
        budget_data.append({
            "category": cat.name,
            "budget": budget_amount,
            "percentage_budget": percentage_val,
            "actual": actual,
            "remaining": budget_amount - actual,
            "percentage": percentage,
            "is_over": actual > budget_amount
        })
    
    total_budget_all = sum(item['budget'] for item in budget_data)
    
    # Calculate navigation
    p_year, p_month = year, month - 1
    if p_month == 0:
        p_month = 12
        p_year -= 1
    
    n_year, n_month = year, month + 1
    if n_month == 13:
        n_month = 1
        n_year += 1

    return templates.TemplateResponse(
        "budget.html",
        {
            "request": request,
            "user": current_user,
            "budgets": budget_data,
            "year": year,
            "month": month,
            "prev_year": p_year,
            "prev_month": p_month,
            "next_year": n_year,
            "next_month": n_month,
            "is_current": is_current,
            "has_prev_budgets": has_prev_budgets,
            "categories": expense_cats,
            "total_income": total_income,
            "total_budget": total_budget_all
        }
    )

@router.post("/budget")
async def create_budget(
    request: Request,
    category: str = Form(...),
    amount: float = Form(...),
    is_percentage: bool = Form(False),
    year: int = Form(...),
    month: int = Form(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    try:
        final_amount = amount
        percentage = None
        
        if is_percentage:
            percentage = amount # The input field value is treated as percentage
            # Calculate snapshot amount based on CURRENT income, just for initial record
            stats = crud.get_monthly_stats(db, current_user.id)
            total_income = stats.get("income", 0)
            final_amount = (percentage / 100) * total_income
        
        crud_extended.create_budget(db, current_user.id, category, final_amount, year, month, percentage)
        return RedirectResponse(url="/budget", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/budget/{budget_id}/delete")
async def delete_budget_route(
    budget_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    crud_extended.delete_budget(db, budget_id, current_user.id)
    return RedirectResponse(url="/budget", status_code=303)

@router.post("/budget/copy")
async def copy_budget(
    from_year: int = Form(...),
    from_month: int = Form(...),
    to_year: int = Form(...),
    to_month: int = Form(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    prev_budgets = crud_extended.get_budgets(db, current_user.id, from_year, from_month)
    for b in prev_budgets:
        crud_extended.create_budget(db, current_user.id, b.category, b.amount, to_year, to_month, b.percentage)
    return RedirectResponse(url=f"/budget?year={to_year}&month={to_month}", status_code=303)

