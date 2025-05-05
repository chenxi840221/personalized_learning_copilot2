import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json

from azure.core.credentials import AzureKeyCredential
from azure.ai.openai import OpenAIClient  # Updated for version < 1.0.0

from models.user import User
from models.content import Content
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class LearningPlanService:
    """Service for generating and managing learning plans using Azure OpenAI."""
    
    def __init__(self):
        """Initialize the learning plan service."""
        self.openai_client = OpenAIClient(
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            credential=AzureKeyCredential(settings.AZURE_OPENAI_KEY)
        )
        
        # In-memory storage for plans (in a real application, use Azure Cosmos DB or similar)
        self.learning_plans = {}
    
    async def generate_learning_plan(
        self,
        user: User,
        subject: str,
        content_items: List[Content]
    ) -> LearningPlan:
        """
        Generate a personalized learning plan for a user.
        
        Args:
            user: The user to generate the plan for
            subject: The subject to focus on
            content_items: Available content items to include in the plan
            
        Returns:
            A personalized learning plan
        """
        try:
            # Format content for the prompt
            content_descriptions = self._format_content_for_prompt(content_items)
            
            # Create the prompt for learning plan generation
            prompt = self._create_learning_plan_prompt(user, subject, content_descriptions)
            
            # Generate learning plan using Azure OpenAI
            completion = self.openai_client.get_completions(
                deployment_id=settings.AZURE_OPENAI_DEPLOYMENT,
                prompt=prompt,
                max_tokens=1500,
                temperature=0.7,
                top_p=0.95,
                stop=None,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            # Extract the generated text
            generated_text = completion.choices[0].text.strip()
            
            # Parse the generated plan
            try:
                # Find JSON content within the generated text
                json_start = generated_text.find("{")
                json_end = generated_text.rfind("}") + 1
                
                if json_start >= 0 and json_end > json_start:
                    plan_json = generated_text[json_start:json_end]
                    plan_dict = json.loads(plan_json)
                else:
                    # Fall back to simple parsing if JSON extraction fails
                    plan_dict = self._parse_generated_plan(generated_text)
                
                # Create the learning plan
                plan = self._create_learning_plan_from_dict(plan_dict, user.id, subject, content_items)
                
                # Store the plan
                self.learning_plans[plan.id] = plan
                
                return plan
                
            except json.JSONDecodeError:
                # Fall back to simple parsing if JSON parsing fails
                plan_dict = self._parse_generated_plan(generated_text)
                plan = self._create_learning_plan_from_dict(plan_dict, user.id, subject, content_items)
                self.learning_plans[plan.id] = plan
                return plan
                
        except Exception as e:
            logger.error(f"Error generating learning plan: {e}")
            # Create a simple default plan if generation fails
            return self._create_default_plan(user.id, subject, content_items)
    
    def _format_content_for_prompt(self, content_items: List[Content]) -> str:
        """Format content items for inclusion in the prompt."""
        formatted_content = ""
        
        for i, content in enumerate(content_items):
            formatted_content += f"""
            Content {i+1}:
            - ID: {content.id}
            - Title: {content.title}
            - Type: {content.content_type.value}
            - Difficulty: {content.difficulty_level.value}
            - Description: {content.description}
            - URL: {content.url}
            
            """
        
        return formatted_content
    
    def _create_learning_plan_prompt(self, user: User, subject: str, content_descriptions: str) -> str:
        """Create the prompt for learning plan generation."""
        # Create a prompt that will work well with the GPT model
        student_name = user.full_name or user.username
        grade_level = str(user.grade_level) if user.grade_level else "Unknown"
        learning_style = user.learning_style.value if user.learning_style else "Mixed"
        interests = ", ".join(user.subjects_of_interest) if user.subjects_of_interest else "General learning"
        
        prompt = f"""
        You are an expert educational AI assistant tasked with creating personalized learning plans.
        
        STUDENT PROFILE:
        - Name: {student_name}
        - Grade Level: {grade_level}
        - Learning Style: {learning_style}
        - Subjects of Interest: {interests}
        
        SUBJECT TO FOCUS ON: {subject}
        
        AVAILABLE LEARNING RESOURCES:
        {content_descriptions}
        
        Based on the student profile and available resources, create a personalized learning plan for the student.
        Include a title, description, and a sequence of 3-5 learning activities.
        
        For each activity:
        1. Choose appropriate content from the available resources
        2. Set an estimated duration in minutes
        3. Provide a brief description of what the student should do
        4. Set the activities in a logical order
        
        Return the learning plan in the following JSON format:
        ```json
        {{
            "title": "Learning Plan Title",
            "description": "Brief description of overall plan",
            "subject": "{subject}",
            "topics": ["topic1", "topic2"],
            "activities": [
                {{
                    "title": "Activity Title",
                    "description": "Activity description",
                    "content_id": "<ID of content resource or null>",
                    "duration_minutes": <minutes>,
                    "order": <order number>
                }},
                ...
            ]
        }}
        ```
        
        Return ONLY the JSON response without any additional text.
        """
        
        return prompt
    
    def _parse_generated_plan(self, generated_text: str) -> Dict[str, Any]:
        """Parse a learning plan from generated text if JSON parsing fails."""
        # Simple parser for extracting key information
        plan_dict = {
            "title": "Learning Plan",
            "description": "A personalized learning plan",
            "subject": "",
            "topics": [],
            "activities": []
        }
        
        # Extract title
        title_match = re.search(r"title:?\s*\"?([^\"]+)\"?", generated_text, re.IGNORECASE)
        if title_match:
            plan_dict["title"] = title_match.group(1).strip()
        
        # Extract description
        desc_match = re.search(r"description:?\s*\"?([^\"]+)\"?", generated_text, re.IGNORECASE)
        if desc_match:
            plan_dict["description"] = desc_match.group(1).strip()
        
        # Extract subject
        subject_match = re.search(r"subject:?\s*\"?([^\"]+)\"?", generated_text, re.IGNORECASE)
        if subject_match:
            plan_dict["subject"] = subject_match.group(1).strip()
        
        # Extract topics
        topics_match = re.search(r"topics:?\s*\[(.*?)\]", generated_text, re.IGNORECASE | re.DOTALL)
        if topics_match:
            topics_text = topics_match.group(1)
            topics = re.findall(r"\"([^\"]+)\"", topics_text)
            plan_dict["topics"] = topics
        
        # Extract activities
        activities_section = re.search(r"activities:?\s*\[(.*?)\]", generated_text, re.IGNORECASE | re.DOTALL)
        if activities_section:
            activities_text = activities_section.group(1)
            activity_blocks = re.findall(r"\{(.*?)\}", activities_text, re.DOTALL)
            
            for i, activity_block in enumerate(activity_blocks):
                activity = {
                    "title": f"Activity {i+1}",
                    "description": "Learning activity",
                    "content_id": None,
                    "duration_minutes": 30,
                    "order": i+1
                }
                
                # Extract activity details
                title_match = re.search(r"title:?\s*\"?([^\"]+)\"?", activity_block, re.IGNORECASE)
                if title_match:
                    activity["title"] = title_match.group(1).strip()
                
                desc_match = re.search(r"description:?\s*\"?([^\"]+)\"?", activity_block, re.IGNORECASE)
                if desc_match:
                    activity["description"] = desc_match.group(1).strip()
                
                content_id_match = re.search(r"content_id:?\s*\"?([^\"]+)\"?", activity_block, re.IGNORECASE)
                if content_id_match:
                    activity["content_id"] = content_id_match.group(1).strip()
                
                duration_match = re.search(r"duration_minutes:?\s*(\d+)", activity_block, re.IGNORECASE)
                if duration_match:
                    activity["duration_minutes"] = int(duration_match.group(1))
                
                order_match = re.search(r"order:?\s*(\d+)", activity_block, re.IGNORECASE)
                if order_match:
                    activity["order"] = int(order_match.group(1))
                
                plan_dict["activities"].append(activity)
        
        return plan_dict
    
    def _create_learning_plan_from_dict(
        self, 
        plan_dict: Dict[str, Any], 
        user_id: str, 
        subject: str,
        content_items: List[Content]
    ) -> LearningPlan:
        """Create a learning plan object from a dictionary."""
        plan_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Ensure the plan has the correct subject
        if not plan_dict.get("subject"):
            plan_dict["subject"] = subject
        
        # Create activities
        activities = []
        for i, activity_dict in enumerate(plan_dict.get("activities", [])):
            # Validate content_id
            content_id = activity_dict.get("content_id")
            if content_id:
                # Check if the content ID exists in our resources
                content_exists = any(str(content.id) == content_id for content in content_items)
                if not content_exists:
                    content_id = None
            
            activity = LearningActivity(
                id=str(uuid.uuid4()),
                title=activity_dict.get("title", f"Activity {i+1}"),
                description=activity_dict.get("description", "Learning activity"),
                content_id=content_id,
                duration_minutes=activity_dict.get("duration_minutes", 30),
                order=activity_dict.get("order", i+1),
                status=ActivityStatus.NOT_STARTED,
                completed_at=None
            )
            activities.append(activity)
        
        # Create the learning plan
        plan = LearningPlan(
            id=plan_id,
            student_id=user_id,
            title=plan_dict.get("title", f"{subject} Learning Plan"),
            description=plan_dict.get("description", f"A personalized learning plan for {subject}"),
            subject=plan_dict.get("subject", subject),
            topics=plan_dict.get("topics", [subject]),
            activities=activities,
            status=ActivityStatus.NOT_STARTED,
            progress_percentage=0.0,
            created_at=now,
            updated_at=now,
            start_date=now,
            end_date=now + timedelta(days=14)  # 2-week plan by default
        )
        
        return plan
    
    def _create_default_plan(self, user_id: str, subject: str, content_items: List[Content]) -> LearningPlan:
        """Create a default learning plan when generation fails."""
        plan_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Create simple activities from available content
        activities = []
        for i, content in enumerate(content_items[:5]):  # Use up to 5 content items
            activity = LearningActivity(
                id=str(uuid.uuid4()),
                title=f"Study: {content.title}",
                description=content.description,
                content_id=content.id,
                duration_minutes=content.duration_minutes or 30,
                order=i+1,
                status=ActivityStatus.NOT_STARTED,
                completed_at=None
            )
            activities.append(activity)
        
        # Create the learning plan
        plan = LearningPlan(
            id=plan_id,
            student_id=user_id,
            title=f"{subject} Learning Plan",
            description=f"A personalized learning plan for {subject}",
            subject=subject,
            topics=[subject],
            activities=activities,
            status=ActivityStatus.NOT_STARTED,
            progress_percentage=0.0,
            created_at=now,
            updated_at=now,
            start_date=now,
            end_date=now + timedelta(days=14)  # 2-week plan by default
        )
        
        return plan
    
    async def get_user_learning_plans(self, user_id: str) -> List[LearningPlan]:
        """Get all learning plans for a user."""
        # Filter plans by user ID
        user_plans = [plan for plan in self.learning_plans.values() if plan.student_id == user_id]
        return user_plans
    
    async def get_learning_plan(self, plan_id: str, user_id: str) -> Optional[LearningPlan]:
        """Get a specific learning plan."""
        # Get the plan
        plan = self.learning_plans.get(plan_id)
        
        # Check if plan exists and belongs to the user
        if plan and plan.student_id == user_id:
            return plan
        
        return None
    
    async def update_activity_status(
        self,
        plan_id: str,
        activity_id: str,
        status: ActivityStatus,
        completed_at: Optional[datetime] = None,
        user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Update activity status in a learning plan."""
        # Get the plan
        plan = self.learning_plans.get(plan_id)
        
        # Check if plan exists and belongs to the user
        if not plan or (user_id and plan.student_id != user_id):
            return None
        
        # Find and update the activity
        activity_found = False
        for i, activity in enumerate(plan.activities):
            if activity.id == activity_id:
                plan.activities[i].status = status
                if status == ActivityStatus.COMPLETED:
                    plan.activities[i].completed_at = completed_at or datetime.utcnow()
                activity_found = True
                break
        
        if not activity_found:
            return None
        
        # Update plan status and progress
        self._update_plan_progress(plan)
        
        # Update timestamp
        plan.updated_at = datetime.utcnow()
        
        # Save updated plan
        self.learning_plans[plan_id] = plan
        
        return {
            "success": True,
            "message": "Activity status updated",
            "progress_percentage": plan.progress_percentage,
            "plan_status": plan.status
        }
    
    def _update_plan_progress(self, plan: LearningPlan):
        """Update plan progress percentage and status."""
        if not plan.activities:
            plan.progress_percentage = 0
            plan.status = ActivityStatus.NOT_STARTED
            return
        
        # Count completed activities
        total_activities = len(plan.activities)
        completed_activities = sum(1 for a in plan.activities if a.status == ActivityStatus.COMPLETED)
        
        # Calculate progress percentage
        plan.progress_percentage = (completed_activities / total_activities) * 100
        
        # Update plan status
        if completed_activities == total_activities:
            plan.status = ActivityStatus.COMPLETED
        elif completed_activities > 0:
            plan.status = ActivityStatus.IN_PROGRESS
        else:
            plan.status = ActivityStatus.NOT_STARTED

# Singleton instance
learning_plan_service = None

async def get_learning_plan_service():
    """Get or create learning plan service singleton."""
    global learning_plan_service
    if learning_plan_service is None:
        learning_plan_service = LearningPlanService()
    return learning_plan_service