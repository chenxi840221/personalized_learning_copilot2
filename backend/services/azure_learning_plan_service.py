# backend/services/azure_learning_plan_service.py
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
import aiohttp

from models.user import User
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class AzureLearningPlanService:
    """
    Service for managing learning plans using Azure AI Search.
    """
    
    def __init__(self):
        """Initialize learning plan service."""
        self.search_endpoint = settings.AZURE_SEARCH_ENDPOINT
        self.search_key = settings.AZURE_SEARCH_KEY
        self.index_name = settings.PLANS_INDEX_NAME
        
    def _parse_datetime(self, datetime_str: str) -> datetime:
        """
        Parse datetime string from Azure Search with improved error handling.
        Handles various ISO formats including those with milliseconds and timezone information.
        
        Args:
            datetime_str: ISO datetime string to parse
            
        Returns:
            Parsed datetime object
        """
        if not datetime_str:
            return datetime.utcnow()
            
        try:
            # Try standard parsing
            # First attempt to remove any timezone information as Python < 3.11 fromisoformat
            # has issues with some timezone formats
            if '+' in datetime_str:
                # Handle format like "2023-04-30T12:34:56.789+00:00"
                # Split at the timezone marker and keep only the first part
                datetime_str = datetime_str.split('+')[0]
            elif 'Z' in datetime_str:
                # Handle ISO format with Z (UTC) suffix
                datetime_str = datetime_str.replace('Z', '')

            # Remove milliseconds if they exist
            if '.' in datetime_str:
                parts = datetime_str.split('.')
                datetime_str = parts[0]
                
            # Parse the simplified string
            return datetime.fromisoformat(datetime_str)
        except Exception as e:
            logger.warning(f"Error parsing datetime '{datetime_str}': {e}. Using current time.")
            return datetime.utcnow()
    
    async def get_learning_plans(
        self, 
        user_id: str,
        subject: Optional[str] = None,
        limit: int = 50
    ) -> List[LearningPlan]:
        """
        Get learning plans for a user.
        
        Args:
            user_id: User ID
            subject: Optional subject filter
            limit: Maximum number of results
            
        Returns:
            List of learning plans
        """
        if not (self.search_endpoint and self.search_key):
            logger.warning("Azure Search not configured")
            return []
        
        try:
            # Build search URL
            search_url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search"
            search_url += f"?api-version=2023-07-01-Preview"
            
            # Filter by owner_id or student_id to allow either relationship
            filter_expr = f"owner_id eq '{user_id}' or student_id eq '{user_id}'"
            if subject:
                filter_expr = f"(owner_id eq '{user_id}' or student_id eq '{user_id}') and subject eq '{subject}'"
            
            # Build search body - using field names that match the schema
            search_body = {
                "filter": filter_expr,
                "orderby": "created_at desc",  # This field name should match the schema
                "top": limit
            }
            
            # Execute search
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    search_url,
                    json=search_body,
                    headers={
                        "Content-Type": "application/json",
                        "api-key": self.search_key
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"Azure Search error: {response.status} - {await response.text()}")
                        return []
                    
                    # Parse response
                    result = await response.json()
                    
                    # Convert to LearningPlan objects
                    plans = []
                    for item in result.get("value", []):
                        try:
                            # Get activities from the complex type collection
                            activities = []
                            
                            # Process activities collection directly from Azure Search response
                            if "activities" in item and isinstance(item["activities"], list):
                                logger.info(f"Found {len(item['activities'])} activities in complex type collection")
                                
                                # Convert to LearningActivity objects
                                for activity_obj in item["activities"]:
                                    try:
                                        # Create a LearningActivity with fields from the complex type
                                        # Add default values for fields not in the schema
                                        activity = LearningActivity(
                                            id=activity_obj.get("id", str(uuid.uuid4())),
                                            title=activity_obj.get("title", "Activity"),
                                            description=activity_obj.get("description", ""),
                                            content_id=activity_obj.get("content_id"),
                                            content_url="",  # Not in schema but needed
                                            duration_minutes=activity_obj.get("duration_minutes", 30),
                                            order=activity_obj.get("order", 1),
                                            day=1,  # Default day since not in schema
                                            status=ActivityStatus(activity_obj.get("status", "not_started")),
                                            completed_at=activity_obj.get("completed_at"),
                                            learning_benefit="",  # Not in schema
                                            metadata={}  # Not in schema
                                        )
                                        activities.append(activity)
                                    except Exception as activity_error:
                                        logger.error(f"Error creating activity: {activity_error}")
                            else:
                                logger.warning("No activities field found in the learning plan")
                                
                            # Fallback for backward compatibility with old schema
                            if not activities:
                                # Try old field names
                                for field_name in ["activities_json", "activities_content"]:
                                    if field_name in item and item[field_name]:
                                        try:
                                            old_activities = json.loads(item[field_name])
                                            logger.info(f"Found {len(old_activities)} activities in {field_name}")
                                            for activity_dict in old_activities:
                                                activity = LearningActivity(
                                                    id=activity_dict.get("id", str(uuid.uuid4())),
                                                    title=activity_dict.get("title", "Activity"),
                                                    description=activity_dict.get("description", ""),
                                                    content_id=activity_dict.get("content_id"),
                                                    content_url=activity_dict.get("content_url"),
                                                    duration_minutes=activity_dict.get("duration_minutes", 30),
                                                    order=activity_dict.get("order", 1),
                                                    day=activity_dict.get("day", 1),
                                                    status=ActivityStatus(activity_dict.get("status", "not_started")),
                                                    completed_at=activity_dict.get("completed_at"),
                                                    learning_benefit=activity_dict.get("learning_benefit", ""),
                                                    metadata=activity_dict.get("metadata", {})
                                                )
                                                activities.append(activity)
                                        except json.JSONDecodeError:
                                            logger.error(f"Error parsing {field_name}: {item.get(field_name)}")
                            # Fallback to activities field for backward compatibility
                            elif "activities" in item:
                                # Convert activities JSON if it's stored as a string
                                if isinstance(item.get("activities"), str):
                                    try:
                                        item["activities"] = json.loads(item["activities"])
                                    except json.JSONDecodeError:
                                        item["activities"] = []
                                
                                # Convert each activity to LearningActivity
                                for activity_dict in item.get("activities", []):
                                    activity = LearningActivity(
                                        id=activity_dict.get("id", str(uuid.uuid4())),
                                        title=activity_dict.get("title", "Activity"),
                                        description=activity_dict.get("description", ""),
                                        content_id=activity_dict.get("content_id"),
                                        content_url=activity_dict.get("content_url"),
                                        duration_minutes=activity_dict.get("duration_minutes", 30),
                                        order=activity_dict.get("order", 1),
                                        day=activity_dict.get("day", 1),
                                        status=ActivityStatus(activity_dict.get("status", "not_started")),
                                        completed_at=activity_dict.get("completed_at"),
                                        learning_benefit=activity_dict.get("learning_benefit", ""),
                                        metadata=activity_dict.get("metadata", {})
                                    )
                                    activities.append(activity)
                            
                            # Sort activities by day and order
                            activities.sort(key=lambda x: (getattr(x, "day", 1), x.order))
                            
                            # Parse metadata from the simplified schema
                            metadata = {}
                            if "metadata" in item and item["metadata"]:
                                try:
                                    if isinstance(item["metadata"], str):
                                        metadata = json.loads(item["metadata"])
                                    elif isinstance(item["metadata"], dict):
                                        metadata = item["metadata"]
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse metadata: {item.get('metadata')}")
                            
                            # Create LearningPlan with field name mapping
                            plan = LearningPlan(
                                id=item.get("id", str(uuid.uuid4())),
                                student_id=item.get("student_id", user_id),
                                title=item.get("title", "Learning Plan"),
                                description=item.get("description", ""),
                                subject=item.get("subject", "General"),
                                topics=item.get("topics", []),
                                activities=activities,
                                status=ActivityStatus(item.get("status", "not_started")),
                                # Map from simplified fields
                                progress_percentage=item.get("progress_percentage", 0.0),
                                created_at=self._parse_datetime(item.get("created_at")) if item.get("created_at") else datetime.utcnow(),
                                updated_at=self._parse_datetime(item.get("updated_at")) if item.get("updated_at") else datetime.utcnow(),
                                start_date=self._parse_datetime(item.get("start_date")) if item.get("start_date") else None,
                                end_date=self._parse_datetime(item.get("end_date")) if item.get("end_date") else None,
                                metadata=metadata,
                                owner_id=item.get("owner_id")  # Get owner_id from the document
                            )
                            plans.append(plan)
                        except Exception as e:
                            logger.error(f"Error converting plan: {e}")
                    
                    return plans
                    
        except Exception as e:
            logger.error(f"Error getting learning plans: {e}")
            return []
    
    async def create_learning_plan(self, plan: LearningPlan) -> bool:
        """
        Create a new learning plan.
        
        Args:
            plan: Learning plan to create
            
        Returns:
            Success status
        """
        if not (self.search_endpoint and self.search_key):
            logger.warning("Azure Search not configured")
            return False
        
        try:
            # Build request URL
            index_url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/index"
            index_url += f"?api-version=2023-07-01-Preview"
            
            # Convert plan to dict
            plan_dict = plan.dict()
            
            # Create a new dictionary with fields matching the Azure Search schema
            simplified_dict = {
                "id": plan_dict.get("id"),
                "student_id": plan_dict.get("student_id"),
                "owner_id": plan_dict.get("owner_id"),  # Include owner_id field
                "title": plan_dict.get("title", "Learning Plan"),
                "description": plan_dict.get("description", ""),
                "subject": plan_dict.get("subject", "General"),
                "topics": plan_dict.get("topics", []),
                "status": plan_dict.get("status", "not_started"),
                "progress_percentage": plan_dict.get("progress_percentage", 0.0)
            }
            
            # Format dates according to the exact field names in the schema
            if "created_at" in plan_dict and plan_dict["created_at"]:
                if isinstance(plan_dict["created_at"], datetime):
                    simplified_dict["created_at"] = plan_dict["created_at"].isoformat() + "Z"
                    
            if "updated_at" in plan_dict and plan_dict["updated_at"]:
                if isinstance(plan_dict["updated_at"], datetime):
                    simplified_dict["updated_at"] = plan_dict["updated_at"].isoformat() + "Z"
                    
            if "start_date" in plan_dict and plan_dict["start_date"]:
                if isinstance(plan_dict["start_date"], datetime):
                    simplified_dict["start_date"] = plan_dict["start_date"].isoformat() + "Z"
                    
            if "end_date" in plan_dict and plan_dict["end_date"]:
                if isinstance(plan_dict["end_date"], datetime):
                    simplified_dict["end_date"] = plan_dict["end_date"].isoformat() + "Z"
            
            # Convert activities to a collection of complex types as per schema
            activities_collection = []
            for activity in plan.activities:
                activity_dict = activity.dict()
                # Only include fields that exist in the schema
                activity_obj = {
                    "id": activity_dict.get("id"),
                    "title": activity_dict.get("title"),
                    "description": activity_dict.get("description"),
                    "content_id": activity_dict.get("content_id"),
                    "duration_minutes": activity_dict.get("duration_minutes"),
                    "order": activity_dict.get("order"),
                    "status": activity_dict.get("status")
                }
                
                # Format completed_at date if present
                if activity_dict.get("completed_at"):
                    if isinstance(activity_dict["completed_at"], datetime):
                        activity_obj["completed_at"] = activity_dict["completed_at"].isoformat() + "Z"
                
                activities_collection.append(activity_obj)
            
            # Add activities as a collection field
            simplified_dict["activities"] = activities_collection
            
            # No need for chunking or JSON conversion - using complex types directly

            # Replace plan_dict with our simplified dictionary
            plan_dict = simplified_dict
            
            logger.info(f"Plan dict ready for Azure Search with keys: {', '.join(plan_dict.keys())}")
            
            # Build request body
            request_body = {
                "value": [plan_dict]
            }
            
            # Execute request
            try:
                logger.info(f"Sending update request to Azure Search index: {self.index_name}")
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        index_url,
                        json=request_body,
                        headers={
                            "Content-Type": "application/json",
                            "api-key": self.search_key
                        }
                    ) as response:
                        response_text = await response.text()
                        if response.status != 200 and response.status != 201:
                            logger.error(f"Azure Search error: {response.status} - {response_text}")
                            return False
                        
                        # Parse response
                        logger.info(f"Got successful response from Azure Search: {response.status}")
                        try:
                            result = json.loads(response_text)
                        except json.JSONDecodeError as je:
                            logger.error(f"Failed to parse Azure Search response: {je} - Response: {response_text}")
                            return False
            except Exception as e:
                logger.exception(f"Network error when updating Azure Search index: {e}")
                return False
                    
            # Check for errors
            if "value" in result:
                for item in result["value"]:
                    if not item.get("status", False):
                        logger.error(f"Error creating learning plan: {item.get('errorMessage')}")
                        return False
            
            return True
                
        except Exception as e:
            logger.error(f"Error creating learning plan: {e}")
            return False
    
    async def update_learning_plan(self, plan: LearningPlan) -> bool:
        """
        Update an existing learning plan.
        
        Args:
            plan: Learning plan to update
            
        Returns:
            Success status
        """
        # For Azure Search, create and update are the same operation
        return await self.create_learning_plan(plan)
    
    async def get_learning_plan(self, plan_id: str, user_id: str) -> Optional[LearningPlan]:
        """
        Get a specific learning plan.
        
        Args:
            plan_id: Learning plan ID
            user_id: User ID for authorization
            
        Returns:
            Learning plan or None if not found
        """
        if not (self.search_endpoint and self.search_key):
            logger.warning("Azure Search not configured")
            return None
        
        try:
            # Build search URL
            search_url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/search"
            search_url += f"?api-version=2023-07-01-Preview"
            
            # Get plan by id without any user filtering (we'll check permissions later)
            filter_expr = f"id eq '{plan_id}'"
            
            # Build search body
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
                        "api-key": self.search_key
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"Azure Search error: {response.status} - {await response.text()}")
                        return None
                    
                    # Parse response
                    result = await response.json()
                    
                    # Check if plan was found
                    if not result.get("value") or len(result["value"]) == 0:
                        return None
                    
                    # Get plan data
                    item = result["value"][0]
                    
                    # Check user permission - allow access to both owner and student
                    stored_owner_id = item.get("owner_id")
                    stored_student_id = item.get("student_id")
                    
                    # For debug logging
                    logger.info(f"Permission check for plan {plan_id}: user_id={user_id}, owner_id={stored_owner_id}, student_id={stored_student_id}")
                    
                    if (stored_owner_id and stored_owner_id != user_id) and (stored_student_id and stored_student_id != user_id):
                        logger.warning(f"User {user_id} does not have permission to access plan {plan_id}")
                        return None
                    
                    # Get activities from the complex type collection
                    activities = []
                    
                    # Process activities collection directly from Azure Search response
                    if "activities" in item and isinstance(item["activities"], list):
                        logger.info(f"Found {len(item['activities'])} activities in complex type collection")
                        
                        # Convert to LearningActivity objects
                        for activity_obj in item["activities"]:
                            try:
                                # Create a LearningActivity with fields from the complex type
                                # Add default values for fields not in the schema
                                activity = LearningActivity(
                                    id=activity_obj.get("id", str(uuid.uuid4())),
                                    title=activity_obj.get("title", "Activity"),
                                    description=activity_obj.get("description", ""),
                                    content_id=activity_obj.get("content_id"),
                                    content_url="",  # Not in schema but needed
                                    duration_minutes=activity_obj.get("duration_minutes", 30),
                                    order=activity_obj.get("order", 1),
                                    day=1,  # Default day since not in schema
                                    status=ActivityStatus(activity_obj.get("status", "not_started")),
                                    completed_at=activity_obj.get("completed_at"),
                                    learning_benefit="",  # Not in schema
                                    metadata={}  # Not in schema
                                )
                                activities.append(activity)
                            except Exception as activity_error:
                                logger.error(f"Error creating activity: {activity_error}")
                    else:
                        logger.warning("No activities field found in the learning plan")
                        
                    # Fallback for backward compatibility with old schema
                    if not activities:
                        # Try old field names
                        for field_name in ["activities_json", "activities_content"]:
                            if field_name in item and item[field_name]:
                                try:
                                    old_activities = json.loads(item[field_name])
                                    logger.info(f"Found {len(old_activities)} activities in {field_name}")
                                    for activity_dict in old_activities:
                                        activity = LearningActivity(
                                            id=activity_dict.get("id", str(uuid.uuid4())),
                                            title=activity_dict.get("title", "Activity"),
                                            description=activity_dict.get("description", ""),
                                            content_id=activity_dict.get("content_id"),
                                            content_url=activity_dict.get("content_url"),
                                            duration_minutes=activity_dict.get("duration_minutes", 30),
                                            order=activity_dict.get("order", 1),
                                            day=activity_dict.get("day", 1),
                                            status=ActivityStatus(activity_dict.get("status", "not_started")),
                                            completed_at=activity_dict.get("completed_at"),
                                            learning_benefit=activity_dict.get("learning_benefit", ""),
                                            metadata=activity_dict.get("metadata", {})
                                        )
                                        activities.append(activity)
                                except json.JSONDecodeError:
                                    logger.error(f"Error parsing {field_name}: {item.get(field_name)}")
                        
                        # Fallback to activities field for backward compatibility
                        if not activities and "activities" in item:
                            # Convert activities JSON if it's stored as a string
                            if isinstance(item.get("activities"), str):
                                try:
                                    item["activities"] = json.loads(item["activities"])
                                except json.JSONDecodeError:
                                    item["activities"] = []
                            
                            # Convert each activity to LearningActivity
                            for activity_dict in item.get("activities", []):
                                activity = LearningActivity(
                                    id=activity_dict.get("id", str(uuid.uuid4())),
                                    title=activity_dict.get("title", "Activity"),
                                    description=activity_dict.get("description", ""),
                                    content_id=activity_dict.get("content_id"),
                                    content_url=activity_dict.get("content_url"),
                                    duration_minutes=activity_dict.get("duration_minutes", 30),
                                    order=activity_dict.get("order", 1),
                                    day=activity_dict.get("day", 1),
                                    status=ActivityStatus(activity_dict.get("status", "not_started")),
                                    completed_at=activity_dict.get("completed_at"),
                                    learning_benefit=activity_dict.get("learning_benefit", ""),
                                    metadata=activity_dict.get("metadata", {})
                                )
                                activities.append(activity)
                    
                    # Sort activities by day and order
                    activities.sort(key=lambda x: (getattr(x, "day", 1), x.order))
                    
                    # Parse metadata if it exists (either from metadata or metadata_json field)
                    metadata = {}
                    # Try the new metadata_json field first (used with API version 2023-07-01-Preview)
                    if "metadata_json" in item and item["metadata_json"]:
                        try:
                            if isinstance(item["metadata_json"], str):
                                metadata = json.loads(item["metadata_json"])
                            elif isinstance(item["metadata_json"], dict):
                                metadata = item["metadata_json"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse metadata_json: {item.get('metadata_json')}")
                    # Fallback to the original metadata field for backward compatibility
                    elif "metadata" in item and item["metadata"]:
                        try:
                            if isinstance(item["metadata"], str):
                                metadata = json.loads(item["metadata"])
                            elif isinstance(item["metadata"], dict):
                                metadata = item["metadata"]
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse metadata JSON: {item.get('metadata')}")
                    
                    # Create LearningPlan - using field names that match the schema
                    plan = LearningPlan(
                        id=item.get("id", str(uuid.uuid4())),
                        student_id=item.get("student_id", user_id),
                        title=item.get("title", "Learning Plan"),
                        description=item.get("description", ""),
                        subject=item.get("subject", "General"),
                        topics=item.get("topics", []),
                        activities=activities,
                        status=ActivityStatus(item.get("status", "not_started")),
                        progress_percentage=item.get("progress_percentage", 0.0),
                        created_at=self._parse_datetime(item.get("created_at")) if item.get("created_at") else datetime.utcnow(),
                        updated_at=self._parse_datetime(item.get("updated_at")) if item.get("updated_at") else datetime.utcnow(),
                        start_date=self._parse_datetime(item.get("start_date")) if item.get("start_date") else None,
                        end_date=self._parse_datetime(item.get("end_date")) if item.get("end_date") else None,
                        metadata=metadata,
                        owner_id=item.get("owner_id")  # Include owner_id from the document
                    )
                    
                    return plan
                    
        except Exception as e:
            logger.error(f"Error getting learning plan: {e}")
            return None
    
    async def update_activity_status(
        self,
        plan_id: str,
        activity_id: str,
        status: ActivityStatus,
        completed_at: Optional[datetime] = None,
        user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update activity status in a learning plan.
        
        Args:
            plan_id: Learning plan ID
            activity_id: Activity ID
            status: New status
            completed_at: Optional completion date
            user_id: User ID for authorization
            
        Returns:
            Dictionary with status information
        """
        logger.info(f"Updating activity status in service: plan_id={plan_id}, activity_id={activity_id}, status={status}, user_id={user_id}")
        
        try:
            # Get the plan
            plan = await self.get_learning_plan(plan_id, user_id)
            if not plan:
                logger.warning(f"Plan not found: {plan_id} for user {user_id}")
                return None
                
            logger.info(f"Plan found with {len(plan.activities)} activities")
        except Exception as e:
            logger.exception(f"Error getting learning plan: {e}")
            return None
        
        # Find and update the activity
        activity_found = False
        try:
            for i, activity in enumerate(plan.activities):
                logger.info(f"Checking activity {activity.id} against {activity_id}")
                if activity.id == activity_id:
                    logger.info(f"Found matching activity, updating status to {status}")
                    plan.activities[i].status = status
                    if status == ActivityStatus.COMPLETED:
                        plan.activities[i].completed_at = completed_at or datetime.utcnow()
                    activity_found = True
                    break
            
            if not activity_found:
                logger.warning(f"Activity not found: {activity_id} in plan {plan_id}")
                return None
            
            # Update plan status and progress
            self._update_plan_progress(plan)
            
            # Update timestamp
            plan.updated_at = datetime.utcnow()
            
            # Save updated plan
            try:
                logger.info(f"Saving updated plan with {len(plan.activities)} activities")
                logger.info(f"Plan details before save: id={plan.id}, status={plan.status}, activities={len(plan.activities)}, owner_id={plan.owner_id}")
                
                try:
                    # Convert to dict first to catch any serialization issues
                    plan_dict = plan.dict()
                    logger.info(f"Plan converted to dict successfully with {len(plan_dict['activities'])} activities")
                    
                    # Check if this is a plan with many activities that should use chunking
                    if len(plan_dict['activities']) > 20:
                        logger.info("Plan has many activities, setting weekly chunking for efficient storage")
                        # Set a custom attribute on the plan object to indicate it should use weekly chunking
                        setattr(plan, "use_weekly_chunking", True)
                except Exception as dict_err:
                    logger.exception(f"Error converting plan to dict: {dict_err}")
                    return None
                
                success = await self.update_learning_plan(plan)
                
                if not success:
                    logger.error("Failed to save updated plan")
                    return None
                
                logger.info(f"Plan updated successfully, new progress: {plan.progress_percentage}%")
                return {
                    "success": True,
                    "message": "Activity status updated",
                    "progress_percentage": plan.progress_percentage,
                    "plan_status": plan.status  # ActivityStatus inherits from str, so this works
                }
            except Exception as e:
                logger.exception(f"Error updating plan: {e}")
                return None
        except Exception as e:
            logger.exception(f"Error updating activity: {e}")
            return None
    
    def _update_plan_progress(self, plan: LearningPlan):
        """
        Update plan progress percentage and status.
        
        Args:
            plan: Learning plan to update
        """
        if not plan.activities:
            plan.progress_percentage = 0
            plan.status = ActivityStatus.NOT_STARTED
            return
        
        # Count completed activities
        total_activities = len(plan.activities)
        completed_activities = sum(1 for a in plan.activities if a.status == ActivityStatus.COMPLETED)
        
        # Calculate progress percentage
        plan.progress_percentage = (completed_activities / total_activities) * 100 if total_activities > 0 else 0
        
        # Update plan status
        if completed_activities == total_activities:
            plan.status = ActivityStatus.COMPLETED
        elif completed_activities > 0:
            plan.status = ActivityStatus.IN_PROGRESS
        else:
            plan.status = ActivityStatus.NOT_STARTED
            
    async def delete_learning_plan(self, plan_id: str, user_id: str) -> bool:
        """
        Delete a learning plan.
        
        Args:
            plan_id: Learning plan ID
            user_id: User ID for authorization
            
        Returns:
            Success status
        """
        if not (self.search_endpoint and self.search_key):
            logger.warning("Azure Search not configured")
            return False
        
        try:
            # First verify the plan exists and belongs to the user
            plan = await self.get_learning_plan(plan_id, user_id)
            if not plan:
                logger.warning(f"Plan not found or access denied: {plan_id} for user {user_id}")
                return False
            
            # Delete URL for Azure Search
            delete_url = f"{self.search_endpoint}/indexes/{self.index_name}/docs/index"
            delete_url += f"?api-version=2023-07-01-Preview"
            
            # Build request body for delete operation
            request_body = {
                "value": [
                    {
                        "@search.action": "delete",
                        "id": plan_id
                    }
                ]
            }
            
            # Execute delete request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    delete_url,
                    json=request_body,
                    headers={
                        "Content-Type": "application/json",
                        "api-key": self.search_key
                    }
                ) as response:
                    if response.status != 200 and response.status != 201:
                        response_text = await response.text()
                        logger.error(f"Azure Search error deleting plan: {response.status} - {response_text}")
                        return False
                    
                    # Parse response to check for errors
                    try:
                        result = await response.json()
                        if "value" in result:
                            for item in result["value"]:
                                if not item.get("status", False):
                                    logger.error(f"Error deleting learning plan: {item.get('errorMessage')}")
                                    return False
                    except json.JSONDecodeError:
                        # Some successful responses might not have a JSON body
                        pass
                    
                    logger.info(f"Successfully deleted learning plan {plan_id}")
                    return True
                
        except Exception as e:
            logger.error(f"Error deleting learning plan: {e}")
            return False
    
    async def generate_html_export(self, plan: LearningPlan) -> str:
        """
        Generate HTML representation of a learning plan for export.
        
        Args:
            plan: Learning plan to export
            
        Returns:
            HTML string representation of the learning plan
        """
        # Create HTML content with modern styling
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{plan.title} - Learning Plan</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3 {{
                    color: #2563eb;
                }}
                .plan-header {{
                    border-bottom: 2px solid #e5e7eb;
                    padding-bottom: 15px;
                    margin-bottom: 25px;
                }}
                .plan-meta {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 15px;
                    margin-bottom: 15px;
                    font-size: 0.9rem;
                    color: #6b7280;
                }}
                .plan-meta div {{
                    padding: 5px 10px;
                    background-color: #f3f4f6;
                    border-radius: 4px;
                }}
                .progress-container {{
                    margin: 20px 0;
                }}
                .progress-bar {{
                    height: 8px;
                    background-color: #e5e7eb;
                    border-radius: 4px;
                    overflow: hidden;
                }}
                .progress-fill {{
                    height: 100%;
                    background-color: #2563eb;
                    width: {plan.progress_percentage}%;
                }}
                .activity {{
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 15px;
                }}
                .activity-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                }}
                .activity-title {{
                    font-weight: 600;
                    font-size: 1.1rem;
                    margin: 0;
                }}
                .activity-meta {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    margin-top: 10px;
                    font-size: 0.8rem;
                }}
                .badge {{
                    padding: 3px 8px;
                    border-radius: 9999px;
                    font-weight: 500;
                }}
                .badge-blue {{
                    background-color: #dbeafe;
                    color: #1e40af;
                }}
                .badge-green {{
                    background-color: #dcfce7;
                    color: #166534;
                }}
                .badge-yellow {{
                    background-color: #fef3c7;
                    color: #92400e;
                }}
                .badge-gray {{
                    background-color: #f3f4f6;
                    color: #4b5563;
                }}
                .footer {{
                    margin-top: 40px;
                    text-align: center;
                    font-size: 0.8rem;
                    color: #6b7280;
                }}
                .learning-benefit {{
                    background-color: #dbeafe;
                    border-radius: 6px;
                    padding: 10px;
                    margin-top: 10px;
                }}
                .learning-benefit-title {{
                    font-weight: 600;
                    color: #1e40af;
                    margin-bottom: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="plan-header">
                <h1>{plan.title}</h1>
                <p>{plan.description}</p>
                <div class="plan-meta">
                    <div>Subject: {plan.subject}</div>
                    <div>Topics: {', '.join(plan.topics)}</div>
                    <div>Created: {plan.created_at.strftime("%Y-%m-%d")}</div>
                    <div>Status: {plan.status.value.replace('_', ' ').title()}</div>
                </div>
            </div>

            <div class="progress-container">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span>Progress</span>
                    <span>{plan.progress_percentage:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
            </div>

            <h2>Activities</h2>
        """
        
        # Add activities
        for activity in plan.activities:
            # Determine status badge color
            status_badge = "badge-gray"
            if activity.status == ActivityStatus.COMPLETED:
                status_badge = "badge-green"
            elif activity.status == ActivityStatus.IN_PROGRESS:
                status_badge = "badge-yellow"
                
            # Format activity
            activity_html = f"""
            <div class="activity">
                <div class="activity-header">
                    <h3 class="activity-title">{activity.title}</h3>
                    <span class="badge {status_badge}">{activity.status.value.replace('_', ' ').title()}</span>
                </div>
                <p>{activity.description}</p>
                <div class="activity-meta">
                    <span class="badge badge-blue">{activity.duration_minutes} minutes</span>
                    {f'<span>Completed on: {activity.completed_at.strftime("%Y-%m-%d")}</span>' if activity.completed_at else ''}
                </div>
            """
            
            # Add learning benefit if present
            if hasattr(activity, 'learning_benefit') and activity.learning_benefit:
                activity_html += f"""
                <div class="learning-benefit">
                    <div class="learning-benefit-title">How This Helps Learning:</div>
                    <p>{activity.learning_benefit}</p>
                </div>
                """
                
            # Add content link if present
            if hasattr(activity, 'content_url') and activity.content_url:
                activity_html += f"""
                <div style="margin-top: 15px;">
                    <a href="{activity.content_url}" target="_blank" style="color: #2563eb; text-decoration: none;">
                        Open Learning Resource →
                    </a>
                </div>
                """
            elif activity.content_id:
                activity_html += f"""
                <div style="margin-top: 15px;">
                    <span style="color: #6b7280;">Content ID: {activity.content_id}</span>
                </div>
                """
                
            # Close activity div
            activity_html += "</div>"
            html_content += activity_html
        
        # Add footer and close HTML
        html_content += f"""
            <div class="footer">
                <p>Generated on {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</p>
                <p>Personalized Learning Co-pilot</p>
            </div>
        </body>
        </html>
        """
        
        return html_content

# Singleton instance
learning_plan_service = None

async def get_learning_plan_service():
    """Get or create learning plan service singleton."""
    global learning_plan_service
    if learning_plan_service is None:
        learning_plan_service = AzureLearningPlanService()
    return learning_plan_service