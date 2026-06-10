"""
Routes for transaction management (edit, delete)
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db import session, crud, models, crud_new_features, crud_extended
from app.auth import auth
from app.db.models import TransactionType

router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

@router.get("/transaction/{transaction_id}", response_class=HTMLResponse)
async def view_transaction(
    transaction_id: int,
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Get edit history
    edits = db.query(models.TransactionEdit).filter(
        models.TransactionEdit.transaction_id == transaction_id
    ).order_by(models.TransactionEdit.created_at.desc()).all()
    
    # Get photos
    photos = transaction.photos
    
    # Get unread notifications
    unread_notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True, limit=5)
    
    return templates.TemplateResponse(
        "transaction_detail.html",
        {
            "request": request,
            "user": current_user,
            "transaction": transaction,
            "edits": edits,
            "photos": photos,
            "photos": photos,
            "categories": [c.name for c in db.query(models.UserCategory).filter(models.UserCategory.user_id==current_user.id, models.UserCategory.is_active==True).all()],
            "unread_notifications": unread_notifications or []
        }
    )

@router.get("/transaction/{transaction_id}/edit", response_class=HTMLResponse)
async def edit_transaction_page(
    transaction_id: int,
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == current_user.id,
        models.Transaction.is_deleted == False
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    unread_notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True, limit=5)
    return templates.TemplateResponse(
        "transaction_edit.html",
        {
            "request": request,
            "user": current_user,
            "transaction": transaction,
            "transaction": transaction,
            "categories": [c.name for c in db.query(models.UserCategory).filter(models.UserCategory.user_id==current_user.id, models.UserCategory.is_active==True).all()],
            "unread_notifications": unread_notifications or []
        }
    )

@router.post("/transaction/{transaction_id}/edit")
async def update_transaction(
    transaction_id: int,
    request: Request,
    amount: float = Form(None),
    category: str = Form(None),
    description: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    transaction = crud_new_features.update_transaction(
        db, transaction_id, current_user.id,
        amount=amount, category=category,
        description=description, notes=notes
    )
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return RedirectResponse(url=f"/transaction/{transaction_id}", status_code=303)

@router.post("/transaction/{transaction_id}/delete")
async def delete_transaction_route(
    transaction_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    success = crud_new_features.delete_transaction(db, transaction_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/transaction/{transaction_id}/restore")
async def restore_transaction_route(
    transaction_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    transaction = crud_new_features.restore_transaction(db, transaction_id, current_user.id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return RedirectResponse(url=f"/transaction/{transaction_id}", status_code=303)


@router.get("/transactions", response_class=HTMLResponse)
async def transactions_page(
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie),
    search: str = None,
    category: str = None,
    transaction_type: str = None,
    year: int = None,
    month: int = None,
    page: int = 1,
    per_page: int = 20
):
    # 1. Get transactions using efficient SQL pagination
    offset = (page - 1) * per_page
    
    if search or category or transaction_type or (year and month):
        cat_enum = category if category else None
        
        type_enum = None
        if transaction_type:
            tt_upper = transaction_type.upper()
            if tt_upper in TransactionType.__members__:
                type_enum = TransactionType[tt_upper]
        
        # Calculate date range if year and month are provided
        start_date, end_date = None, None
        if year and month:
            # Get user's start of month preference
            pref = db.query(models.UserPreference).filter(models.UserPreference.user_id == current_user.id).first()
            start_day = pref.start_of_month if pref else 1
            start_date, end_date = crud.get_monthly_period_dates(year, month, start_day)
        
        # Use refactored search_transactions with limit/offset
        transactions_list, total_transactions = crud_extended.search_transactions(
            db, current_user.id,
            search_term=search,
            category=cat_enum,
            transaction_type=type_enum,
            start_date=start_date,
            end_date=end_date,
            limit=per_page,
            offset=offset
        )
    else:
        # Standard list: Use a new specific efficient query for the main list
        # We can implement a specialized one or use search_transactions with no filters
        transactions_list, total_transactions = crud_extended.search_transactions(
            db, current_user.id,
            limit=per_page,
            offset=offset
        )
    
    # Calculate pagination stats
    total_pages = (total_transactions + per_page - 1) // per_page if total_transactions > 0 else 1
    
    # Stats for Charts
    stats = crud.get_monthly_stats(db, current_user.id)
    multi_month = crud_extended.get_multi_month_stats(db, current_user.id, months=6)
    
    # Notifications
    unread_notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True, limit=5)
    
    return templates.TemplateResponse(
        "transactions.html",
        {
            "request": request,
            "user": current_user,
            "stats": stats,
            "transactions": transactions_list,
            "multi_month": multi_month,
            "categories": [c.name for c in db.query(models.UserCategory).filter(models.UserCategory.user_id==current_user.id).all()],
            "unread_notifications": unread_notifications or [],
            "search": search,
            "category": category,
            "transaction_type": transaction_type,
            "year": year,
            "month": month,
            "page": page,
            "per_page": per_page,
            "total_transactions": total_transactions,
            "total_pages": total_pages
        }
    )

@router.post("/transactions/add")
async def add_transaction_route(
    request: Request,
    text: str = Form(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    from app.ai import classifier
    
    # Get user categories for context
    user_cats = db.query(models.UserCategory).filter(
        models.UserCategory.user_id == current_user.id,
        models.UserCategory.is_active == True
    ).all()
    cat_names = [c.name for c in user_cats]
    cat_types = {c.name: c.type for c in user_cats}
    
    # Classify transaction using AI
    classified = classifier.classify_transaction(text, cat_names, category_types=cat_types)
    
    # Create transaction
    transaction = crud.create_transaction(
        db=db,
        user_id=current_user.id,
        transaction_type=classified["type"],
        amount=classified["amount"],
        category=classified["category"],
        description=classified["description"],
        raw_input=text,
        tags=classified.get("tags")
    )
    
    # Trigger Budget Check immediately for the specific category
    if transaction.type == TransactionType.EXPENSE:
        try:
            from app.tasks import notifications
            notifications.check_budget_alerts(db, current_user.id, transaction.category)
        except Exception as e:
            print(f"Error checking budget alerts: {e}")
            
    return RedirectResponse(url="/transactions", status_code=303)


