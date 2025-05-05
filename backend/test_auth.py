#!/usr/bin/env python3
# test_auth.py
import sys
import jwt
import requests
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Settings
SERVER_URL = "http://localhost:8001"
SECRET_KEY = "your_secret_key_here"  # Same as in settings.py
ALGORITHM = "HS256"

def get_token_directly():
    """Create a token directly using the same method as test-token endpoint."""
    # Create token data
    token_data = {"sub": "test-user-123"}
    
    # Set expiration
    expire = datetime.utcnow() + timedelta(minutes=60)
    token_data.update({"exp": expire})
    
    # Create token
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return token

def test_auth_flow():
    """Test the authentication flow."""
    # Get token from API
    try:
        logger.info("Getting token from API...")
        response = requests.get(f"{SERVER_URL}/auth/test-token")
        if response.status_code == 200:
            token_info = response.json()
            token = token_info.get("access_token")
            logger.info(f"Got token from API: {token[:20]}...")
        else:
            logger.error(f"Failed to get token from API: {response.status_code} - {response.text}")
            # Create token directly
            token = get_token_directly()
            logger.info(f"Created token directly: {token[:20]}...")
    except Exception as e:
        logger.error(f"Error getting token from API: {e}")
        # Create token directly
        token = get_token_directly()
        logger.info(f"Created token directly: {token[:20]}...")
    
    # Test token with /users/me endpoint
    try:
        logger.info("Testing token with /users/me endpoint...")
        response = requests.get(
            f"{SERVER_URL}/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            user_info = response.json()
            logger.info(f"Got user info: {user_info}")
        else:
            logger.error(f"Failed to get user info: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error getting user info: {e}")

if __name__ == "__main__":
    # Test auth flow
    test_auth_flow()