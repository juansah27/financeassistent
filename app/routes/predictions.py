"""
Spending Trends & Predictions routes
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json
from app.db import session, models, crud_new_features
from app.auth import auth

router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

@router.get("/predictions", response_class=HTMLResponse)
async def predictions_page(
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Display spending trends and predictions"""
    
    # Get spending trends by category (last 6 months)
    category_trends = crud_new_features.get_spending_trends_by_category(db, months=6)
    
    # Get spending pattern by day of week
    day_of_week_pattern = crud_new_features.get_spending_pattern_by_day_of_week(db, months=3)
    
    # Get overall next month prediction
    overall_prediction = crud_new_features.predict_next_month_spending(db, current_user.id, months_history=6)
    
    # Get category-specific predictions (skip income categories)
    category_predictions = {}
    # Get category-specific predictions (skip income categories)
    category_predictions = {}
    # Fetch user expense categories
    expense_categories = db.query(models.UserCategory).filter(
        models.UserCategory.user_id == current_user.id,
        models.UserCategory.type == 'Pengeluaran',
        models.UserCategory.is_active == True
    ).all()
    
    for cat in expense_categories:
        prediction = crud_new_features.predict_category_spending(db, cat.name, months_history=6)
        category_predictions[cat.name] = prediction
        
    # Get custom projection (Recurring + Non-Recurring extrapolation)
    custom_projection = crud_new_features.calculate_custom_projection(db, current_user.id)
    
    # Calculate next month info
    next_month = datetime.now().replace(day=1)
    if next_month.month == 12:
        next_month = next_month.replace(year=next_month.year + 1, month=1)
    else:
        next_month = next_month.replace(month=next_month.month + 1)
    
    # Prepare category trends data for charts (serialize for template)
    chart_data_json = {}
    for cat_name, trend_data in category_trends.items():
        chart_data_json[cat_name] = {
            "labels": [f"{item['month']:02d}/{item['year']}" for item in trend_data],
            "amounts": [item["amount"] for item in trend_data]
        }
    
    # Prepare JSON strings for template
    chart_data_json_str = json.dumps(chart_data_json)
    day_of_week_json_str = json.dumps(day_of_week_pattern)
    
    return templates.TemplateResponse(
        "predictions.html",
        {
            "request": request,
            "user": current_user,
            "category_trends": category_trends,
            "day_of_week_pattern": day_of_week_pattern,
            "day_of_week_json": day_of_week_json_str,
            "overall_prediction": overall_prediction,
            "category_predictions": category_predictions,
            "next_month": next_month,
            "chart_data": chart_data_json_str,
            "custom_projection": custom_projection
        }
    )

