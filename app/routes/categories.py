from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.db import session, models
from app.auth import auth
from app.templates_utils import create_templates
from app.db import crud_extended

router = APIRouter()
templates = create_templates("app/templates")

class CategoryCreate(BaseModel):
    name: str
    type: str # Pemasukan, Pengeluaran, etc
    icon: Optional[str] = None
    color: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None

@router.get("/categories", response_class=HTMLResponse)
async def categories_page(
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Categories management page - Redirect to Settings"""
    return RedirectResponse(url="/settings?tab=categories", status_code=303)

@router.get("/api/categories")
async def get_categories(
    type: Optional[str] = None,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Fetch categories
    query = db.query(models.UserCategory).filter(
        models.UserCategory.user_id == current_user.id,
        models.UserCategory.is_active == True
    )
    
    if type:
        query = query.filter(models.UserCategory.type == type)
        
    categories = query.order_by(models.UserCategory.type, models.UserCategory.name).all()

    # Fetch all active keywords
    keywords_query = db.query(models.TransactionKeyword).filter(models.TransactionKeyword.is_active == True).all()
    
    # Map keywords to categories
    keywords_by_category = {}
    for kw in keywords_query:
        cat_name = kw.category
        if not cat_name:
            cat_name = "Uncategorized"
        
        if cat_name not in keywords_by_category:
            keywords_by_category[cat_name] = []
        keywords_by_category[cat_name].append({
            "id": kw.id,
            "keyword": kw.keyword,
            "is_active": kw.is_active
        })

    # Prepare response list
    categories_data = []
    existing_cat_names = set()
    
    for c in categories:
        existing_cat_names.add(c.name)
        categories_data.append({
            "id": c.id,
            "name": c.name,
            "type": c.type,
            "icon": c.icon,
            "color": c.color,
            "is_default": c.is_default,
            "keywords": keywords_by_category.get(c.name, [])
        })

    # Collect uncategorized and orphaned keywords
    uncategorized_keywords = keywords_by_category.get("Uncategorized", [])
    
    # Check for keywords pointing to non-existent categories (orphaned)
    for cat_name, kws in keywords_by_category.items():
        if cat_name != "Uncategorized" and cat_name not in existing_cat_names:
            # Only add if we're not filtering by type OR if we decide to show orphans always
            # Ideally, orphans should show up somewhere.
            uncategorized_keywords.extend(kws)

    return {
        "success": True,
        "categories": categories_data,
        "uncategorized_keywords": uncategorized_keywords
    }

@router.post("/api/categories")
async def create_category(
    data: CategoryCreate,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Check duplicate
    exists = db.query(models.UserCategory).filter(
        models.UserCategory.user_id == current_user.id,
        models.UserCategory.name == data.name,
        models.UserCategory.type == data.type,
        models.UserCategory.is_active == True
    ).first()
    
    if exists:
        return {"success": False, "message": "Kategori sudah ada"}
        
    new_cat = models.UserCategory(
        user_id=current_user.id,
        name=data.name,
        type=data.type,
        icon=data.icon,
        color=data.color,
        is_default=False
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    
    return {"success": True, "category_id": new_cat.id}

@router.put("/api/categories/{id}")
async def update_category(
    id: int,
    data: CategoryUpdate,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    cat = db.query(models.UserCategory).filter(
        models.UserCategory.id == id,
        models.UserCategory.user_id == current_user.id
    ).first()
    
    if not cat:
        return {"success": False, "message": "Category not found"}
    
    # Prevent changing system defaults logic if desired, but user likely wants to edit defaults too?
    # If is_default, maybe limit name change? For now allow all.
         
    if data.name: cat.name = data.name
    if data.type: cat.type = data.type
    if data.icon: cat.icon = data.icon
    if data.color: cat.color = data.color
    
    db.commit()
    return {"success": True}

@router.delete("/api/categories/{id}")
async def delete_category(
    id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    cat = db.query(models.UserCategory).filter(
        models.UserCategory.id == id,
        models.UserCategory.user_id == current_user.id
    ).first()
    
    if not cat:
        return {"success": False, "message": "Category not found"}
        
    # Check usage?
    # Ideally checking if transactions exist with this category name.
    # Since we store as String `name`, deleting a category doesn't cascade delete transactions, 
    # but it just hides it from the list. The old transactions remain with the string value.
    # This is actually safe behavior for string-based categories.
    
    # Soft delete
    cat.is_active = False
    db.commit()
    return {"success": True}
