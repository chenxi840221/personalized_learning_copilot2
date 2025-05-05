# backend/api/auth_routes.py
from fastapi import APIRouter, HTTPException, status, Depends, Query, Body
from fastapi.responses import RedirectResponse
from typing import Dict, Any, Optional
import logging

from auth.entra_auth import (
    get_current_user, 
    get_login_url, 
    exchange_code_for_token,
    create_or_update_user_profile
)
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.get("/login")
async def login(redirect_uri: str = Query(...)):
    """
    Start the login process by redirecting to Entra ID login.
    
    Args:
        redirect_uri: URI to redirect to after authentication
        
    Returns:
        Redirect to Entra ID login
    """
    # Generate login URL
    login_url = await get_login_url(redirect_uri)
    
    # Redirect to login URL
    return RedirectResponse(url=login_url)

@router.get("/callback")
async def auth_callback(
    code: str = Query(...),
    redirect_uri: str = Query(...),
    state: Optional[str] = Query(None)
):
    """
    Handle authentication callback from Entra ID.
    
    Args:
        code: Authorization code from Entra ID
        redirect_uri: Redirect URI used in the authentication request
        state: Optional state parameter for verification
        
    Returns:
        Access token information
    """
    try:
        # Exchange code for token
        token_info = await exchange_code_for_token(code, redirect_uri)
        
        return token_info
        
    except Exception as e:
        logger.error(f"Authentication callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/profile")
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get the current user's profile.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User profile information
    """
    return current_user

@router.put("/profile")
async def update_profile(
    profile_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update the current user's profile.
    
    Args:
        profile_data: Profile data to update
        current_user: Current authenticated user
        
    Returns:
        Updated user profile information
    """
    try:
        # Merge current user data with profile updates
        updated_user = current_user.copy()
        updated_user.update({
            "grade_level": profile_data.get("grade_level", current_user.get("grade_level")),
            "subjects_of_interest": profile_data.get("subjects_of_interest", current_user.get("subjects_of_interest", [])),
            "learning_style": profile_data.get("learning_style", current_user.get("learning_style"))
        })
        
        # Save to Azure Search
        success = await create_or_update_user_profile(updated_user)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile"
            )
            
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )