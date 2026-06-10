"""
Settings routes (dark mode, currency, family members)
"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db import session, models, crud_new_features, crud_extended
from app.db.crud_bot_reply import get_all_templates, create_template, update_template, delete_template, get_template
from app.auth import auth

router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    preferences = crud_new_features.get_user_preference(db, current_user.id)
    family_members = crud_new_features.get_family_members(db, current_user.id)
    currencies = crud_new_features.get_all_currencies(db)
    bot_templates = get_all_templates(db, active_only=False)
    
    
    # Get all users for admin management
    from app.db import crud
    all_users = crud.get_all_users(db)
    
    # Get notifications for the notifications tab
    unread_notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True, limit=5)
    notifications = crud_extended.get_notifications(db, current_user.id, unread_only=False)
    
    # Determine active tab
    tab = request.query_params.get("tab", "general")
    
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": current_user,
            "preferences": preferences,
            "family_members": family_members,
            "currencies": currencies,
            "bot_templates": bot_templates,
            "all_users": all_users,
            "unread_notifications": unread_notifications or [],
            "notifications": notifications,
            "active_tab": tab
        }
    )

@router.post("/settings/dark-mode")
async def toggle_dark_mode(
    dark_mode: str = Form(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Convert string to boolean
    is_dark = dark_mode.lower() == 'true'
    crud_new_features.update_user_preference(db, current_user.id, dark_mode=is_dark)
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/settings/currency")
async def update_currency(
    currency_code: str = Form(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    crud_new_features.update_user_preference(db, current_user.id, base_currency_code=currency_code)
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/settings/family-member")
async def add_family_member(
    name: str = Form(...),
    role: str = Form(None),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    crud_new_features.create_family_member(db, current_user.id, name, role)
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/settings/family-member/{member_id}/delete")
async def delete_family_member(
    member_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    crud_new_features.delete_family_member(db, member_id, current_user.id)
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/settings/bot-reply")
async def create_bot_reply_template(
    name: str = Form(...),
    template: str = Form(...),
    is_active: bool = Form(False),
    is_default: bool = Form(False),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Create a new bot reply template"""
    from app.db.crud_bot_reply import create_template
    create_template(db, name, template, is_active, is_default)
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/settings/bot-reply/{template_id}/update")
async def update_bot_reply_template(
    template_id: int,
    name: str = Form(...),
    template: str = Form(...),
    is_active: bool = Form(False),
    is_default: bool = Form(False),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Update bot reply template"""
    from app.db.crud_bot_reply import update_template
    update_template(db, template_id, name, template, is_active, is_default)
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/settings/bot-reply/{template_id}/delete")
async def delete_bot_reply_template(
    template_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Delete bot reply template"""
    from app.db.crud_bot_reply import delete_template
    delete_template(db, template_id)
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/settings/users")
async def create_new_user(
    username: str = Form(...),
    pin: str = Form(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Create a new login user"""
    from app.db import crud
    
    # Validation
    if len(pin) != 6 or not pin.isdigit():
        # In a real app we should flash a message, but for now just redirect
        # Ideally we'd use session flash messages
        return RedirectResponse(url="/settings", status_code=303)
        
    # Check if user exists
    existing_user = crud.get_user_by_username(db, username)
    if existing_user:
        return RedirectResponse(url="/settings", status_code=303)
        
    crud.create_user(db, username, pin)
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/settings/family/create")
async def create_family_route(
    name: str = Form(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    from app.db import crud
    
    if current_user.family_id:
        return RedirectResponse(url="/settings?error=already_in_family", status_code=303)
        
    family = crud.create_family(db, name)
    current_user.family_id = family.id
    db.commit()
    
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/settings/family/join")
async def join_family_route(
    code: str = Form(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    from app.db import crud
    
    if current_user.family_id:
        return RedirectResponse(url="/settings?error=already_in_family", status_code=303)
        
    family = crud.get_family_by_code(db, code.upper())
    if not family:
        return RedirectResponse(url="/settings?error=invalid_code", status_code=303)
        
    current_user.family_id = family.id
    db.commit()
    
    return RedirectResponse(url="/settings", status_code=303)

@router.post("/settings/family/leave")
async def leave_family_route(
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    if not current_user.family_id:
        return RedirectResponse(url="/settings", status_code=303)
        
    current_user.family_id = None
    db.commit()
    
    return RedirectResponse(url="/settings", status_code=303)

