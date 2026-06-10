"""
Analytics dashboard routes
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db import session, models, crud, crud_extended, crud_new_features
from app.auth import auth

router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

from datetime import datetime, timedelta

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    period: str = "6m", # 1m, 3m, 6m, 1y, all
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Determine date range based on period
    now = datetime.now()
    if period == "1m":
        months = 1
    elif period == "3m":
        months = 3
    elif period == "1y":
        months = 12
    elif period == "all":
        months = 24 # Cap at 2 years for now to avoid overload
    else: # Default 6m
        months = 6
        
    start_date = (now.replace(day=1) - timedelta(days=30 * months)).replace(day=1)
    
    # 1. Monthly Summary (Income vs Expense) for Main Chart
    # We fetch 12 months for the main chart regardless of period? 
    # Or should we match the period? Let's match the period for better zoom.
    # But usually trends are better over a year. Let's fix it to 12 months for trend chart 
    # unless period is longer.
    trend_months = months if months > 6 else 12
    monthly_summary = crud_new_features.get_monthly_summary(db, current_user.id, months=trend_months)
    
    # 2. Category Breakdown (Doughnut Chart)
    # This should strictly follow the selected period
    category_breakdown = crud_new_features.get_category_breakdown(
        db, current_user.id, start_date, now
    )
    
    # 3. Family Member Spending
    member_spending = crud_new_features.get_family_member_spending(db, current_user.id, months=months)
    
    # 4. Next Month Prediction
    prediction = crud_new_features.predict_next_month_spending(db, current_user.id, months_history=6)
    
    # Calculate key metrics
    total_period_expense = sum(item['total'] for item in category_breakdown)
    avg_monthly = total_period_expense / months if months > 0 else 0
    
    # Top spending category
    top_category = category_breakdown[0] if category_breakdown else None
    
    return templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "user": current_user,
            "period": period,
            "monthly_summary": monthly_summary,
            "category_breakdown": category_breakdown,
            "member_spending": member_spending,
            "prediction": prediction,
            "total_period_expense": total_period_expense,
            "avg_monthly": avg_monthly,
            "top_category": top_category
        }
    )

