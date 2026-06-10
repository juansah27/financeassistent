"""
Transaction Keywords management routes
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.db import session, models
from app.db.crud_keywords import (
    get_all_keywords, create_keyword, update_keyword, 
    delete_keyword, toggle_keyword, get_keyword, resync_all_transactions
)
from app.db.crud_categories import get_categories
from app.auth import auth

router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

@router.get("/keywords", response_class=HTMLResponse)
async def keywords_page(request: Request):
    """Redirect to categories tab in settings"""
    return RedirectResponse(url="/settings?tab=categories", status_code=303)

@router.post("/keywords")
async def create_keyword_route(
    request: Request,
    keyword: str = Form(...),
    category: str = Form(None),
    is_active: bool = Form(True),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Create a new keyword"""
    try:
        keyword_lower = keyword.lower().strip()
        if not keyword_lower:
            raise HTTPException(status_code=400, detail="Keyword cannot be empty")
        
        # Handle "None" string from select option
        if category == "None" or category == "":
            category = None
            
        create_keyword(db, keyword_lower, category=category, is_active=is_active)
        return RedirectResponse(url="/keywords", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating keyword: {str(e)}")

@router.post("/keywords/{keyword_id}/toggle")
async def toggle_keyword_route(
    keyword_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Toggle keyword active status"""
    result = toggle_keyword(db, keyword_id)
    if result:
        return RedirectResponse(url="/keywords", status_code=303)
    raise HTTPException(status_code=404, detail="Keyword not found")

@router.post("/keywords/{keyword_id}/delete")
async def delete_keyword_route(
    keyword_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Delete keyword (soft delete)"""
    result = delete_keyword(db, keyword_id)
    if result:
        return RedirectResponse(url="/keywords", status_code=303)
    raise HTTPException(status_code=404, detail="Keyword not found")

@router.post("/keywords/{keyword_id}/update")
async def update_keyword_route(
    keyword_id: int,
    keyword: str = Form(...),
    category: str = Form(None),
    is_active: bool = Form(True),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Update keyword"""
    try:
        keyword_lower = keyword.lower().strip()
        if not keyword_lower:
            raise HTTPException(status_code=400, detail="Keyword cannot be empty")
        
        # Handle "None" string from select option
        if category == "None" or category == "":
            category = None
            
        result = update_keyword(db, keyword_id, keyword_lower, category=category, is_active=is_active)
        if result:
            return RedirectResponse(url="/keywords", status_code=303)
        raise HTTPException(status_code=404, detail="Keyword not found or duplicate")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating keyword: {str(e)}")

# API endpoint for bot.js to fetch keywords
@router.get("/api/keywords")
async def get_keywords_api(
    active_only: bool = True,
    db: Session = Depends(session.get_db)
):
    """API endpoint to get keywords list (for WhatsApp bot)"""
    from app.db.crud_keywords import get_keyword_list
    keywords = get_keyword_list(db, active_only=active_only)
    return JSONResponse({
        "success": True,
        "keywords": keywords,
        "count": len(keywords)
    })

@router.post("/api/keywords/resync")
async def resync_keywords_route(
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Resync all transactions with current keywords"""
    try:
        updated_count = resync_all_transactions(db)
        return JSONResponse({
            "success": True,
            "message": f"Synced {updated_count} transactions",
            "updated_count": updated_count
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
