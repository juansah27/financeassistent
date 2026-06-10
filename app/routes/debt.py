from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.db import session, crud, models, crud_new_features
from app.auth import auth
from app.ai import debt_classifier
import os

router = APIRouter(
    prefix="/api/debt",
    tags=["debt"]
)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-change-this")

class DebtCreate(BaseModel):
    type: str
    creditor: str
    total_amount: float
    name: Optional[str] = None
    tenor: Optional[int] = None
    interest_rate: Optional[float] = None
    installment_amount: Optional[float] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None

class DebtPayment(BaseModel):
    amount: float
    notes: Optional[str] = None
    transaction_id: Optional[int] = None

class DebtParseRequest(BaseModel):
    text: str

@router.get("/")
async def list_debts(
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_optional),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret")
):
    user = current_user
    if not user and x_webhook_secret == WEBHOOK_SECRET:
        user = db.query(models.User).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    debts = crud_new_features.get_debts(db, user.id)
    return {"success": True, "debts": debts}

@router.get("/summary/stats")
async def debt_stats(
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    summary = crud_new_features.get_debt_summary(db, current_user.id)
    return {"success": True, "summary": summary}

@router.post("/")
async def create_new_debt(
    data: DebtCreate,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_optional),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret")
):
    user = current_user
    if not user and x_webhook_secret == WEBHOOK_SECRET:
        user = db.query(models.User).first()
        
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    debt = crud_new_features.create_debt(
        db, user.id, **data.dict()
    )
    return {"success": True, "debt": debt}

@router.post("/{debt_id}/pay")
async def pay_debt(
    debt_id: int,
    data: DebtPayment,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_optional),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret")
):
    user = current_user
    if not user and x_webhook_secret == WEBHOOK_SECRET:
        user = db.query(models.User).first()
        
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    debt = crud_new_features.record_debt_payment(
        db, debt_id, user.id, data.amount, data.transaction_id, data.notes
    )
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
        
    return {"success": True, "debt": debt}

@router.post("/parse")
async def parse_debt_input(data: DebtParseRequest):
    result = debt_classifier.classify_debt(data.text)
    return result
