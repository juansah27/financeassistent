from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import os
import shutil
from pathlib import Path
from app.db import session, crud_extended, models, crud_new_features
from app.auth import auth
from app.services import ocr
from datetime import datetime

router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

# Create uploads directory
UPLOAD_DIR = Path("app/static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/transaction/{transaction_id}/upload-photo")
async def upload_photo(
    transaction_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Verify transaction belongs to user
    from app.db import crud
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Save file
    file_ext = Path(file.filename).suffix
    filename = f"{transaction_id}_{datetime.now().timestamp()}{file_ext}"
    file_path = UPLOAD_DIR / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Save to database
    photo = crud_extended.add_transaction_photo(
        db, transaction_id, file.filename, f"static/uploads/{filename}"
    )
    
    # Try OCR if it's an image
    if file.content_type and file.content_type.startswith('image/'):
        try:
            ocr_result = ocr.extract_receipt_data(str(file_path))
            if ocr_result:
                from app.db.models import ReceiptOCR
                crud_new_features.create_receipt_ocr(
                    db, transaction_id, photo.id,
                    extracted_text=ocr_result.get("extracted_text"),
                    merchant_name=ocr_result.get("merchant_name"),
                    total_amount=ocr_result.get("total_amount"),
                    date_detected=datetime.fromisoformat(ocr_result.get("date")) if ocr_result.get("date") else None,
                    items=str(ocr_result.get("items", [])),
                    confidence_score=ocr_result.get("confidence", 0.0)
                )
                
                # Auto-update transaction if OCR found amount
                if ocr_result.get("total_amount"):
                    transaction.amount = ocr_result["total_amount"]
                    if ocr_result.get("merchant_name"):
                        transaction.description = ocr_result["merchant_name"]
                    db.commit()
        except Exception as e:
            print(f"OCR failed: {e}")
    
    return RedirectResponse(url=f"/transaction/{transaction_id}", status_code=303)

@router.post("/transaction/{transaction_id}/photo/{photo_id}/delete")
async def delete_photo(
    transaction_id: int,
    photo_id: int,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Verify transaction belongs to user
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Get photo and delete file
    photo = db.query(models.TransactionPhoto).filter(
        models.TransactionPhoto.id == photo_id,
        models.TransactionPhoto.transaction_id == transaction_id
    ).first()
    
    if photo:
        file_path = Path("app") / photo.file_path
        if file_path.exists():
            file_path.unlink()
        crud_extended.delete_transaction_photo(db, photo_id)
    
    return RedirectResponse(url=f"/transaction/{transaction_id}", status_code=303)

