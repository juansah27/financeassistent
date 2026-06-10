from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db import session, crud_extended, models
from app.auth import auth

router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    return RedirectResponse(url="/settings?tab=notifications", status_code=303)

@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    crud_extended.mark_notification_read(db, notification_id, current_user.id)
    return RedirectResponse(url="/notifications", status_code=303)

@router.post("/notifications/read-all")
async def mark_all_read(
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    crud_extended.mark_all_notifications_read(db, current_user.id)
    return RedirectResponse(url="/notifications", status_code=303)

@router.get("/api/notifications/unread-count")
async def unread_count(
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True)
    return JSONResponse({"count": len(notifications)})

@router.post("/api/notifications/read-all")
async def api_mark_all_read(
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    crud_extended.mark_all_notifications_read(db, current_user.id)
    return JSONResponse({"success": True})
