"""
WhatsApp Report API routes
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.db import session, crud_whatsapp_report, models
from app.services import report_generator
from app.auth import auth
import httpx
import os

router = APIRouter()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-webhook-secret-change-this")
BOT_API_URL = os.getenv("WHATSAPP_BOT_API_URL", "http://whatsapp-bot:3000")

class ReportScheduleRequest(BaseModel):
    is_enabled: bool = True
    report_time: str = "10:00"  # Format: "HH:MM"
    group_name: Optional[str] = None
    group_id: Optional[str] = None

@router.get("/api/whatsapp/report-schedule")
async def get_report_schedule(
    current_user: dict = Depends(auth.get_current_user_cookie),
    db: Session = Depends(session.get_db)
):
    """Get current report schedule configuration"""
    user_id = current_user.id
    schedule = crud_whatsapp_report.get_report_schedule(db, user_id)
    
    if not schedule:
        # Return default values if no schedule exists
        return JSONResponse({
            "success": True,
            "schedule": {
                "is_enabled": False,
                "report_time": "10:00",
                "group_name": None,
                "group_id": None,
                "last_sent_at": None
            }
        })
    
    return JSONResponse({
        "success": True,
        "schedule": {
            "is_enabled": schedule.is_enabled,
            "report_time": schedule.report_time,
            "group_name": schedule.group_name,
            "group_id": schedule.group_id,
            "last_sent_at": schedule.last_sent_at.isoformat() if schedule.last_sent_at else None
        }
    })

@router.post("/api/whatsapp/report-schedule")
async def create_or_update_schedule(
    request: ReportScheduleRequest,
    current_user: dict = Depends(auth.get_current_user_cookie),
    db: Session = Depends(session.get_db)
):
    """Create or update report schedule"""
    user_id = current_user.id
    
    # Validate time format
    try:
        hour, minute = map(int, request.report_time.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time")
    except:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM (e.g., 10:00)")
    
    schedule = crud_whatsapp_report.update_report_schedule(
        db,
        user_id=user_id,
        is_enabled=request.is_enabled,
        report_time=request.report_time,
        group_name=request.group_name,
        group_id=request.group_id
    )
    
    return JSONResponse({
        "success": True,
        "message": "Report schedule updated successfully",
        "schedule": {
            "is_enabled": schedule.is_enabled,
            "report_time": schedule.report_time,
            "group_name": schedule.group_name,
            "group_id": schedule.group_id
        }
    })

@router.post("/api/whatsapp/report-schedule/test")
async def test_send_report(
    current_user: dict = Depends(auth.get_current_user_cookie),
    db: Session = Depends(session.get_db)
):
    """Manually trigger report send for testing"""
    user_id = current_user.id
    
    # Get schedule to know which group to send to
    schedule = crud_whatsapp_report.get_report_schedule(db, user_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="No report schedule configured. Please configure schedule first.")
    
    try:
        # Generate report
        report_message = report_generator.generate_daily_report(db, user_id)
        
        print(f"DEBUG: Generated report length: {len(report_message)}", flush=True)
        print(f"DEBUG: Target Group: {schedule.group_name} ({schedule.group_id})", flush=True)
        print(f"DEBUG: Bot API URL: {BOT_API_URL}", flush=True)

        payload = {
            "group_name": schedule.group_name,
            "group_id": schedule.group_id,
            "message": report_message
        }
        
        # Send via WhatsApp bot
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"DEBUG: Sending payload to {BOT_API_URL}/send-message", flush=True)
            response = await client.post(
                f"{BOT_API_URL}/send-message",
                json=payload,
                headers={
                    "X-Webhook-Secret": WEBHOOK_SECRET,
                    "Content-Type": "application/json"
                }
            )
            
            print(f"DEBUG: Bot Response Status: {response.status_code}", flush=True)
            print(f"DEBUG: Bot Response Body: {response.text}", flush=True)

            if response.status_code == 200:
                # Update last_sent_at
                crud_whatsapp_report.update_last_sent(db, schedule.id)
                
                return JSONResponse({
                    "success": True,
                    "message": "Report sent successfully",
                    "report_preview": report_message[:200] + "..." if len(report_message) > 200 else report_message
                })
            else:
                print(f"ERROR: Failed to send message. Status: {response.status_code}, Body: {response.text}", flush=True)
                return JSONResponse({
                    "success": False,
                    "error": f"Failed to send message: {response.text}"
                }, status_code=500)
                
    except Exception as e:
        print(f"ERROR: Exception in test_send_report: {str(e)}", flush=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@router.get("/api/whatsapp/groups")
async def get_whatsapp_groups(
    current_user: dict = Depends(auth.get_current_user_cookie),
    db: Session = Depends(session.get_db)
):
    """Get list of WhatsApp groups from database"""
    try:
        # Fetch known groups from database
        groups = db.query(models.WhatsAppGroup).filter(models.WhatsAppGroup.is_allowed == True).all()
        
        group_data = []
        for g in groups:
            group_data.append({
                "id": g.group_id,
                "name": g.name,
                "isAllowed": True
            })
            
        return JSONResponse({
            "success": True,
            "groups": group_data
        })
                
    except Exception as e:
        print(f"Error fetching groups: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "groups": []
        }, status_code=500)
@router.get("/api/whatsapp/connection-status")
async def get_whatsapp_connection_status(
    db: Session = Depends(session.get_db)
):
    """
    Get WhatsApp Bot connection status and QR code
    """
    try:
        import httpx
        BOT_API_URL = os.getenv("WHATSAPP_BOT_API_URL", "http://whatsapp-bot:3000")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{BOT_API_URL}/status")
                if response.status_code == 200:
                    data = response.json()
                    return JSONResponse({
                        "success": True,
                        "status": data.get("status", "unknown"),
                        "qr": data.get("qr")
                    })
                else:
                    return JSONResponse({
                        "success": False,
                        "status": "error",
                        "error": "Bot returned non-200 status"
                    }, status_code=503)
            except httpx.RequestError as exc:
                print(f"Connection error to bot: {exc}")
                return JSONResponse({
                    "success": False,
                    "status": "error",
                    "error": "Bot unreachable"
                }, status_code=503)
                
    except Exception as e:
        print(f"Error fetching whatsapp status: {e}")
        return JSONResponse({
            "success": False,
            "status": "error",
            "error": str(e)
        }, status_code=500)

@router.post("/api/whatsapp/logout")
async def logout_whatsapp_session(
    db: Session = Depends(session.get_db)
):
    """
    Force logout/reset WhatsApp session
    """
    try:
        import httpx
        BOT_API_URL = os.getenv("WHATSAPP_BOT_API_URL", "http://whatsapp-bot:3000")
        WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{BOT_API_URL}/logout",
                headers={"X-Webhook-Secret": WEBHOOK_SECRET}
            )
            
            if response.status_code == 200:
                return JSONResponse({
                    "success": True,
                    "message": "Session reset successfully"
                })
            else:
                return JSONResponse({
                    "success": False,
                    "error": "Failed to logout"
                }, status_code=response.status_code)
                
    except Exception as e:
        print(f"Error logging out whatsapp: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)
