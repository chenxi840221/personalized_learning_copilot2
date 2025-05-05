from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict
# Simple authentication settings
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# Password handling
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# OAuth2 password bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# Mock user database
fake_users_db = {
    "testuser": {
        "username": "testuser",
        "email": "user@example.com",
        "full_name": "Test User",
        "hashed_password": pwd_context.hash("password"),
        "is_active": True
    }
}
def verify_password(plain_password, hashed_password):
    """Verify password against hashed version."""
    return pwd_context.verify(plain_password, hashed_password)
def get_password_hash(password):
    """Hash password."""
    return pwd_context.hash(password)
def get_user(username: str):
    """Get user from database."""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return user_dict
    return None
def authenticate_user(username: str, password: str):
    """Authenticate user."""
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username=username)
    if user is None:
        raise credentials_exception
    return user
