from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid

class ReportType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SPECIAL_ED = "special_ed"
    STANDARDIZED_TEST = "standardized_test"

class Subject(BaseModel):
    name: str
    grade: Optional[str] = None
    comments: Optional[str] = None
    achievement_level: Optional[str] = None
    areas_for_improvement: List[str] = []
    strengths: List[str] = []

class StudentReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str  # Links to the user ID
    report_type: ReportType
    school_name: Optional[str] = None
    school_year: Optional[str] = None
    term: Optional[str] = None
    grade_level: Optional[int] = None
    teacher_name: Optional[str] = None
    report_date: Optional[datetime] = None
    subjects: List[Subject] = []
    general_comments: Optional[str] = None
    attendance: Optional[Dict[str, Any]] = None
    raw_extracted_text: Optional[str] = None  # Stores the raw text from the document
    document_url: Optional[str] = None  # URL to the processed document in storage
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}
    
    # PII fields - will be encrypted
    encrypted_fields: Dict[str, str] = {}  # For storing encrypted sensitive data

class StudentReportWithEmbedding(StudentReport):
    embedding: List[float]
    embedding_model: str = "text-embedding-ada-002"