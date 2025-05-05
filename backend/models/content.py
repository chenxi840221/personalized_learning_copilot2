from pydantic import BaseModel, Field, HttpUrl, AnyUrl
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import uuid
from datetime import datetime

# Content Type Enum - with extra options for flexibility
class ContentType(str, Enum):
    ARTICLE = "article"
    VIDEO = "video"
    INTERACTIVE = "interactive"
    WORKSHEET = "worksheet"
    QUIZ = "quiz"
    LESSON = "lesson"
    ACTIVITY = "activity"
    OTHER = "other"

# Difficulty Level Enum
class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    UNKNOWN = "unknown"

# Content models
class Content(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    description: Optional[str] = None
    content_type: Optional[Union[ContentType, str]] = None
    subject: Optional[str] = None
    topics: List[str] = []
    url: Optional[Union[HttpUrl, AnyUrl, str]] = None  # More flexible URL field
    source: Optional[str] = "ABC Education"
    difficulty_level: Optional[Union[DifficultyLevel, str]] = None
    grade_level: Optional[List[int]] = []
    duration_minutes: Optional[int] = None
    keywords: Optional[List[str]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = {}
    
    class Config:
        orm_mode = True
        # Allow any extra fields that might come from Azure Search
        extra = "allow"
        # Be more permissive with field values
        arbitrary_types_allowed = True
# Content with embedding model
class ContentWithEmbedding(Content):
    embedding: List[float]
    embedding_model: str = "text-embedding-ada-002"