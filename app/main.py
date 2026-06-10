from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta, datetime
from app.db import session, crud, models, crud_extended
from app.auth import auth
from app.ai import classifier, analyst
from app.db.models import TransactionType
from app.routes import (
    transactions, upload, recurring, goals,
    budget, analytics, backup_restore, notifications,
    settings, reports_advanced, whatsapp, predictions, keywords,
    assets, whatsapp_report, whatsapp_report_ui, categories, qna, debt
)
import os
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables and start scheduler
    models.Base.metadata.create_all(bind=session.engine)
    
    import logging
    logger = logging.getLogger(__name__)
    try:
        from app.tasks.scheduler import start_scheduler
        start_scheduler()
        logger.info("Background scheduler initialized successfully")
    except Exception as e:
        logger.error(f"Failed to start background scheduler: {e}", exc_info=True)
    
    yield
    
    # Shutdown: Stop scheduler
    try:
        from app.tasks.scheduler import stop_scheduler
        stop_scheduler()
        logger.info("Background scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

app = FastAPI(
    title="Family Finance Assistant",
    description="Advanced performance-optimized financial tracking system",
    version="2.0.0",
    lifespan=lifespan,
    debug=True
)

# Include routers
app.include_router(budget.router)
app.include_router(recurring.router)
app.include_router(goals.router)
app.include_router(notifications.router)
app.include_router(upload.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(backup_restore.router)
app.include_router(settings.router)
app.include_router(reports_advanced.router)
app.include_router(whatsapp.router)
app.include_router(predictions.router)
app.include_router(keywords.router)
app.include_router(assets.router)
app.include_router(whatsapp_report.router)
app.include_router(whatsapp_report_ui.router)
app.include_router(qna.router)
app.include_router(debt.router)

app.include_router(categories.router)

# Exception handler for authentication redirects
@app.exception_handler(HTTPException)
async def auth_exception_handler(request: Request, exc: HTTPException):
    if (exc.status_code == 307 or exc.status_code == 303) and "Location" in exc.headers:
        return RedirectResponse(url=exc.headers["Location"], status_code=exc.status_code)
    raise exc

# Static files and authentication middlewares...

# Templates and static files
from app.templates_utils import create_templates
templates = create_templates("app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    pin: str = Form(...),
    db: Session = Depends(session.get_db)
):
    user = crud.get_user_by_username(db, username)
    if not user or not crud.verify_pin(pin, user.pin_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Username atau PIN salah"}
        )
    
    access_token = auth.create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token", 
        value=access_token, 
        httponly=True, 
        secure=True, 
        samesite="lax", 
        max_age=3600 # 60 minutes
    )
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Get monthly stats
    stats = crud.get_monthly_stats(db, current_user.id)
    
    # Get previous month stats for percentage calculation
    # Get current period information
    current_year, current_month, start_day = crud.get_current_period(db, current_user.id)
    now = datetime.now()
            
    # Calculate previous period
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year

    prev_stats = crud.get_monthly_stats(db, current_user.id, year=prev_year, month=prev_month)
    
    # Calculate percentage changes
    income_change = ((stats["income"] - prev_stats["income"]) / prev_stats["income"] * 100) if prev_stats["income"] > 0 else 0
    expense_change = ((stats["expenses"] - prev_stats["expenses"]) / prev_stats["expenses"] * 100) if prev_stats["expenses"] > 0 else 0
    balance_change = ((stats["balance"] - prev_stats["balance"]) / prev_stats["balance"] * 100) if prev_stats["balance"] > 0 else 0
    
    # Get weekly stats for chart
    weekly_stats = crud.get_weekly_stats(db, current_user.id, days=7)
    
    # Get recent transactions
    transactions = crud.get_user_transactions(db, current_user.id, limit=10)
    
    # Get unread notifications count
    from app.tasks import notifications as notif_tasks
    notif_tasks.run_all_checks(db, current_user.id)  # Check and create notifications
    unread_notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True, limit=5)
    
    # Calculate daily average (actual so far)
    # User requested to exclude recurring transactions from "Rata-rata Harian"
    # Get start of current period
    from app.db.crud import get_monthly_period_dates
    start_of_period, _ = get_monthly_period_dates(current_year, current_month, start_day)
    
    # Calculate days passed in this period
    days_passed = (now - start_of_period).days + 1
    days_passed = max(1, days_passed)
    
    # Need to fetch total variable expenses for this month specifically
    total_variable_this_month = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.type == models.TransactionType.EXPENSE,
        models.Transaction.recurring_id == None, # Exclude linked recurring
        models.Transaction.created_at >= start_of_period,
        models.Transaction.created_at <= now
    ).scalar() or 0
    total_variable_this_month = float(total_variable_this_month)
    
    # Also apply the same deduplication logic (name/amount match)?
    # Ideally yes, but for dashboard speed let's rely on recurring_id for now
    # since we just ran the linking script. 
    # For consistent UX, if we did strict filtering in projection, we should probably do it here too,
    # or just accept that "Daily Average" is "Non-Recurring" only.
    
    avg_daily_actual = total_variable_this_month / days_passed
    
    # Calculate daily limit based on this actual average (or maybe we should keep limit stable?)
    # Limit logic: avg * 1.5 might be too high if based on actual high spending. 
    # Let's keep limit as is? No, previous logic was: expense / 30 * 1.5.
    # If we want a target, maybe 1/30 of income? Or 1/30 of monthly budget?
    # For now, let's just properly calculate the displayed average.
    
    # Let's preserve the old variable name 'avg_daily_expense' for compatibility but update its value logic
    # But wait, 'daily_limit' formula depends on it. 
    # If we use accurate daily average:
    # Day 1: Spent 100k. Avg = 100k. Limit = 150k.
    # Day 20: Spent 2000k. Avg = 100k. Limit = 150k.
    # This seems fine.
    
    avg_daily_expense = avg_daily_actual
    daily_limit = avg_daily_expense * 1.5
    
    # Get total assets value
    total_assets = crud_extended.get_asset_total_value(db, current_user.id)
    
    if "category_breakdown" in stats:
        stats["category_breakdown"] = dict(sorted(
            stats["category_breakdown"].items(), 
            key=lambda item: item[1], 
            reverse=True
        ))
    
    # Get projected expenses for next month
    projected = crud_extended.get_projected_expenses(db, current_user.id)

    # Get active recurring transactions for dashboard display
    recurring_transactions = crud_extended.get_recurring_transactions(db, current_user.id, active_only=True)
    
    # Get budget overview for dashboard (similar to budget.py logic)
    # Use synchronized year/month to match stats
    budgets_list = crud_extended.get_budgets(db, current_user.id, current_year, current_month)
    
    # Create a budget map for instant lookup (FIX N+1)
    budget_map = {b.category: b for b in budgets_list}
    
    # Get user expense categories
    user_cats = db.query(models.UserCategory).filter(
        models.UserCategory.user_id == current_user.id,
        models.UserCategory.is_active == True,
        models.UserCategory.type == 'Pengeluaran'
    ).all()
    
    # Calculate budget vs actual for each category
    budget_data = []
    for cat in user_cats:
        # Use our pre-loaded map instead of querying DB again (Optimization)
        budget = budget_map.get(cat.name)
        actual = stats.get("category_breakdown", {}).get(cat.name, 0)
        
        # Calculate budget amount
        budget_amount = 0
        percentage_val = None
        
        if budget:
            if budget.percentage and budget.percentage > 0:
                # Dynamic calculation based on income
                budget_amount = (float(budget.percentage) / 100) * float(stats.get("income", 0))
                percentage_val = float(budget.percentage)
            else:
                budget_amount = float(budget.amount)
        
        if budget_amount > 0:  # Only include categories with budgets
            percentage = (float(actual) / float(budget_amount) * 100) if budget_amount > 0 else 0
            
            budget_data.append({
                "category": cat.name,
                "budget": budget_amount,
                "percentage_budget": percentage_val,
                "actual": actual,
                "remaining": budget_amount - actual,
                "percentage": percentage,
                "is_over": actual > budget_amount
            })
    
    # Sort budgets by percentage (highest first - those closest to/over budget limit)
    budgets_sorted = sorted(budget_data, key=lambda x: x.get('percentage', 0), reverse=True)
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "stats": stats,
            "transactions": transactions,
            "categories": [c.name for c in db.query(models.UserCategory).filter(models.UserCategory.user_id==current_user.id).all()],
            "unread_notifications": unread_notifications or [],
            "weekly_stats": weekly_stats,
            "income_change": income_change,
            "expense_change": expense_change,
            "balance_change": balance_change,
            "daily_limit": daily_limit,
            "total_assets": total_assets,
            "projected": projected,
            "avg_daily": avg_daily_expense,
            "recurring_transactions": recurring_transactions,
            "start_day": start_day,
            "budgets": budgets_sorted,  # Add sorted budgets
        }
    )

@app.get("/api/dashboard/cash-flow")
async def get_cash_flow_data(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    """API endpoint to fetch cash flow data based on timeframe"""
    from fastapi.responses import JSONResponse
    from zoneinfo import ZoneInfo
    
    try:
        from fastapi.responses import JSONResponse
        from zoneinfo import ZoneInfo
        
        tz = ZoneInfo("Asia/Jakarta")
        now = datetime.now(tz)
        
        # 1. Parse & Validate Dates
        if not start_date or not end_date:
            # Default: Start of current month to Today
            dt_end = now
            dt_start = dt_end.replace(day=1)
        else:
            try:
                dt_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=tz)
                dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=tz)
            except ValueError:
                return JSONResponse({"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}, status_code=400)
        
        # Ensure Start <= End
        if dt_start > dt_end:
            dt_start, dt_end = dt_end, dt_start
            
        # 2. Set Time Boundaries (Server TZ)
        # start at 00:00:00, end at 23:59:59
        range_start = dt_start.replace(hour=0, minute=0, second=0, microsecond=0)
        range_end = dt_end.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # 3. Determine Grouping
        days_diff = (range_end - range_start).days
        
        if days_diff <= 31:
            group_by = "day"
        elif days_diff <= 365:
            group_by = "month"
        else:
            group_by = "year"
            
        # 4. Fetch Transactions
        transactions = db.query(models.Transaction).filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.created_at >= range_start,
            models.Transaction.created_at <= range_end,
            models.Transaction.is_deleted == False
        ).all()
        
        # 5. Aggregate Data
        chart_data_map = {} # Key -> {label, income, expense}
        total_income = 0
        total_expense = 0
        category_breakdown = {}
        
        def get_key(dt):
            # Ensure dt is aware or force it
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            else:
                dt = dt.astimezone(tz)
                
            if group_by == "day":
                return dt.strftime("%Y-%m-%d"), dt.strftime("%d %b")
            elif group_by == "month":
                return dt.strftime("%Y-%m"), dt.strftime("%b %Y")
            else:
                return dt.strftime("%Y"), dt.strftime("%Y")

        for t in transactions:
            val = float(t.amount)
            if t.type == TransactionType.INCOME:
                total_income += val
            elif t.type == TransactionType.EXPENSE:
                total_expense += val
                cat = t.category or "Lainnya"
                category_breakdown[cat] = category_breakdown.get(cat, 0) + val
                
            # Chart Data (Include all types if desired, or strictly Income/Expense)
            # Typically Cash Flow is Income vs Expense. 
            # If user has Savings, where do they go? Usually separate or Expense.
            # Assuming strictly Income vs Expense for this specific Chart endpoint.
            
            key_sort, key_label = get_key(t.created_at)
            if key_sort not in chart_data_map:
                chart_data_map[key_sort] = {"label": key_label, "income": 0, "expense": 0}
            
            if t.type == TransactionType.INCOME:
                chart_data_map[key_sort]["income"] += val
            elif t.type == TransactionType.EXPENSE:
                chart_data_map[key_sort]["expense"] += val

        # Sort chart data
        sorted_keys = sorted(chart_data_map.keys())
        chart_output = [chart_data_map[k] for k in sorted_keys]
        
        # Calculate Stats
        total_balance = total_income - total_expense
        denom = days_diff if days_diff > 0 else 1
        avg_daily = total_expense / denom
        
        # 6. Construct Response
        return JSONResponse({
            "success": True,
            "period": {
                "start": range_start.strftime("%Y-%m-%d"),
                "end": range_end.strftime("%Y-%m-%d"),
                "group_by": group_by
            },
            "summary": {
                "income": total_income,
                "expense": total_expense,
                "balance": total_balance,
                "avg_daily": avg_daily
            },
            "chart": chart_output,
            "category_breakdown": category_breakdown
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({
            "success": False, 
            "error": str(e)
        }, status_code=500)

@app.get("/add", response_class=RedirectResponse)
async def add_page_redirect():
    return RedirectResponse(url="/transactions", status_code=303)

@app.post("/add")
async def add_transaction_redirect(
    request: Request,
    text: str = Form(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Forward the POST request logic if needed, but simpler to redirect user to new page
    # Or, to be "nice", handles the legacy post by forwarding to new logic? 
    # For now, let's keep the logic here OR better: redirect POST?
    # Browsers cannot easily redirect POST with data to another POST.
    # So we should probably keep the handler here but call the new logical flow, OR just keep it working as legacy support.
    # Decision: Redirect GET only. For POST, we can keep the handler functioning but deprecated, or just move logic.
    # But wait, implementation plan said "Redirect /add and /reports". 
    # Let's simple redirect GETs. For POST /add from old forms (if any cached), we can process it and redirect to /transactions.
    
    # Re-use logic or call into new route? 
    # Let's just keep the logic here for a bit for legacy support, but change redirect target to /transactions
    # Actually, simpler: The goal is to MERGE.
    # The new form posts to /transactions/add.
    # The old form posts to /add.
    # I will move the logic to transactions.py (done) and make this just a wrapper or delete it if I'm sure no one uses old.
    # Safest: Keep logic here but redirect to /transactions.
    from app.ai import classifier
    
    user_cats = db.query(models.UserCategory).filter(
        models.UserCategory.user_id == current_user.id,
        models.UserCategory.is_active == True
    ).all()
    cat_names = [c.name for c in user_cats]
    cat_types = {c.name: c.type for c in user_cats}
    
    classified = classifier.classify_transaction(text, cat_names, category_types=cat_types)
    
    crud.create_transaction(
        db=db,
        user_id=current_user.id,
        transaction_type=classified["type"],
        amount=classified["amount"],
        category=classified["category"],
        description=classified["description"],
        raw_input=text,
        tags=classified.get("tags")
    )
    return RedirectResponse(url="/transactions", status_code=303)


@app.get("/assistant", response_class=HTMLResponse)
async def assistant_page(
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    stats = crud.get_monthly_stats(db, current_user.id)
    analysis = analyst.analyze_finances(stats)
    unread_notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True, limit=5)
    
    return templates.TemplateResponse(
        "assistant.html",
        {
            "request": request,
            "user": current_user,
            "stats": stats,
            "analysis": analysis,
            "unread_notifications": unread_notifications or []
        }
    )

@app.get("/reports", response_class=RedirectResponse)
async def reports_page_redirect():
    return RedirectResponse(url="/transactions", status_code=301)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    return response

# API endpoint for AJAX requests
@app.post("/api/classify")
async def api_classify(
    text: str = Form(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Get user categories for context
    user_cats = db.query(models.UserCategory).filter(
        models.UserCategory.user_id == current_user.id,
        models.UserCategory.is_active == True
    ).all()
    cat_names = [c.name for c in user_cats]
    cat_types = {c.name: c.type for c in user_cats}
    
    classified = classifier.classify_transaction(text, cat_names, category_types=cat_types)
    
    return {
        "type": classified["type"].value,
        "amount": classified["amount"],
        "category": classified["category"],
        "description": classified["description"]
    }




