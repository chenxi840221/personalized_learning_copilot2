# backend/api/learning_plan_routes.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status, Request
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import logging
import json
import asyncio

from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from auth.entra_auth import get_current_user
from services.azure_learning_plan_service import get_learning_plan_service
from rag.generator import get_plan_generator
from rag.retriever import retrieve_relevant_content
from services.search_service import get_search_service

# Setup logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/learning-plans", tags=["learning-plans"])

@router.get("/")
async def get_learning_plans(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    limit: int = Query(50, description="Maximum number of plans to return"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all learning plans for the current user.
    
    Args:
        subject: Optional subject filter
        limit: Maximum number of plans to return
        current_user: Current authenticated user
        
    Returns:
        List of learning plans
    """
    try:
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Get learning plans
        plans = await learning_plan_service.get_learning_plans(
            user_id=current_user["id"],
            subject=subject,
            limit=limit
        )
        
        # Convert to JSON-serializable format
        return [plan.dict() for plan in plans]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting learning plans: {str(e)}"
        )

@router.post("/")
async def create_learning_plan(
    subject: str = Body(..., embed=True),
    learning_period: Optional[str] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new personalized learning plan.
    
    Args:
        subject: Subject for the learning plan
        learning_period: Optional period for the learning plan (one_week, two_weeks, one_month, two_months, school_term)
        current_user: Current authenticated user
        
    Returns:
        Created learning plan
    """
    try:
        # Create a user model from current user
        from models.user import User, LearningStyle
        
        user = User(
            id=current_user["id"],
            username=current_user["username"],
            email=current_user["email"],
            full_name=current_user.get("full_name", ""),
            grade_level=current_user.get("grade_level"),
            subjects_of_interest=current_user.get("subjects_of_interest", []),
            learning_style=LearningStyle(current_user.get("learning_style")) if current_user.get("learning_style") else None,
            is_active=True
        )
        
        # First try to get relevant content from Azure Search
        # Flag to track if we need to use fallback content
        use_fallback = False
        try:
            # Get relevant content for the learning plan with more items to ensure sufficient content for all activities
            logger.info(f"Searching for content for subject: {subject}")
            relevant_content = await retrieve_relevant_content(
                student_profile=user,
                subject=subject,
                k=15  # Get more content to ensure we have enough for all activities
            )
            
            # If we got results, log success
            if relevant_content:
                logger.info(f"✅ Found {len(relevant_content)} relevant content items for {subject}")
            else:
                logger.warning(f"⚠️ No content found in Azure Search for subject {subject}. Will try fallback.")
                use_fallback = True
        except Exception as e:
            logger.error(f"Error retrieving content from Azure Search: {e}")
            # Log detailed error information for debugging
            import traceback
            logger.debug(f"Full error details: {traceback.format_exc()}")
            relevant_content = []
            use_fallback = True
        
        # Add fallback content if no content was found
        if use_fallback or not relevant_content:
            logger.warning(f"🔄 Falling back to default content for subject {subject}")
            try:
                # Import fallback content function
                from scripts.add_fallback_content import get_fallback_content
                fallback_content = get_fallback_content(subject)
                if fallback_content:
                    logger.info(f"✅ Using {len(fallback_content)} fallback content items for {subject}")
                    relevant_content = fallback_content
                else:
                    logger.error(f"❌ No fallback content available for {subject}. This will cause planning errors.")
                    # Create bare minimum fallback content to prevent crashes
                    from models.content import Content, ContentType, DifficultyLevel
                    # uuid is already imported at the module level
                    
                    # Create a very basic fallback item for this subject
                    emergency_content = Content(
                        id=f"fallback-{uuid.uuid4()}",
                        title=f"Learning about {subject}",
                        description=f"A general introduction to {subject} concepts",
                        content_type=ContentType.ARTICLE,
                        subject=subject,
                        difficulty_level=DifficultyLevel.INTERMEDIATE,
                        url=f"https://example.com/{subject.lower().replace(' ', '-')}",
                        grade_level=[7, 8, 9],  # Middle school level as default
                        topics=[subject],
                        duration_minutes=30,
                        keywords=[subject],
                        source="Emergency Fallback Content"
                    )
                    relevant_content = [emergency_content]
                    logger.warning(f"Created emergency fallback content for {subject} to prevent application errors")
            except Exception as e:
                logger.error(f"Error getting fallback content: {e}")
                # Log detailed error information for debugging
                import traceback
                logger.debug(f"Fallback content error details: {traceback.format_exc()}")
        
        # Get plan generator
        plan_generator = await get_plan_generator()
        
        # Set up start and end dates based on learning period
        from models.learning_plan import LearningPeriod
        
        # Parse learning period from string to enum
        period = None
        if learning_period:
            try:
                period = LearningPeriod(learning_period)
            except ValueError:
                logger.warning(f"Invalid learning period: {learning_period}. Using default.")
                period = LearningPeriod.ONE_MONTH
        else:
            period = LearningPeriod.ONE_MONTH
        
        # Calculate days and activity_days
        days = LearningPeriod.to_days(period)
        # For very long periods, split into weeks and generate activities for all days
        weeks_in_period = (days + 6) // 7  # Ceiling division to get full weeks
        all_activities = []
        logger.info(f"Creating plan with {weeks_in_period} weeks for learning period: {period.value} ({days} days)")
        
        # Generate a plan for each week of the learning period
        for week_num in range(weeks_in_period):
            week_plan_dict = await plan_generator.generate_plan(
                student=user,
                subject=subject,
                relevant_content=relevant_content,
                days=7,  # Always use 7 days for a weekly plan
                is_weekly_plan=True
            )
            
            # Adjust day numbers to be relative to the entire learning period
            week_activities = week_plan_dict.get("activities", [])
            for activity in week_activities:
                # Update day number to be relative to the full learning period
                activity["day"] = activity["day"] + (week_num * 7)
                all_activities.append(activity)
        
        # Create a combined plan dictionary with all weeks' activities
        plan_dict = {
            "title": week_plan_dict.get("title", f"{subject} Learning Plan for {period.value.replace('_', ' ').title()}"),
            "description": f"A comprehensive {period.value.replace('_', ' ')} learning plan for {subject} spanning {weeks_in_period} weeks",
            "subject": week_plan_dict.get("subject", subject),
            "topics": week_plan_dict.get("topics", [subject]) if 'week_plan_dict' in locals() else [subject],
            "activities": all_activities
        }
        
        # Process activities to ensure each has associated content
        activities = []
        for i, activity_dict in enumerate(plan_dict.get("activities", [])):
            # Get existing content URL and ID from the activity
            content_url = activity_dict.get("content_url")
            content_id = activity_dict.get("content_id")
            matching_content = None
            
            # Try to find matching content if the activity has a content_id
            if content_id:
                matching_content = next(
                    (content for content in relevant_content if str(content.id) == content_id),
                    None
                )
                if matching_content and not content_url:
                    content_url = matching_content.url
            
            # If the activity doesn't have a content reference, assign one from available content
            if not content_id and relevant_content:
                # Pick a content item that hasn't been used yet
                used_content_ids = [a.get("content_id") for a in plan_dict.get("activities", []) if a.get("content_id")]
                unused_content = [c for c in relevant_content if str(c.id) not in used_content_ids]
                
                if unused_content:
                    # Use the first unused content
                    matching_content = unused_content[0]
                    content_id = str(matching_content.id)
                    content_url = matching_content.url
                    logger.info(f"Assigned content {content_id} to activity without content reference")
                elif relevant_content:
                    # If all content has been used, reuse the first item
                    matching_content = relevant_content[0]
                    content_id = str(matching_content.id)
                    content_url = matching_content.url
                    logger.info(f"Reused content {content_id} for activity without content reference")
            
            # Prepare content metadata with detailed information about the educational resource
            metadata = activity_dict.get("metadata", {"subject": subject})
            if matching_content:
                content_info = {
                    "title": matching_content.title,
                    "description": matching_content.description,
                    "subject": matching_content.subject,
                    "difficulty_level": matching_content.difficulty_level.value if hasattr(matching_content, "difficulty_level") else None,
                    "content_type": matching_content.content_type.value if hasattr(matching_content, "content_type") else None,
                    "grade_level": matching_content.grade_level if hasattr(matching_content, "grade_level") else None,
                    "url": matching_content.url
                }
                metadata["content_info"] = content_info
            
            # Update the activity dictionary with enhanced content information
            activity_dict["content_id"] = content_id
            activity_dict["content_url"] = content_url
            activity_dict["metadata"] = metadata
            
            # Add enhanced learning benefit if not present
            if "learning_benefit" not in activity_dict or not activity_dict["learning_benefit"]:
                # Create a detailed learning benefit that includes content information
                if matching_content:
                    activity_dict["learning_benefit"] = f"This activity helps develop skills in {subject} using {matching_content.title}. The educational resource is tailored to your learning style and grade level, providing an effective learning experience."
                else:
                    activity_dict["learning_benefit"] = f"This activity helps develop skills in {subject} by using educational resources tailored to your learning style and needs."
            
            activities.append(activity_dict)
        
        # Create learning plan object from the returned dictionary with enhanced activities
        now = datetime.utcnow()
        
        # Calculate start and end dates
        start_date = now
        end_date = now + timedelta(days=days)
        
        # Create metadata with learning period
        metadata = {
            "learning_period": period.value,
            "period_days": days,
            "weeks_in_period": weeks_in_period,
            "activity_days": days  # Now we create activities for all days
        }
        
        learning_plan = LearningPlan(
            id=str(uuid.uuid4()),
            student_id=user.id,
            title=plan_dict.get("title", f"{subject} Learning Plan for {period.value.replace('_', ' ').title()}"),
            description=plan_dict.get("description", f"A {period.value.replace('_', ' ')} learning plan for {subject}"),
            subject=plan_dict.get("subject", subject),
            topics=plan_dict.get("topics", [subject]),
            activities=[LearningActivity(**activity) for activity in activities],
            status=ActivityStatus.NOT_STARTED,
            progress_percentage=0.0,
            created_at=now,
            updated_at=now,
            start_date=start_date,
            end_date=end_date,
            metadata=metadata,
            owner_id=current_user["id"]  # Set the owner_id to the current user
        )
        
        # Get learning plan service and save the plan
        learning_plan_service = await get_learning_plan_service()
        success = await learning_plan_service.create_learning_plan(learning_plan)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save learning plan"
            )
        
        # Return the created plan
        return learning_plan.dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating learning plan: {str(e)}"
        )

@router.post("/profile-based")
async def create_profile_based_learning_plan(
    plan_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new personalized learning plan based on a student profile.
    
    Args:
        plan_data: Learning plan data with student_profile_id, optional learning_period
                  (one_week, two_weeks, one_month, two_months, school_term)
        current_user: Current authenticated user
        
    Returns:
        Task ID for tracking the learning plan creation
    """
    try:
        logger.info(f"Creating profile-based learning plan with data: {plan_data}")
        
        # Validate required fields
        student_profile_id = plan_data.get("student_profile_id")
        if not student_profile_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="student_profile_id is required"
            )
        
        # Import task tracker
        from utils import task_status_tracker
        
        # Create a new task for tracking
        task_id = task_status_tracker.create_task(
            user_id=current_user["id"],
            task_type="learning_plan_creation",
            params=plan_data
        )
        
        # Update task status to in_progress
        task_status_tracker.update_task_status(
            task_id=task_id,
            status=task_status_tracker.STATUS_IN_PROGRESS,
            progress=0,
            message="Starting learning plan creation",
            current_step="Validating input"
        )
        
        # Start a background task to create the learning plan
        asyncio.create_task(
            _create_profile_based_learning_plan_async(
                task_id=task_id,
                plan_data=plan_data,
                current_user=current_user
            )
        )
        
        # Return the task ID for tracking
        return {
            "task_id": task_id,
            "status": "in_progress",
            "message": "Learning plan creation started"
        }
        
    except Exception as e:
        logger.exception(f"Error initiating profile-based learning plan creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initiating learning plan creation: {str(e)}"
        )

async def _create_profile_based_learning_plan_async(
    task_id: str,
    plan_data: Dict[str, Any],
    current_user: Dict[str, Any]
):
    """
    Background task to create a learning plan based on a student profile.
    Updates task status as it progresses.
    
    Args:
        task_id: Task ID for status tracking
        plan_data: Learning plan data
        current_user: Current authenticated user
    """
    # Import task tracker
    from utils import task_status_tracker
    
    try:
        # Get the student profile
        task_status_tracker.update_task_status(
            task_id=task_id,
            progress=5,
            message="Retrieving student profile",
            current_step="Retrieving student profile"
        )
        
        student_profile_id = plan_data.get("student_profile_id")
        search_service = await get_search_service()
        if not search_service:
            task_status_tracker.update_task_status(
                task_id=task_id,
                status=task_status_tracker.STATUS_FAILED,
                message="Search service not available",
                error="Search service not available"
            )
            return
            
        # Find the student profile
        filter_expression = f"id eq '{student_profile_id}'"
        profiles = await search_service.search_documents(
            index_name="student-profiles",
            query="*",
            filter=filter_expression,
            top=1
        )
        
        if not profiles:
            task_status_tracker.update_task_status(
                task_id=task_id,
                status=task_status_tracker.STATUS_FAILED,
                message=f"Student profile with ID {student_profile_id} not found",
                error=f"Student profile with ID {student_profile_id} not found"
            )
            return
            
        student_profile = profiles[0]
        logger.info(f"Found student profile: {student_profile.get('full_name')}")
        
        # Create a user model from the student profile
        task_status_tracker.update_task_status(
            task_id=task_id,
            progress=10,
            message="Processing student profile",
            current_step="Processing student profile"
        )
        
        from models.user import User, LearningStyle
        
        # Handle learning style conversion safely
        learning_style_value = None
        if student_profile.get("learning_style"):
            try:
                # Convert to lowercase and try to match with enum
                ls_value = student_profile.get("learning_style", "").lower()
                
                # Map common learning style names to our enum values
                learning_style_mapping = {
                    "visual": LearningStyle.VISUAL,
                    "auditory": LearningStyle.AUDITORY,
                    "reading": LearningStyle.READING_WRITING,
                    "reading_writing": LearningStyle.READING_WRITING,
                    "read/write": LearningStyle.READING_WRITING,
                    "kinesthetic": LearningStyle.KINESTHETIC,
                    "tactile": LearningStyle.KINESTHETIC,
                    "mixed": LearningStyle.MIXED,
                    "multimodal": LearningStyle.MIXED
                }
                
                # Try to find a match
                if ls_value in learning_style_mapping:
                    learning_style_value = learning_style_mapping[ls_value]
                else:
                    # Fall back to mixed if no match
                    logger.warning(f"Unknown learning style: {student_profile.get('learning_style')}. Using 'mixed' instead.")
                    learning_style_value = LearningStyle.MIXED
            except Exception as e:
                logger.warning(f"Error processing learning style: {e}")
                learning_style_value = LearningStyle.MIXED
        
        # Extract student information from profile
        interests = student_profile.get("interests", [])
        strengths = student_profile.get("strengths", [])
        areas_for_improvement = student_profile.get("areas_for_improvement", [])
        
        # If areas_for_improvement is a string, convert it
        if isinstance(areas_for_improvement, str):
            try:
                areas_for_improvement = json.loads(areas_for_improvement)
            except:
                areas_for_improvement = [area.strip() for area in areas_for_improvement.split(",") if area.strip()]
        
        # Define known subjects (expanded list)
        task_status_tracker.update_task_status(
            task_id=task_id,
            progress=15,
            message="Analyzing student interests and strengths",
            current_step="Analyzing student profile"
        )
        
        known_subjects = [
            "Mathematics", "Math", "Algebra", "Geometry", "Calculus", 
            "Science", "Biology", "Chemistry", "Physics", 
            "English", "Literature", "Writing", "Grammar", "Reading",
            "History", "Social Studies", "Geography", "Civics", 
            "Art", "Music", "Physical Education", "PE", "Computer Science",
            "Technology", "Programming", "Foreign Languages", "Spanish", "French"
        ]
        
        # Map to main subject categories - more comprehensive mapping
        subject_categories = {
            "Mathematics": ["math", "mathematics", "algebra", "geometry", "calculus", "arithmetic", "statistics", "probability", "number theory"],
            "Science": ["science", "biology", "physics", "chemistry", "laboratory", "environment", "ecology", "astronomy", "earth science"],
            "English": ["english", "writing", "reading", "literature", "grammar", "vocabulary", "comprehension", "spelling", "composition"],
            "History": ["history", "social studies", "geography", "civics", "world history", "american history", "economics", "politics"],
            "Art": ["art", "creative", "drawing", "painting", "sculpture", "design", "photography", "visual arts"],
            "Music": ["music", "singing", "instruments", "composition", "theory", "orchestra", "band", "choir"],
            "Physical Education": ["physical education", "pe", "sports", "fitness", "exercise", "health", "teamwork"],
            "Computer Science": ["computer", "programming", "coding", "technology", "software", "web development", "app development"],
            "Foreign Languages": ["spanish", "french", "german", "chinese", "japanese", "latin", "language"]
        }
        
        # Extract subjects from student profile data
        def extract_subjects_from_terms(terms, categories):
            extracted_subjects = []
            for term in terms:
                term_lower = term.lower()
                for subject, keywords in categories.items():
                    # Match either direct subject name or keywords
                    if subject.lower() in term_lower or any(keyword in term_lower for keyword in keywords):
                        if subject not in extracted_subjects:
                            extracted_subjects.append(subject)
            return extracted_subjects
        
        # Extract subjects from different profile sections
        interest_subjects = extract_subjects_from_terms(interests, subject_categories)
        strength_subjects = extract_subjects_from_terms(strengths, subject_categories)
        improvement_subjects = extract_subjects_from_terms(areas_for_improvement, subject_categories)
        
        # Determine focus subjects (combining interests, strengths, and improvement areas with priority)
        focus_subjects = []
        
        # First add improvement areas as highest priority
        focus_subjects.extend(improvement_subjects)
        
        # Then add interests if not already included
        for subject in interest_subjects:
            if subject not in focus_subjects:
                focus_subjects.append(subject)
                
        # Then add strengths if not already included
        for subject in strength_subjects:
            if subject not in focus_subjects:
                focus_subjects.append(subject)
        
        # If we still don't have enough subjects, add common core subjects
        if len(focus_subjects) < 3:
            core_subjects = ["Mathematics", "Science", "English"]
            for subject in core_subjects:
                if subject not in focus_subjects:
                    focus_subjects.append(subject)
                    if len(focus_subjects) >= 3:
                        break
        
        task_status_tracker.update_task_status(
            task_id=task_id,
            progress=20,
            message=f"Identified {len(focus_subjects)} focus subjects: {', '.join(focus_subjects)}",
            current_step="Determining focus subjects"
        )
        
        # Create the user model
        user = User(
            id=student_profile_id,  # Use profile ID as user ID
            username=student_profile.get("full_name", "").replace(" ", "_").lower(),
            email=f"{student_profile_id}@example.com",  # Use placeholder email
            full_name=student_profile.get("full_name", ""),
            grade_level=student_profile.get("grade_level"),
            subjects_of_interest=focus_subjects,  # Use focus subjects as subjects of interest
            learning_style=learning_style_value,
            is_active=True,
            areas_for_improvement=improvement_subjects  # Add improvement areas to user model
        )
        
        # Get plan parameters
        plan_type = plan_data.get("type", "balanced")
        daily_minutes = plan_data.get("daily_minutes", 60)
        
        # Get learning period
        from models.learning_plan import LearningPeriod
        learning_period_str = plan_data.get("learning_period")
        
        # Parse learning period from string to enum
        period = None
        if learning_period_str:
            try:
                period = LearningPeriod(learning_period_str)
            except ValueError:
                logger.warning(f"Invalid learning period: {learning_period_str}. Using default.")
                period = LearningPeriod.ONE_MONTH
        else:
            period = LearningPeriod.ONE_MONTH
            
        # Calculate start and end dates
        now = datetime.utcnow()
        start_date = now
        days = LearningPeriod.to_days(period)
        end_date = now + timedelta(days=days)
        
        logger.info(f"Creating plan with learning period: {period.value} ({days} days)")
        weeks_in_period = (days + 6) // 7  # Ceiling division to get full weeks
        
        task_status_tracker.update_task_status(
            task_id=task_id,
            progress=25,
            message=f"Planning {period.value} learning period with {weeks_in_period} weeks",
            current_step="Planning learning period"
        )
        
        # Balance learning time across subjects
        subject_times = {}
        
        # Calculate time allocation with more sophisticated logic
        for subject in focus_subjects:
            # Start with base allocation
            base_time = daily_minutes / len(focus_subjects)
            
            # Apply multipliers based on categorization
            is_improvement_area = subject in improvement_subjects
            is_interest = subject in interest_subjects
            is_strength = subject in strength_subjects
            
            # Calculate adjusted time with weighted factors
            multiplier = 1.0
            if is_improvement_area:
                # Highest priority for improvement areas
                multiplier += 0.5
            if is_interest:
                # Boost for interests
                multiplier += 0.3
            if is_strength:
                # Slight reduction for strengths (unless also an interest)
                if not is_interest:
                    multiplier -= 0.2
            
            # Calculate adjusted time with a minimum threshold
            adjusted_time = max(10, int(base_time * multiplier))
            subject_times[subject] = adjusted_time
        
        # Normalize to ensure total matches daily_minutes
        total_allocated = sum(subject_times.values())
        scaling_factor = daily_minutes / total_allocated if total_allocated > 0 else 1
        for subject in subject_times:
            subject_times[subject] = max(10, int(subject_times[subject] * scaling_factor))
        
        logger.info(f"Focus subjects: {focus_subjects}")
        logger.info(f"Time allocation for subjects: {subject_times}")
        
        task_status_tracker.update_task_status(
            task_id=task_id,
            progress=30,
            message="Balanced time allocations for subjects",
            current_step="Calculating study time"
        )
        
        # Retrieve content for all subjects at once
        all_content = {}
        
        # Calculate total progress for content retrieval
        content_progress_total = 25  # Will go from 30% to 55%
        content_progress_per_subject = content_progress_total / len(focus_subjects)
        current_progress = 30
        
        # First try getting content for all subjects
        for i, subject in enumerate(focus_subjects):
            estimated_content_needed = min(30, weeks_in_period * 3)  # Get enough items for all weeks
            logger.info(f"Retrieving {estimated_content_needed} content items for {subject}")
            
            task_status_tracker.update_task_status(
                task_id=task_id,
                progress=int(current_progress),
                message=f"Retrieving content for {subject} ({i+1}/{len(focus_subjects)})",
                current_step="Retrieving educational content"
            )
            
            try:
                # Try to get relevant content from search
                relevant_content = await retrieve_relevant_content(
                    student_profile=user,
                    subject=subject,
                    grade_level=student_profile.get("grade_level"),
                    k=estimated_content_needed
                )
                
                if relevant_content:
                    logger.info(f"✅ Found {len(relevant_content)} relevant content items for {subject}")
                    all_content[subject] = relevant_content
                    
                    task_status_tracker.update_task_status(
                        task_id=task_id,
                        progress=int(current_progress + content_progress_per_subject * 0.8),
                        message=f"Found {len(relevant_content)} content items for {subject}",
                    )
                else:
                    logger.warning(f"⚠️ No content found in search for subject {subject}. Will try fallback.")
                    # Try fallback content
                    try:
                        task_status_tracker.update_task_status(
                            task_id=task_id,
                            progress=int(current_progress + content_progress_per_subject * 0.4),
                            message=f"Using fallback content for {subject}",
                        )
                        
                        from scripts.add_fallback_content import get_fallback_content
                        fallback_content = get_fallback_content(subject)
                        if fallback_content:
                            logger.info(f"✅ Using {len(fallback_content)} fallback content items for {subject}")
                            all_content[subject] = fallback_content
                            
                            task_status_tracker.update_task_status(
                                task_id=task_id,
                                progress=int(current_progress + content_progress_per_subject * 0.6),
                                message=f"Using {len(fallback_content)} fallback content items for {subject}",
                            )
                        else:
                            # Create emergency fallback
                            from models.content import Content, ContentType, DifficultyLevel
                            emergency_content = Content(
                                id=f"fallback-{uuid.uuid4()}",
                                title=f"Learning about {subject}",
                                description=f"A general introduction to {subject} concepts",
                                content_type=ContentType.ARTICLE,
                                subject=subject,
                                difficulty_level=DifficultyLevel.INTERMEDIATE,
                                url=f"https://example.com/{subject.lower().replace(' ', '-')}",
                                grade_level=[7, 8, 9],  # Middle school level as default
                                topics=[subject],
                                duration_minutes=30,
                                keywords=[subject],
                                source="Emergency Fallback Content"
                            )
                            all_content[subject] = [emergency_content]
                            logger.warning(f"Created emergency fallback content for {subject}")
                            
                            task_status_tracker.update_task_status(
                                task_id=task_id,
                                progress=int(current_progress + content_progress_per_subject * 0.5),
                                message=f"Created emergency content for {subject}",
                            )
                    except Exception as e:
                        logger.error(f"Error getting fallback content: {e}")
                        # Create minimal emergency content
                        from models.content import Content, ContentType, DifficultyLevel
                        emergency_content = Content(
                            id=f"fallback-{uuid.uuid4()}",
                            title=f"Learning about {subject}",
                            description=f"A general introduction to {subject} concepts",
                            content_type=ContentType.ARTICLE,
                            subject=subject,
                            difficulty_level=DifficultyLevel.INTERMEDIATE,
                            url=f"https://example.com/{subject.lower().replace(' ', '-')}",
                            grade_level=[7, 8, 9],
                            topics=[subject],
                            duration_minutes=30,
                            keywords=[subject],
                            source="Emergency Fallback Content"
                        )
                        all_content[subject] = [emergency_content]
                        
                        task_status_tracker.update_task_status(
                            task_id=task_id,
                            progress=int(current_progress + content_progress_per_subject * 0.5),
                            message=f"Created emergency content for {subject} after error",
                        )
            except Exception as e:
                logger.error(f"Error retrieving content for {subject}: {e}")
                # Create minimal emergency content 
                from models.content import Content, ContentType, DifficultyLevel
                emergency_content = Content(
                    id=f"fallback-{uuid.uuid4()}",
                    title=f"Learning about {subject}",
                    description=f"A general introduction to {subject} concepts",
                    content_type=ContentType.ARTICLE,
                    subject=subject,
                    difficulty_level=DifficultyLevel.INTERMEDIATE,
                    url=f"https://example.com/{subject.lower().replace(' ', '-')}",
                    grade_level=[7, 8, 9],
                    topics=[subject],
                    duration_minutes=30,
                    keywords=[subject],
                    source="Emergency Fallback Content"
                )
                all_content[subject] = [emergency_content]
                
                task_status_tracker.update_task_status(
                    task_id=task_id,
                    progress=int(current_progress + content_progress_per_subject * 0.5),
                    message=f"Created emergency content for {subject} after exception",
                )
            
            # Update progress for next subject
            current_progress += content_progress_per_subject
        
        # Create a weekly learning plan with activities from all subjects
        task_status_tracker.update_task_status(
            task_id=task_id,
            progress=55,
            message="Generating learning activities",
            current_step="Creating learning plan"
        )
        
        plan_generator = await get_plan_generator()
        all_activities = []
        
        # Track used content to avoid duplicates across weeks
        used_content_ids = set()
        
        # Calculate progress for weeks
        week_progress_total = 25  # Will go from 55% to 80%
        week_progress_per_week = week_progress_total / weeks_in_period
        current_progress = 55
        
        # For each week in the learning period, create a balanced set of activities
        for week_num in range(weeks_in_period):
            task_status_tracker.update_task_status(
                task_id=task_id,
                progress=int(current_progress),
                message=f"Creating plan for week {week_num+1}/{weeks_in_period}",
                current_step="Creating weekly plans"
            )
            
            # For each subject, generate activities for this week
            week_activities = []
            
            for subject, minutes in subject_times.items():
                if subject not in all_content:
                    logger.warning(f"No content available for subject {subject}, skipping")
                    continue
                
                # Get available content for this subject
                subject_content = all_content[subject]
                
                # Filter out content that's already been used
                available_content = [c for c in subject_content if str(c.id) not in used_content_ids]
                
                # If we're running low on content, reuse previously used content
                if len(available_content) < 3:
                    logger.info(f"Running low on unused content for {subject}, allowing reuse")
                    available_content = subject_content
                
                # Generate activities for this subject for this week
                try:
                    # Generate a mini plan for this subject for this week
                    subject_plan = await plan_generator.generate_plan(
                        student=user,
                        subject=subject,
                        relevant_content=available_content,
                        days=7,  # One week
                        is_weekly_plan=True
                    )
                    
                    # Get this subject's activities (usually 1-3 per day)
                    subject_activities = subject_plan.get("activities", [])
                    
                    # Limit the number of activities based on time allocation
                    # Default to 7 activities per week, adjusted by subject time allocation
                    activity_count = max(1, min(7, round(7 * minutes / daily_minutes)))
                    
                    # Ensure we get at least 1 and at most the number that were generated
                    activity_count = min(activity_count, len(subject_activities))
                    
                    # Select activities prioritizing different days of the week
                    selected_activities = []
                    day_coverage = set()
                    
                    # First pass: try to cover different days
                    for activity in subject_activities:
                        day = activity.get("day", 1)
                        if day not in day_coverage and len(selected_activities) < activity_count:
                            selected_activities.append(activity)
                            day_coverage.add(day)
                            # Track the content used 
                            if activity.get("content_id"):
                                used_content_ids.add(activity.get("content_id"))
                    
                    # Second pass: fill remaining slots if needed
                    remaining = activity_count - len(selected_activities)
                    if remaining > 0:
                        for activity in subject_activities:
                            if activity not in selected_activities and len(selected_activities) < activity_count:
                                selected_activities.append(activity)
                                # Track the content used
                                if activity.get("content_id"):
                                    used_content_ids.add(activity.get("content_id"))
                    
                    # Adjust day numbers for the week and add subject prefix
                    for activity in selected_activities:
                        # Update day to be relative to the full learning period
                        activity["day"] = activity.get("day", 1) + (week_num * 7)
                        # Add subject name to activity title
                        activity["title"] = f"{subject}: {activity.get('title', 'Activity')}"
                        # Add to week activities
                        week_activities.append(activity)
                
                except Exception as e:
                    logger.error(f"Error generating plan for subject {subject} in week {week_num+1}: {e}")
            
            # Add this week's activities to the overall plan
            all_activities.extend(week_activities)
            
            # Update progress
            current_progress += week_progress_per_week
            task_status_tracker.update_task_status(
                task_id=task_id,
                progress=int(current_progress),
                message=f"Completed week {week_num+1} plan with {len(week_activities)} activities",
            )
        
        # Create the complete learning plan with activities from all subjects and weeks
        task_status_tracker.update_task_status(
            task_id=task_id,
            progress=80,
            message="Finalizing learning plan",
            current_step="Finishing learning plan"
        )
        
        # Convert to LearningActivity objects with enhanced metadata
        activities = []
        
        for i, activity_dict in enumerate(all_activities):
            # Extract the subject from the title
            activity_subject = activity_dict.get("title", "").split(":", 1)[0].strip() if ":" in activity_dict.get("title", "") else "General"
            
            # Get content references
            content_url = activity_dict.get("content_url")
            content_id = activity_dict.get("content_id")
            matching_content = None
            
            # Find matching content
            if content_id and activity_subject in all_content:
                matching_content = next(
                    (c for c in all_content[activity_subject] if str(c.id) == content_id),
                    None
                )
                
                if matching_content and not content_url:
                    content_url = matching_content.url
            
            # If no content reference, assign one
            if not content_id and activity_subject in all_content:
                # Try to find unused content
                unused_content = [c for c in all_content[activity_subject] if str(c.id) not in used_content_ids]
                
                if unused_content:
                    matching_content = unused_content[0]
                elif all_content[activity_subject]:
                    matching_content = all_content[activity_subject][0]
                
                if matching_content:
                    content_id = str(matching_content.id)
                    content_url = matching_content.url
                    used_content_ids.add(content_id)
            
            # Create metadata
            content_metadata = {"subject": activity_subject}
            if matching_content:
                content_info = {
                    "title": matching_content.title,
                    "description": matching_content.description,
                    "subject": matching_content.subject,
                    "difficulty_level": matching_content.difficulty_level.value if hasattr(matching_content, "difficulty_level") else None,
                    "content_type": matching_content.content_type.value if hasattr(matching_content, "content_type") else None,
                    "grade_level": matching_content.grade_level if hasattr(matching_content, "grade_level") else None,
                    "url": matching_content.url
                }
                content_metadata["content_info"] = content_info
            
            # Create or use learning benefit
            learning_benefit = activity_dict.get("learning_benefit")
            if not learning_benefit and matching_content:
                learning_benefit = f"This activity helps develop skills in {activity_subject} using {matching_content.title}. The educational resource is tailored to the student's learning style and grade level, providing an effective learning experience."
            elif not learning_benefit:
                learning_benefit = f"This activity helps develop skills in {activity_subject} using educational resources tailored to the student's learning style and needs."
            
            # Create the activity
            activity = LearningActivity(
                id=str(uuid.uuid4()),
                title=activity_dict.get("title", f"Activity {i+1}"),
                description=activity_dict.get("description", "Complete this activity"),
                content_id=content_id,
                content_url=content_url,
                duration_minutes=activity_dict.get("duration_minutes", 15),
                order=i + 1,
                day=activity_dict.get("day", 1),
                status=ActivityStatus.NOT_STARTED,
                learning_benefit=learning_benefit,
                metadata=activity_dict.get("metadata", content_metadata)
            )
            activities.append(activity)
        
        task_status_tracker.update_task_status(
            task_id=task_id,
            progress=85,
            message=f"Created {len(activities)} learning activities",
        )
        
        # Sort activities by day and order
        activities.sort(key=lambda x: (x.day, x.order))
        
        # Create the final learning plan
        period_name = period.value.replace('_', ' ').title()
        learning_plan = LearningPlan(
            id=str(uuid.uuid4()),
            student_id=user.id,
            title=f"Personalized Learning Plan for {user.full_name} - {period_name}",
            description=f"A balanced {period_name} learning plan with {daily_minutes} minutes of daily study across {len(focus_subjects)} subjects, tailored to {user.full_name}'s interests, strengths, and areas for improvement.",
            subject="Multiple Subjects",
            topics=focus_subjects,
            activities=activities,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            start_date=start_date,
            end_date=end_date,
            status=ActivityStatus.NOT_STARTED,
            progress_percentage=0.0,
            metadata={
                "plan_type": plan_type,
                "daily_minutes": daily_minutes,
                "focus_areas": focus_subjects,
                "interest_areas": interest_subjects,
                "strength_areas": strength_subjects,
                "improvement_areas": improvement_subjects,
                "student_profile_id": student_profile_id,
                "learning_period": period.value,
                "period_days": days
            },
            owner_id=current_user["id"]  # Set the owner_id to the current user
        )
        
        task_status_tracker.update_task_status(
            task_id=task_id,
            progress=90,
            message="Saving learning plan",
            current_step="Saving plan"
        )
        
        # Get learning plan service and save the plan
        learning_plan_service = await get_learning_plan_service()
        success = await learning_plan_service.create_learning_plan(learning_plan)
        
        if not success:
            task_status_tracker.update_task_status(
                task_id=task_id,
                status=task_status_tracker.STATUS_FAILED,
                progress=95,
                message="Failed to save learning plan",
                error="Failed to save learning plan to database"
            )
            return
        
        # Success! Update task status
        task_status_tracker.update_task_status(
            task_id=task_id,
            status=task_status_tracker.STATUS_COMPLETED,
            progress=100,
            message="Learning plan created successfully",
            result=learning_plan.dict()
        )
        
    except Exception as e:
        logger.exception(f"Error creating profile-based learning plan: {e}")
        # Update task status with error
        task_status_tracker.update_task_status(
            task_id=task_id,
            status=task_status_tracker.STATUS_FAILED,
            message=f"Error creating learning plan: {str(e)}",
            error=str(e)
        )

@router.get("/{plan_id}")
async def get_learning_plan(
    plan_id: str = Path(..., description="Learning plan ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a specific learning plan.
    
    Args:
        plan_id: Learning plan ID
        current_user: Current authenticated user
        
    Returns:
        Learning plan
    """
    try:
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Get learning plan
        plan = await learning_plan_service.get_learning_plan(
            plan_id=plan_id,
            user_id=current_user["id"]
        )
        
        if not plan:
            return JSONResponse(
                content={"detail": "Learning plan not found"},
                status_code=status.HTTP_404_NOT_FOUND,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
        # Return the plan
        return plan.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            content={"detail": f"Error getting learning plan: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )

@router.options("/{path:path}")
async def options_learning_plan(
    request: Request,
    path: str
):
    """Handle OPTIONS preflight request for all plan operations."""
    origin = request.headers.get("origin", "*")
    logger.info(f"Handling OPTIONS request for /learning-plans/{path} from origin: {origin}")
    
    return JSONResponse(
        content={"detail": "OK"},
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400",
        }
    )

@router.delete("/{plan_id}")
async def delete_learning_plan(
    plan_id: str = Path(..., description="Learning plan ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None
):
    """
    Delete a learning plan.
    
    Args:
        plan_id: Learning plan ID
        current_user: Current authenticated user
        request: The request object to extract origin
        
    Returns:
        Success message
    """
    try:
        # Log the incoming request
        logger.info(f"Processing DELETE request for learning plan: {plan_id}")
        origin = request.headers.get("origin", "*") if request else "*"
        logger.info(f"Request origin: {origin}")
        
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Check if plan exists and belongs to user
        plan = await learning_plan_service.get_learning_plan(
            plan_id=plan_id,
            user_id=current_user["id"]
        )
        
        if not plan:
            return JSONResponse(
                content={"detail": "Learning plan not found"},
                status_code=status.HTTP_404_NOT_FOUND,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
        # Delete the learning plan
        success = await learning_plan_service.delete_learning_plan(
            plan_id=plan_id,
            user_id=current_user["id"]
        )
        
        if not success:
            return JSONResponse(
                content={"detail": "Failed to delete learning plan"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
        # Return success with explicit CORS headers
        logger.info(f"Successfully deleted learning plan {plan_id}")
        return JSONResponse(
            content={"message": "Learning plan deleted successfully"},
            status_code=status.HTTP_200_OK,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )
        
    except Exception as e:
        logger.exception(f"Error deleting learning plan: {e}")
        # Add CORS headers to generic exception responses
        origin = request.headers.get("origin", "*") if request else "*"
        return JSONResponse(
            content={"detail": f"Error deleting learning plan: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )

@router.put("/{plan_id}")
async def update_learning_plan(
    plan_id: str = Path(..., description="Learning plan ID"),
    plan_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update a learning plan.
    
    Args:
        plan_id: Learning plan ID
        plan_data: Updated plan data
        current_user: Current authenticated user
        
    Returns:
        Updated learning plan
    """
    try:
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Check if plan exists and belongs to user
        existing_plan = await learning_plan_service.get_learning_plan(
            plan_id=plan_id,
            user_id=current_user["id"]
        )
        
        if not existing_plan:
            return JSONResponse(
                content={"detail": "Learning plan not found"},
                status_code=status.HTTP_404_NOT_FOUND,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
        # Update fields from plan_data
        for field, value in plan_data.items():
            # Skip id, student_id, and owner_id fields for security
            if field not in ["id", "student_id", "owner_id"]:
                setattr(existing_plan, field, value)
        
        # Always update the updated_at timestamp
        existing_plan.updated_at = datetime.utcnow()
        
        # Update the learning plan
        updated_plan = await learning_plan_service.update_learning_plan(
            plan=existing_plan,
            user_id=current_user["id"]
        )
        
        if not updated_plan:
            return JSONResponse(
                content={"detail": "Failed to update learning plan"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
        # Return the updated plan
        return updated_plan.dict()
        
    except Exception as e:
        return JSONResponse(
            content={"detail": f"Error updating learning plan: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )

@router.get("/{plan_id}/export")
async def export_learning_plan(
    plan_id: str = Path(..., description="Learning plan ID"),
    format: str = Query("json", description="Export format (json, pdf, html)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Export a learning plan in the specified format.
    
    Args:
        plan_id: Learning plan ID
        format: Export format (json, pdf, html)
        current_user: Current authenticated user
        
    Returns:
        Learning plan in the specified format
    """
    try:
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Get learning plan
        plan = await learning_plan_service.get_learning_plan(
            plan_id=plan_id,
            user_id=current_user["id"]
        )
        
        if not plan:
            return JSONResponse(
                content={"detail": "Learning plan not found"},
                status_code=status.HTTP_404_NOT_FOUND,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
        # Format as requested
        if format.lower() == "json":
            # Return the plan as JSON
            return plan.dict()
        elif format.lower() == "html":
            # Generate HTML representation
            html_content = await learning_plan_service.generate_html_export(plan)
            return {"content": html_content, "format": "html"}
        elif format.lower() == "pdf":
            # PDF not directly supported yet, fall back to HTML
            html_content = await learning_plan_service.generate_html_export(plan)
            return {
                "content": html_content, 
                "format": "html",
                "message": "PDF format is not currently supported. HTML content provided instead."
            }
        else:
            return JSONResponse(
                content={"detail": f"Unsupported export format: {format}"},
                status_code=status.HTTP_400_BAD_REQUEST,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
    except Exception as e:
        return JSONResponse(
            content={"detail": f"Error exporting learning plan: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )

@router.options("/{plan_id}/activities/{activity_id}")
async def options_activity_status(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID")
):
    """Handle OPTIONS preflight request for activity status updates."""
    return JSONResponse(
        content={"detail": "OK"},
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400",
        }
    )

@router.put("/{plan_id}/activities/{activity_id}", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def update_activity_status(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID"),
    activity_status: str = Body(..., embed=True, alias="status"),  # Renamed to avoid conflict
    completed_at: Optional[str] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user),
    request: Request = None
) -> Dict[str, Any]:
    """
    Update the status of a learning activity.
    
    Args:
        plan_id: Learning plan ID
        activity_id: Activity ID
        status: New status (not_started, in_progress, completed)
        completed_at: Optional completion date (ISO format)
        current_user: Current authenticated user
        
    Returns:
        Status update information
    """
    try:
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Log request details for debugging
        logger.info(f"Updating activity status for plan {plan_id}, activity {activity_id} to {activity_status}")
        origin = request.headers.get("origin", "*") if request else "*"
        
        # Parse status
        try:
            parsed_status = ActivityStatus(activity_status)
        except ValueError:
            logger.warning(f"Invalid status provided: {activity_status}")
            return JSONResponse(
                content={"detail": f"Invalid status: {activity_status}. Must be one of: not_started, in_progress, completed"},
                status_code=status.HTTP_400_BAD_REQUEST,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
        # Parse completed_at date if provided
        completion_date = None
        if completed_at:
            try:
                completion_date = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid date format: {completed_at}")
                return JSONResponse(
                    content={"detail": f"Invalid completed_at date format: {completed_at}. Must be ISO format"},
                    status_code=status.HTTP_400_BAD_REQUEST,
                    headers={
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Allow-Credentials": "true",
                    }
                )
        
        # Update activity status
        try:
            result = await learning_plan_service.update_activity_status(
                plan_id=plan_id,
                activity_id=activity_id,
                status=parsed_status,  # Using the parsed status
                completed_at=completion_date,
                user_id=current_user["id"]
            )
            
            if not result:
                logger.warning(f"Learning plan {plan_id} or activity {activity_id} not found")
                return JSONResponse(
                    content={"detail": "Learning plan or activity not found"},
                    status_code=status.HTTP_404_NOT_FOUND,
                    headers={
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Allow-Credentials": "true",
                    }
                )
            
            # Ensure we return a valid JSON response
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Activity status updated successfully",
                    "plan_id": plan_id,
                    "activity_id": activity_id,
                    "status": activity_status,
                    "progress_percentage": result.get("progress_percentage", 0.0),
                    "plan_status": result.get("plan_status", "unknown")
                },
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        except Exception as service_error:
            logger.error(f"Service error updating activity: {service_error}")
            return JSONResponse(
                content={"detail": f"Error in learning plan service: {str(service_error)}"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )
        
    except Exception as e:
        logger.exception(f"Unhandled error updating activity status: {e}")
        origin = request.headers.get("origin", "*") if request else "*"
        return JSONResponse(
            content={"detail": f"Error updating activity status: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )