# backend/auth/authentication.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from azure.identity import ClientSecretCredential, InteractiveBrowserCredential
from msal import ConfidentialClientApplication
import jwt
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from config.settings import Settings
from auth.entra_auth import get_current_user as entra_get_current_user

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

# Set up OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"https://login.microsoftonline.com/{settings.TENANT_ID}/oauth2/v2.0/token",
    auto_error=True
)

# Initialize Entra ID application
app = ConfidentialClientApplication(
    client_id=settings.CLIENT_ID,
    client_credential=settings.CLIENT_SECRET,
    authority=f"https://login.microsoftonline.com/{settings.TENANT_ID}"
)

# Use Entra ID authentication only
get_current_user = entra_get_current_user

async def get_ms_login_url(redirect_uri):
    """Generate Microsoft login URL."""
    if app is None:
        logger.error("Microsoft authentication not configured")
        return None
        
    auth_url = app.get_authorization_request_url(
        scopes=["User.Read"],
        redirect_uri=redirect_uri,
        prompt="select_account"  # Force login screen
    )
    return auth_url

async def get_token_from_code(auth_code, redirect_uri):
    """Exchange authorization code for token."""
    if app is None:
        logger.error("Microsoft authentication not configured")
        return None
        
    result = app.acquire_token_by_authorization_code(
        code=auth_code,
        scopes=["User.Read"],
        redirect_uri=redirect_uri
    )
    
    if "error" in result:
        logger.error(f"Error getting token: {result.get('error_description')}")
        raise Exception(f"Error getting token: {result.get('error_description')}")
        
    return result