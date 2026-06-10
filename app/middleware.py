"""
Middleware to add common template context
"""
from fastapi import Request
from app.db import session, crud_extended

async def add_template_context(request: Request, call_next):
    """Add common context to all authenticated requests"""
    response = await call_next(request)
    
    # Only add context if user is authenticated (has access_token cookie)
    if request.cookies.get("access_token"):
        # We'll add unread_notifications in each route that needs it
        # since we need the user_id from the authenticated user
        pass
    
    return response

