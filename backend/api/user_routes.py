# backend/api/user_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List

from auth.authentication import get_current_user

# Create router
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get the current user's profile.
    
    Args:
        current_user: Current authenticated user from token
        
    Returns:
        User profile information
    """
    return current_user