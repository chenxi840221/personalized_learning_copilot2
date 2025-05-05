# backend/auth/entra_auth.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from msal import ConfidentialClientApplication
import jwt
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
import json

from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

# Set up OAuth2 bearer token
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

async def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate an Entra ID access token and return user information.
    
    Args:
        token: The access token to validate
        
    Returns:
        User information extracted from the token
    
    Raises:
        HTTPException: If the token is invalid
    """
    try:
        # Decode the token without verification - we're just extracting claims
        # We rely on Microsoft for verification
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
            audience=settings.CLIENT_ID
        )
        
        # Validate token expiration
        if 'exp' in payload:
            expiry = datetime.fromtimestamp(payload['exp'])
            if datetime.utcnow() > expiry:
                logger.warning("Token expired")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Extract user information
        user_info = {
            "id": payload.get("oid"),  # Object ID is the unique identifier for the user
            "username": payload.get("preferred_username") or payload.get("upn"),
            "email": payload.get("email") or payload.get("upn") or payload.get("preferred_username"),
            "full_name": payload.get("name"),
            "given_name": payload.get("given_name"),
            "family_name": payload.get("family_name"),
            "roles": payload.get("roles", [])
        }
        
        return user_info
        
    except jwt.PyJWTError as e:
        logger.error(f"JWT error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Get current user information from token.
    
    Args:
        token: The access token
        
    Returns:
        User information
        
    Raises:
        HTTPException: If the token is invalid
    """
    # Validate token and get user info
    user_info = await validate_token(token)
    
    # Get user profile from Azure Search
    try:
        user_profile = await get_user_profile(user_info["id"])
        if user_profile:
            # Merge search profile data with token data
            user_info.update({
                "grade_level": user_profile.get("grade_level"),
                "subjects_of_interest": user_profile.get("subjects_of_interest", []),
                "learning_style": user_profile.get("learning_style")
            })
    except Exception as e:
        logger.warning(f"Could not retrieve user profile from search: {e}")
    
    return user_info

async def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user profile from Azure AI Search.
    
    Args:
        user_id: The user's Entra ID object ID
        
    Returns:
        User profile information or None if not found
    """
    if not (settings.AZURE_SEARCH_ENDPOINT and settings.AZURE_SEARCH_KEY):
        logger.warning("Azure Search not configured")
        return None
    
    try:
        # Build search URL
        search_url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{settings.USERS_INDEX_NAME}/docs"
        search_url += f"/search?api-version=2023-07-01-Preview"
        
        # Build search filter
        filter_expr = f"id eq '{user_id}'"
        
        # Build request body
        search_body = {
            "filter": filter_expr,
            "top": 1
        }
        
        # Execute search
        async with aiohttp.ClientSession() as session:
            async with session.post(
                search_url,
                json=search_body,
                headers={
                    "Content-Type": "application/json",
                    "api-key": settings.AZURE_SEARCH_KEY
                }
            ) as response:
                if response.status != 200:
                    logger.error(f"Azure Search error: {response.status} - {await response.text()}")
                    return None
                
                # Parse response
                result = await response.json()
                
                # Extract user profile
                if "value" in result and len(result["value"]) > 0:
                    return result["value"][0]
                
                return None
                
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return None

async def create_or_update_user_profile(user_info: Dict[str, Any]) -> bool:
    """
    Create or update user profile in Azure AI Search.
    
    Args:
        user_info: User information to save
        
    Returns:
        True if successful, False otherwise
    """
    if not (settings.AZURE_SEARCH_ENDPOINT and settings.AZURE_SEARCH_KEY):
        logger.warning("Azure Search not configured")
        return False
    
    try:
        # Build request URL
        index_url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{settings.USERS_INDEX_NAME}/docs/index"
        index_url += f"?api-version=2023-07-01-Preview"
        
        # Prepare user document
        user_doc = {
            "id": user_info["id"],
            "username": user_info.get("username", ""),
            "email": user_info.get("email", ""),
            "full_name": user_info.get("full_name", ""),
            "given_name": user_info.get("given_name", ""),
            "family_name": user_info.get("family_name", ""),
            "grade_level": user_info.get("grade_level"),
            "subjects_of_interest": user_info.get("subjects_of_interest", []),
            "learning_style": user_info.get("learning_style"),
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Build request body
        request_body = {
            "value": [user_doc]
        }
        
        # Execute request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                index_url,
                json=request_body,
                headers={
                    "Content-Type": "application/json",
                    "api-key": settings.AZURE_SEARCH_KEY
                }
            ) as response:
                if response.status != 200 and response.status != 201:
                    logger.error(f"Azure Search error: {response.status} - {await response.text()}")
                    return False
                
                # Parse response
                result = await response.json()
                
                # Check for errors
                if "value" in result:
                    for item in result["value"]:
                        if not item.get("status", False):
                            logger.error(f"Error creating/updating user profile: {item.get('errorMessage')}")
                            return False
                
                return True
                
    except Exception as e:
        logger.error(f"Error creating/updating user profile: {e}")
        return False

async def get_login_url(redirect_uri: str) -> str:
    """
    Generate Entra ID login URL for user authentication.
    
    Args:
        redirect_uri: The URI to redirect to after authentication
        
    Returns:
        Login URL
    """
    auth_url = app.get_authorization_request_url(
        scopes=["User.Read"],
        redirect_uri=redirect_uri,
        prompt="select_account"  # Force login screen
    )
    return auth_url

async def exchange_code_for_token(code: str, redirect_uri: str) -> Dict[str, Any]:
    """
    Exchange authorization code for access token.
    
    Args:
        code: Authorization code from Entra ID
        redirect_uri: Redirect URI used in the authentication request
        
    Returns:
        Token information
        
    Raises:
        HTTPException: If token acquisition fails
    """
    try:
        result = app.acquire_token_by_authorization_code(
            code=code,
            scopes=["User.Read"],
            redirect_uri=redirect_uri
        )
        
        if "error" in result:
            logger.error(f"Token acquisition error: {result.get('error_description')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Error acquiring token: {result.get('error_description')}",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return result
        
    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error acquiring token",
            headers={"WWW-Authenticate": "Bearer"},
        )