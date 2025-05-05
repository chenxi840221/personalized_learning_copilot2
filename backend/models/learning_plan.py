from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime, timedelta
import uuid

# Activity Status Enum
class ActivityStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

# Learning Period Enum
class LearningPeriod(str, Enum):
    ONE_WEEK = "one_week"
    TWO_WEEKS = "two_weeks"
    ONE_MONTH = "one_month"
    TWO_MONTHS = "two_months"
    SCHOOL_TERM = "school_term"
    
    @staticmethod
    def to_days(period) -> int:
        """Convert learning period to approximate number of days."""
        if period == LearningPeriod.ONE_WEEK:
            return 7
        elif period == LearningPeriod.TWO_WEEKS:
            return 14
        elif period == LearningPeriod.ONE_MONTH:
            return 30
        elif period == LearningPeriod.TWO_MONTHS:
            return 60
        elif period == LearningPeriod.SCHOOL_TERM:
            return 90  # Approximately 3 months for a school term
        return 30  # Default to one month
# Learning Activity model
class LearningActivity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    content_id: Optional[str] = None
    content_url: Optional[str] = None
    duration_minutes: int
    order: int
    day: int = 1  # Which day of the plan this activity belongs to
    status: ActivityStatus = ActivityStatus.NOT_STARTED
    completed_at: Optional[datetime] = None
    learning_benefit: Optional[str] = None
    metadata: Dict[str, Any] = {}
# Learning Plan model
class LearningPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    title: str
    description: str
    subject: str
    topics: List[str] = []
    activities: List[LearningActivity] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: ActivityStatus = ActivityStatus.NOT_STARTED
    progress_percentage: float = 0.0
    metadata: Dict[str, Any] = {}
    owner_id: Optional[str] = None  # ID of the teacher who created this plan
    class Config:
        orm_mode = True
# Learning Plan Creation model
class LearningPlanCreate(BaseModel):
    subject: str
    title: Optional[str] = None
    description: Optional[str] = None
    topics: List[str] = []
    activities: List[LearningActivity] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    learning_period: Optional[LearningPeriod] = LearningPeriod.ONE_MONTH
    metadata: Dict[str, Any] = {}
# Learning Activity Update
class LearningActivityUpdate(BaseModel):
    activity_id: str
    status: ActivityStatus
    completed_at: Optional[datetime] = None
