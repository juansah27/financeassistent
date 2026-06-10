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

@router.get("/goals", response_class=HTMLResponse)
async def goals_page(
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    goals = crud_extended.get_goals(db, current_user.id, include_achieved=True)
    unread_notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True, limit=5)
    
    # Calculate total savings from Tabungan category
    stats = crud.get_monthly_stats(db, current_user.id)
    total_savings = stats.get("category_breakdown", {}).get("Tabungan", 0)
    
    return templates.TemplateResponse(
        "goals.html",
        {
            "request": request,
            "user": current_user,
            "goals": goals,
            "total_savings": total_savings,
            "unread_notifications": unread_notifications or []
        }
    )

@router.post("/goals")
async def create_goal(
    request: Request,
    name: str = Form(...),
    target_amount: float = Form(...),
    target_date: str = Form(None),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    try:
        target_dt = None
        if target_date:
            target_dt = datetime.fromisoformat(target_date)
        
        crud_extended.create_goal(db, current_user.id, name, target_amount, target_dt)
        return RedirectResponse(url="/goals", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/goals/{goal_id}/delete")
async def delete_goal_route(
    goal_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    crud_extended.delete_goal(db, goal_id, current_user.id)
    return RedirectResponse(url="/goals", status_code=303)

