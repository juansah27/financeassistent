from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.db import session, crud_extended, models
from app.auth import auth
from app.db.models import AssetType

router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

@router.get("/assets", response_class=HTMLResponse)
async def assets_page(
    request: Request,
    asset_type_filter: str = None,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Get asset type filter
    filter_type = None
    if asset_type_filter:
        try:
            filter_type = AssetType[asset_type_filter.upper()]
        except KeyError:
            filter_type = None
    
    # Get assets
    assets = crud_extended.get_assets(db, current_user.id, asset_type=filter_type, active_only=True)
    
    # Get statistics
    total_value = crud_extended.get_asset_total_value(db, current_user.id)
    breakdown = crud_extended.get_asset_breakdown(db, current_user.id)
    active_count = len(assets)
    
    # Get highest value asset
    highest_asset = max(assets, key=lambda a: a.current_value) if assets else None
    
    # Calculate growth (total current vs total acquisition)
    total_acquisition = sum(a.acquisition_value for a in assets if a.acquisition_value) or 0
    growth_amount = total_value - total_acquisition if total_acquisition > 0 else 0
    growth_percentage = (growth_amount / total_acquisition * 100) if total_acquisition > 0 else 0
    
    # Get unread notifications
    unread_notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True, limit=5)
    
    return templates.TemplateResponse(
        "assets.html",
        {
            "request": request,
            "user": current_user,
            "assets": assets,
            "total_value": total_value,
            "active_count": active_count,
            "highest_asset": highest_asset,
            "growth_amount": growth_amount,
            "growth_percentage": growth_percentage,
            "breakdown": breakdown,
            "asset_types": [t for t in AssetType],
            "current_filter": asset_type_filter,
            "unread_notifications": unread_notifications or []
        }
    )

@router.post("/assets")
async def create_asset(
    request: Request,
    name: str = Form(...),
    asset_type: str = Form(...),
    current_value: float = Form(...),
    acquisition_date: str = Form(None),
    acquisition_value: float = Form(None),
    quantity: float = Form(None),
    unit: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    try:
        # Convert asset type
        asset_type_enum = AssetType[asset_type.upper()]
        
        # Parse acquisition date
        acq_date = None
        if acquisition_date:
            acq_date = datetime.fromisoformat(acquisition_date.replace('Z', '+00:00'))
        
        # Create asset
        crud_extended.create_asset(
            db, current_user.id, asset_type_enum, name,
            current_value, acq_date, acquisition_value,
            quantity, unit, notes
        )
        
        return RedirectResponse(url="/assets", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating asset: {str(e)}")

@router.get("/assets/{asset_id}", response_class=HTMLResponse)
async def asset_detail(
    asset_id: int,
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    asset = crud_extended.get_asset_by_id(db, asset_id, current_user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get history
    history = crud_extended.get_asset_history(db, asset_id)
    
    # Calculate growth
    growth_amount = 0
    growth_percentage = 0
    if asset.acquisition_value:
        growth_amount = asset.current_value - asset.acquisition_value
        growth_percentage = (growth_amount / asset.acquisition_value * 100) if asset.acquisition_value > 0 else 0
    
    # Get unread notifications
    unread_notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True, limit=5)
    
    return templates.TemplateResponse(
        "asset_detail.html",
        {
            "request": request,
            "user": current_user,
            "asset": asset,
            "history": history,
            "growth_amount": growth_amount,
            "growth_percentage": growth_percentage,
            "asset_types": [t for t in AssetType],
            "unread_notifications": unread_notifications or []
        }
    )

@router.post("/assets/{asset_id}/edit")
async def edit_asset(
    asset_id: int,
    request: Request,
    name: str = Form(...),
    asset_type: str = Form(...),
    current_value: float = Form(...),
    acquisition_date: str = Form(None),
    acquisition_value: float = Form(None),
    quantity: float = Form(None),
    unit: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    try:
        # Get current asset
        asset = crud_extended.get_asset_by_id(db, asset_id, current_user.id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Parse acquisition date
        acq_date = None
        if acquisition_date:
            acq_date = datetime.fromisoformat(acquisition_date.replace('Z', '+00:00'))
        
        # Update asset (this will create history if value changed)
        crud_extended.update_asset(
            db, asset_id, current_user.id,
            name=name,
            current_value=current_value,
            acquisition_date=acq_date,
            acquisition_value=acquisition_value,
            quantity=quantity,
            unit=unit,
            notes=notes,
            create_history=True
        )
        
        return RedirectResponse(url=f"/assets/{asset_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating asset: {str(e)}")

@router.post("/assets/{asset_id}/update-value")
async def update_value(
    asset_id: int,
    new_value: float = Form(...),
    notes: str = Form(None),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    try:
        crud_extended.update_asset_value(db, asset_id, current_user.id, new_value, notes)
        return RedirectResponse(url=f"/assets/{asset_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating value: {str(e)}")

@router.post("/assets/{asset_id}/delete")
async def delete_asset(
    asset_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    success = crud_extended.delete_asset(db, asset_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")
    return RedirectResponse(url="/assets", status_code=303)

# Gold Price Update Endpoints
@router.post("/assets/{asset_id}/update-gold-price")
async def update_gold_price(
    asset_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Update asset value based on current gold price"""
    from app.services import gold_price
    
    try:
        result = gold_price.update_gold_asset_price(db, asset_id, current_user.id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return RedirectResponse(url=f"/assets/{asset_id}", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating gold price: {str(e)}")

@router.get("/api/gold-price/current")
async def get_gold_price(
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """Get current gold price per gram"""
    from app.services import gold_price
    
    try:
        price = gold_price.get_current_gold_price()
        
        if price is None:
            return {
                "success": False,
                "error": "Failed to fetch gold price"
            }
        
        return {
            "success": True,
            "price_per_gram": price,
            "currency": "IDR",
            "updated_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
