from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime
# Learning Style Enum
class LearningStyle(str, Enum):
    VISUAL = "visual"
    AUDITORY = "auditory"
    READING_WRITING = "reading_writing"
    KINESTHETIC = "kinesthetic"
    MIXED = "mixed"
# Token models
class Token(BaseModel):
    access_token: str
    token_type: str
class TokenData(BaseModel):
    username: Optional[str] = None
# User models
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    grade_level: Optional[int] = None
    subjects_of_interest: List[str] = []
    areas_for_improvement: List[str] = []
    learning_style: Optional[LearningStyle] = None
    is_active: bool = True
class UserCreate(UserBase):
    password: str
    confirm_password: Optional[str] = None
class User(UserBase):
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    class Config:
        orm_mode = True
class UserInDB(User):
    hashed_password: str
