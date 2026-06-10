"""
Backup and restore routes
"""
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from app.db import session, models, crud_extended
from app.auth import auth
from app.services import backup

router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

@router.get("/backup", response_class=HTMLResponse)
async def backup_page(
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    unread_notifications = crud_extended.get_notifications(db, current_user.id, unread_only=True, limit=5)
    return templates.TemplateResponse(
        "backup.html",
        {
            "request": request,
            "user": current_user,
            "unread_notifications": unread_notifications or []
        }
    )

@router.post("/backup/export-csv")
async def export_csv(
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    filepath = backup.export_transactions_csv(db, current_user.id)
    return FileResponse(
        filepath,
        media_type="text/csv",
        filename=Path(filepath).name
    )

@router.post("/backup/export-full")
async def export_full(
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    filepath = backup.export_full_backup(db, current_user.id)
    return FileResponse(
        filepath,
        media_type="application/json",
        filename=Path(filepath).name
    )

@router.post("/backup/import")
async def import_backup_file(
    file: UploadFile = File(...),
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Save uploaded file
    upload_path = Path("app/static/backups") / f"import_{current_user.id}_{file.filename}"
    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Import
    try:
        result = backup.import_backup(db, current_user.id, str(upload_path))
        return RedirectResponse(url="/backup?success=1", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

