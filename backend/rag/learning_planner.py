import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import uuid
from models.user import User
from models.content import Content
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from rag.retriever import retrieve_relevant_content
from config.settings import Settings
from rag.openai_adapter import get_openai_adapter

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class LearningPlanner:
    """
    Generate personalized learning plans and paths for students.
    Enhanced to better utilize the educational-content Azure AI Search index.
    """
    def __init__(self):
        # Initialize when needed
        self.openai_client = None
        
    async def create_learning_plan(
        self,
        student: User,
        subject: str,
        relevant_content: List[Content],
        duration_days: int = 14
    ) -> LearningPlan:
        """
        Create a standard learning plan based on relevant content.
        Args:
            student: The student user
            subject: Subject to focus on
            relevant_content: List of relevant content
            duration_days: Duration of the plan in days
        Returns:
            A LearningPlan object
        """
        # Format content for prompt with enhanced metadata
        content_descriptions = ""
        # Group content by topics to better organize learning progression
        content_by_topic = {}
        all_topics = set()
        
        # First pass: collect topics
        for content in relevant_content:
            for topic in content.topics:
                all_topics.add(topic)
                if topic not in content_by_topic:
                    content_by_topic[topic] = []
                content_by_topic[topic].append(content)
                
        # If no topics are available, group by difficulty level
        if not all_topics:
            content_by_difficulty = {
                "beginner": [],
                "intermediate": [],
                "advanced": []
            }
            
            for content in relevant_content:
                difficulty = content.difficulty_level.value
                content_by_difficulty[difficulty].append(content)
            
            # Format content grouped by difficulty level
            for difficulty, items in content_by_difficulty.items():
                if items:
                    content_descriptions += f"\n### {difficulty.upper()} LEVEL RESOURCES:\n"
                    for i, content in enumerate(items):
                        content_descriptions += f"""
                        Content {i+1}:
                        - ID: {content.id}
                        - Title: {content.title}
                        - Type: {content.content_type.value}
                        - Difficulty: {content.difficulty_level.value}
                        - Description: {content.description}
                        - URL: {content.url}
                        - Duration: {content.duration_minutes or 'Unknown'} minutes
                        """
        else:
            # Format content grouped by topic
            for topic in all_topics:
                if topic in content_by_topic and content_by_topic[topic]:
                    content_descriptions += f"\n### TOPIC: {topic}\n"
                    for i, content in enumerate(content_by_topic[topic]):
                        content_descriptions += f"""
                        Content {i+1}:
                        - ID: {content.id}
                        - Title: {content.title}
                        - Type: {content.content_type.value}
                        - Difficulty: {content.difficulty_level.value}
                        - Description: {content.description}
                        - URL: {content.url}
                        - Duration: {content.duration_minutes or 'Unknown'} minutes
                        """
            
        # Create prompt for learning plan generation with enhanced guidance
        prompt = f"""
        You are an expert educational AI assistant tasked with creating personalized learning plans.
        
        STUDENT PROFILE:
        - Name: {student.full_name or student.username}
        - Grade Level: {student.grade_level if student.grade_level else "Unknown"}
        - Learning Style: {student.learning_style.value if student.learning_style else "Mixed"}
        - Subjects of Interest: {', '.join(student.subjects_of_interest) if student.subjects_of_interest else "General learning"}
        
        SUBJECT TO FOCUS ON: {subject}
        
        LEARNING STYLE DETAILS:
        {self._get_learning_style_description(student.learning_style.value if student.learning_style else "Mixed")}
        
        AVAILABLE LEARNING RESOURCES:
        {content_descriptions}
        
        Create a {duration_days}-day learning plan with 4-6 activities that help the student master {subject}.
        The plan should follow these important guidelines:
        
        1. LEARNING PROGRESSION: Activities should follow a logical sequence, starting with foundational concepts and advancing to more complex ones.
        
        2. LEARNING STYLE ADAPTATION: Select content types that match the student's learning style:
           - Visual learners: Prefer videos and visual content
           - Auditory learners: Prefer audio content like lectures
           - Reading/Writing learners: Prefer articles and text-based content
           - Kinesthetic learners: Prefer interactive activities
           - Mixed learners: Include a variety of content types
        
        3. GRADE-APPROPRIATE CONTENT: Ensure all selected content matches the student's grade level ({student.grade_level if student.grade_level else "Unknown"}).
        
        4. CONTENT VARIETY: Include a mix of content types for comprehensive learning.
        
        5. SUBJECT INTEGRATION: If the student has other interests ({', '.join(student.subjects_of_interest) if student.subjects_of_interest else "None specified"}), try to include activities that connect to these interests when relevant.
        
        6. ACTIVITY BALANCE: More complex topics should have longer or multiple activities.
        
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
                    "content_id": "<ID of content resource>",
                    "duration_minutes": <minutes>,
                    "order": <order number>
                }},
                ...
            ]
        }}
        ```
        Return ONLY the JSON response without any additional text.
        """
        
        try:
            # Initialize client if needed
            if not self.openai_client:
                self.openai_client = await get_openai_adapter()
                
            # Generate learning plan using Azure OpenAI
            response = await self.openai_client.create_chat_completion(
                model=settings.AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are an educational AI that creates personalized learning plans."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            plan_dict = json.loads(response["choices"][0]["message"]["content"])
            
            # Format activities with proper IDs and status
            for activity in plan_dict.get("activities", []):
                # Ensure content_id is valid
                if "content_id" in activity and activity["content_id"]:
                    try:
                        # Check if the content ID exists in our resources
                        content_exists = any(str(content.id) == activity["content_id"] for content in relevant_content)
                        if not content_exists:
                            activity["content_id"] = None
                    except:
                        activity["content_id"] = None
                
                # Set default status
                activity["status"] = ActivityStatus.NOT_STARTED
                
            # Create learning plan object
            now = datetime.utcnow()
            learning_plan = LearningPlan(
                student_id=student.id,
                title=plan_dict["title"],
                description=plan_dict["description"],
                subject=plan_dict["subject"],
                topics=plan_dict["topics"],
                activities=[LearningActivity(**activity) for activity in plan_dict["activities"]],
                status=ActivityStatus.NOT_STARTED,
                progress_percentage=0.0,
                created_at=now,
                updated_at=now,
                start_date=now,
                end_date=now + timedelta(days=duration_days)
            )
            
            return learning_plan
            
        except Exception as e:
            logger.error(f"Error creating learning plan: {e}")
            
            # Create a fallback learning plan
            now = datetime.utcnow()
            return LearningPlan(
                student_id=student.id,
                title=f"{subject} Learning Plan",
                description=f"A basic learning plan for {subject}",
                subject=subject,
                topics=[subject],
                activities=[],
                status=ActivityStatus.NOT_STARTED,
                progress_percentage=0.0,
                created_at=now,
                updated_at=now,
                start_date=now,
                end_date=now + timedelta(days=duration_days)
            )
    
    async def create_advanced_learning_path(
        self,
        student: User,
        subject: str,
        relevant_content: List[Content],
        duration_weeks: int = 4
    ) -> Dict[str, Any]:
        """
        Create an advanced learning path with weekly structure.
        Args:
            student: The student user
            subject: Subject to focus on
            relevant_content: List of relevant content
            duration_weeks: Duration of the path in weeks
        Returns:
            A structured learning path
        """
        # Format content for prompt - grouped by difficulty level
        beginner_content = [c for c in relevant_content if c.difficulty_level.value == "beginner"]
        intermediate_content = [c for c in relevant_content if c.difficulty_level.value == "intermediate"]
        advanced_content = [c for c in relevant_content if c.difficulty_level.value == "advanced"]
        
        # Format content by progression level
        content_descriptions = "# AVAILABLE LEARNING RESOURCES\n\n"
        
        if beginner_content:
            content_descriptions += "## BEGINNER LEVEL RESOURCES:\n"
            for i, content in enumerate(beginner_content[:5]):  # Limit to 5 items per level
                content_descriptions += f"""
                Content B{i+1}:
                - ID: {content.id}
                - Title: {content.title}
                - Type: {content.content_type.value}
                - Topics: {', '.join(content.topics) if content.topics else 'General'}
                - Description: {content.description}
                """
        
        if intermediate_content:
            content_descriptions += "\n## INTERMEDIATE LEVEL RESOURCES:\n"
            for i, content in enumerate(intermediate_content[:5]):
                content_descriptions += f"""
                Content I{i+1}:
                - ID: {content.id}
                - Title: {content.title}
                - Type: {content.content_type.value}
                - Topics: {', '.join(content.topics) if content.topics else 'General'}
                - Description: {content.description}
                """
        
        if advanced_content:
            content_descriptions += "\n## ADVANCED LEVEL RESOURCES:\n"
            for i, content in enumerate(advanced_content[:5]):
                content_descriptions += f"""
                Content A{i+1}:
                - ID: {content.id}
                - Title: {content.title}
                - Type: {content.content_type.value}
                - Topics: {', '.join(content.topics) if content.topics else 'General'}
                - Description: {content.description}
                """
        
        # Add learning style information
        learning_style_info = self._get_learning_style_description(
            student.learning_style.value if student.learning_style else "mixed"
        )
        
        # Create prompt for learning path generation with enhanced guidance
        prompt = f"""
        You are creating a {duration_weeks}-week comprehensive learning path for a grade {student.grade_level} student 
        with {student.learning_style.value if student.learning_style else "mixed"} learning style who wants to master {subject}.
        
        # STUDENT PROFILE:
        - Name: {student.full_name or student.username}
        - Grade Level: {student.grade_level if student.grade_level else "Unknown"}
        - Learning Style: {student.learning_style.value if student.learning_style else "Mixed"}
        - Subjects of Interest: {', '.join(student.subjects_of_interest) if student.subjects_of_interest else "General learning"}
        
        # LEARNING STYLE INFORMATION:
        {learning_style_info}
        
        {content_descriptions}
        
        # LEARNING PATH REQUIREMENTS:
        
        Create a structured {duration_weeks}-week learning path with:
        
        1. An overall goal that's achievable and measurable
        2. Weekly themes that build progressively (easier to harder concepts)
        3. 3-5 daily activities for each week (Monday through Friday)
        4. At least one assessment activity per week to check understanding
        5. Weekend review/practice activities
        
        For each activity:
        - Choose appropriate content from the available resources when possible
        - For resource-based activities, include the content ID
        - For custom activities, provide detailed instructions
        - Set estimated duration in minutes (15-45 minutes per activity)
        - Include a mix of content types appropriate for the student's learning style
        - Sequence activities to build on each other within each week
        
        # CONTENT SELECTION GUIDELINES:
        
        - Week 1: Focus on foundational/beginner content
        - Middle weeks: Progress to intermediate content 
        - Final week: Include some advanced content when appropriate
        - Match content types to the student's learning style when possible
        - Include diverse activity types (reading, watching, practicing, creating)
        
        Format the response as a JSON object with this structure:
        ```json
        {{
            "title": "Master [Subject] Fundamentals",
            "description": "A comprehensive learning path to develop strong [subject] skills",
            "overall_goal": "Clear statement of learning objectives",
            "subject": "{subject}",
            "grade_level": {student.grade_level if student.grade_level else "Unknown"},
            "weeks": [
                {{
                    "week_number": 1,
                    "theme": "Introduction to [Topic]",
                    "goal": "Specific goal for this week",
                    "days": [
                        {{
                            "day": "Monday",
                            "activities": [
                                {{
                                    "title": "Activity Title",
                                    "description": "Clear instructions",
                                    "content_id": "ID or null",
                                    "type": "video/reading/practice/etc",
                                    "duration_minutes": 30
                                }}
                            ]
                        }},
                        // Tuesday through Friday...
                    ],
                    "weekend_activity": {{
                        "title": "Weekend Review",
                        "description": "Review activity description",
                        "duration_minutes": 45
                    }},
                    "skills": ["Skill 1", "Skill 2"],
                    "assessment": "Description of assessment activity"
                }},
                // Additional weeks...
            ]
        }}
        ```
        
        Return ONLY the JSON with no additional text.
        """
        
        try:
            # Initialize client if needed
            if not self.openai_client:
                self.openai_client = await get_openai_adapter()
                
            # Generate learning path using Azure OpenAI
            response = await self.openai_client.create_chat_completion(
                model=settings.AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": "You are an educational AI that creates comprehensive learning paths."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            learning_path = json.loads(response["choices"][0]["message"]["content"])
            
            # Add path ID and metadata
            learning_path["id"] = str(uuid.uuid4())
            learning_path["student_id"] = str(student.id)
            learning_path["created_at"] = datetime.utcnow().isoformat()
            
            # Validate content IDs
            for week in learning_path.get("weeks", []):
                for day in week.get("days", []):
                    for activity in day.get("activities", []):
                        if "content_id" in activity and activity["content_id"]:
                            # Check if content ID exists in our resources
                            content_exists = any(str(content.id) == activity["content_id"] for content in relevant_content)
                            if not content_exists:
                                activity["content_id"] = None
            
            return learning_path
            
        except Exception as e:
            logger.error(f"Error creating advanced learning path: {e}")
            
            # Create a fallback learning path
            return {
                "id": str(uuid.uuid4()),
                "title": f"{subject} Learning Path",
                "description": f"A learning path for {subject}",
                "overall_goal": f"Learn the fundamentals of {subject}",
                "student_id": str(student.id),
                "subject": subject,
                "created_at": datetime.utcnow().isoformat(),
                "weeks": []
            }
    
    def _get_learning_style_description(self, learning_style: str) -> str:
        """
        Get a detailed description of a learning style to include in prompts.
        Args:
            learning_style: Learning style identifier
        Returns:
            Detailed description of the learning style
        """
        descriptions = {
            "visual": """
                Visual learners learn best through seeing. They prefer:
                - Videos and demonstrations
                - Diagrams, charts, and graphs
                - Visual presentations and infographics
                - Content with strong visual elements
                
                When planning activities for visual learners, prioritize video content, 
                visual exercises, and content with diagrams and illustrations.
            """,
            
            "auditory": """
                Auditory learners learn best through hearing. They prefer:
                - Lectures and audio recordings
                - Group discussions
                - Verbal instructions
                - Content that can be read aloud or discussed
                
                When planning activities for auditory learners, prioritize video lectures,
                audio content, and activities that involve discussion or verbal explanation.
            """,
            
            "reading_writing": """
                Reading/Writing learners learn best through text. They prefer:
                - Articles and books
                - Written instructions and explanations
                - Note-taking and writing summaries
                - Text-heavy content
                
                When planning activities for reading/writing learners, prioritize articles,
                text-based content, and activities that involve reading and writing.
            """,
            
            "kinesthetic": """
                Kinesthetic learners learn best through doing. They prefer:
                - Hands-on activities and experiments
                - Interactive simulations and games
                - Physical movement and manipulation
                - Practical applications
                
                When planning activities for kinesthetic learners, prioritize interactive content,
                simulations, games, and activities that involve active participation.
            """,
            
            "mixed": """
                Mixed learning style students benefit from variety. They prefer:
                - A combination of different content types
                - Multimodal learning experiences
                - Content that engages multiple senses
                - Variety in presentation and activities
                
                When planning activities for mixed learning style students, include a variety
                of content types with a balance of visual, auditory, reading/writing, and kinesthetic elements.
            """
        }
        
        # Return the description for the specified learning style, or mixed if not found
        return descriptions.get(learning_style.lower(), descriptions["mixed"])
    
    async def adapt_plan_for_performance(
        self,
        learning_plan: LearningPlan,
        performance_metrics: Dict[str, Any]
    ) -> LearningPlan:
        """
        Adapt a learning plan based on student performance.
        Args:
            learning_plan: Current learning plan
            performance_metrics: Student performance metrics
        Returns:
            Updated learning plan
        """
        # Get completed activities
        completed_activities = [a for a in learning_plan.activities if a.status == ActivityStatus.COMPLETED]
        
        # If no completed activities or no performance metrics, return original plan
        if not completed_activities or not performance_metrics:
            return learning_plan
        
        # Extract performance data
        avg_quiz_score = performance_metrics.get("avg_quiz_score", 0.7)
        writing_quality = performance_metrics.get("writing_quality", 70)
        areas_for_improvement = performance_metrics.get("areas_for_improvement", [])
        
        # Determine if plan needs adaptation
        needs_easier_content = avg_quiz_score < 0.6 or writing_quality < 60
        needs_harder_content = avg_quiz_score > 0.85 and writing_quality > 80
        
        if not needs_easier_content and not needs_harder_content:
            # No adaptation needed
            return learning_plan
        
        # Fetch relevant content to provide alternatives
        db = None  # This would be your database connector
        student = await db.users.find_one({"_id": learning_plan.student_id})
        if not student:
            return learning_plan
            
        student_obj = User(**student)
        
        # Get relevant content with appropriate difficulty
        relevant_content = await retrieve_relevant_content(
            student_profile=student_obj,
            subject=learning_plan.subject,
            k=10
        )
        
        if needs_easier_content:
            # Filter for easier content
            easier_content = [c for c in relevant_content if c.difficulty_level.value == "beginner"]
            if easier_content:
                # Replace uncompleted activities with easier ones
                for i, activity in enumerate(learning_plan.activities):
                    if activity.status == ActivityStatus.NOT_STARTED and i < len(easier_content):
                        # Replace with easier content
                        learning_plan.activities[i] = LearningActivity(
                            id=str(uuid.uuid4()),
                            title=f"[EASIER] {easier_content[i].title}",
                            description=f"This activity has been adjusted to help you build foundational skills: {easier_content[i].description}",
                            content_id=easier_content[i].id,
                            duration_minutes=activity.duration_minutes,
                            order=activity.order,
                            status=ActivityStatus.NOT_STARTED
                        )
        elif needs_harder_content:
            # Filter for harder content
            harder_content = [c for c in relevant_content if c.difficulty_level.value == "advanced"]
            if harder_content:
                # Add challenging activities to the plan
                max_order = max([a.order for a in learning_plan.activities]) if learning_plan.activities else 0
                for i, content in enumerate(harder_content[:2]):  # Add up to 2 challenging activities
                    new_activity = LearningActivity(
                        id=str(uuid.uuid4()),
                        title=f"[CHALLENGE] {content.title}",
                        description=f"This advanced activity will challenge your skills: {content.description}",
                        content_id=content.id,
                        duration_minutes=30,
                        order=max_order + i + 1,
                        status=ActivityStatus.NOT_STARTED
                    )
                    learning_plan.activities.append(new_activity)
        
        # Update the learning plan
        learning_plan.updated_at = datetime.utcnow()
        return learning_plan

# Singleton instance
learning_planner = None

async def get_learning_planner():
    """Get or create the learning planner singleton."""
    global learning_planner
    if learning_planner is None:
        learning_planner = LearningPlanner()
    return learning_planner