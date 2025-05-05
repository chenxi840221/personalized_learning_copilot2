#!/usr/bin/env python3
# test_jwt.py
import jwt
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Secret key for JWT tokens (simple auth)
SECRET_KEY = "your_secret_key_here"  # Same as in settings.py
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_simple_token(data, expires_delta=None):
    """Create a simple JWT token for authentication when MS auth is not available."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def test_token_decode():
    """Test token creation and decoding."""
    # Create test token
    token_data = {"sub": "test-user-123"}
    token = create_simple_token(token_data)
    logger.info(f"Created token: {token}")
    
    # Test decoding with correct algorithm
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"Successfully decoded with {ALGORITHM}: {payload}")
    except Exception as e:
        logger.error(f"Error decoding with {ALGORITHM}: {e}")
    
    # Test decoding with incorrect algorithm but verify_alg=False
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["RS256"], options={"verify_alg": False})
        logger.info(f"Successfully decoded with RS256 and verify_alg=False: {payload}")
    except Exception as e:
        logger.error(f"Error decoding with RS256 and verify_alg=False: {e}")
    
    # Test decoding with multiple algorithms
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM, "RS256"])
        logger.info(f"Successfully decoded with multiple algorithms: {payload}")
    except Exception as e:
        logger.error(f"Error decoding with multiple algorithms: {e}")
    
    # Test decoding with incorrect options
    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM, "RS256"], 
            options={"verify_alg": False, "verify_signature": False}
        )
        logger.info(f"Successfully decoded with verify_signature=False: {payload}")
    except Exception as e:
        logger.error(f"Error decoding with verify_signature=False: {e}")
        
    # Test the specific situation in our code - verifying a signature with wrong algorithm
    logger.info("\nTesting Microsoft token validation approach with an HS256 token:")
    try:
        # This simulates what our Microsoft token validation is doing
        payload = jwt.decode(
            token,
            options={"verify_signature": False, "verify_aud": False},
            algorithms=["RS256"]  # Try with only RS256
        )
        logger.info(f"Microsoft token approach works: {payload}")
    except Exception as e:
        logger.error(f"Microsoft token approach fails: {e}")
    
    # Now try with both algorithms
    try:
        # This is what our updated code does
        payload = jwt.decode(
            token,
            options={"verify_signature": False, "verify_aud": False, "verify_alg": False},
            algorithms=["RS256", "HS256"]  # Try with both algorithms
        )
        logger.info(f"Updated approach works: {payload}")
    except Exception as e:
        logger.error(f"Updated approach fails: {e}")

if __name__ == "__main__":
    test_token_decode()