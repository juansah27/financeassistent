"""
WhatsApp Report Settings UI Routes
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.db import session, crud_extended
from app.auth import auth
from app.templates_utils import create_templates

router = APIRouter()
templates = create_templates("app/templates")

@router.get("/whatsapp-report-settings", response_class=HTMLResponse)
async def whatsapp_report_settings_page(
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: dict = Depends(auth.get_current_user_cookie)
):
    """Redirect to WhatsApp settings tab"""
    return RedirectResponse(url="/settings?tab=whatsapp", status_code=303)
