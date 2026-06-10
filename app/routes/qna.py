from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db import session
from app.auth import auth
from app.db import models
from app.services.financial_qna import FinancialQnAService

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request
import os
from app.db.models import User

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-change-this")

router = APIRouter(
    prefix="/api/qna",
    tags=["qna"],
    responses={404: {"description": "Not found"}},
)

class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    answer: str

@router.post("/ask", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    db: Session = Depends(session.get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    user = current_user
    
    # If no cookie session, check for webhook secret (Bot Access)
    if not user:
        if x_webhook_secret == WEBHOOK_SECRET:
            # Bot access: Use default user (first user)
            # In future, we might want to map sender number to user
            user = db.query(models.User).first()
            if not user:
                 raise HTTPException(status_code=404, detail="No default user found")
        else:
            # No auth and no valid secret -> Redirect (mimic original behavior) or 401
            # Since original was get_current_user_cookie which raises 303, we should probably return 401 for API 
            # OR raise the same 303 to strictly match previous behavior for browser? 
            # But browser JS usually prefers 401. Let's raise 401 for API clarity, 
            # unless the frontend purely relies on redirect. 
            # Given this is `api/qna/ask`, it's an API call.
            raise HTTPException(status_code=401, detail="Not authenticated")

    service = FinancialQnAService(db, user.id)
    answer = service.process_question(request.question)
    return QuestionResponse(answer=answer)
