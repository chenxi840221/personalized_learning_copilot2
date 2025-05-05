# backend/api/learning_plan_routes.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import logging
import json

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
        Created learning plan
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
            
        # Get the student profile
        search_service = await get_search_service()
        if not search_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service not available"
            )
            
        # Find the student profile
        filter_expression = f"id eq '{student_profile_id}'"
        profiles = await search_service.search_documents(
            index_name="student-profiles",
            query="*",
            filter=filter_expression,
            top=1
        )
        
        if not profiles:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student profile with ID {student_profile_id} not found"
            )
            
        student_profile = profiles[0]
        logger.info(f"Found student profile: {student_profile.get('full_name')}")
        
        # Create a user model from the student profile
        from models.user import User, LearningStyle
        
        # Extract subjects of interest from profile strengths and interests if available
        subjects_of_interest = []
        known_subjects = ["Mathematics", "Math", "Science", "English", "History", "Geography", "Art", "Music", "Physical Education", "PE"]
        
        # Add interests to subjects_of_interest
        if "interests" in student_profile and student_profile["interests"]:
            interests_subjects = [interest for interest in student_profile["interests"] 
                                if any(subject.lower() in interest.lower() for subject in known_subjects)]
            subjects_of_interest.extend(interests_subjects)
            
        # Add strengths to subjects_of_interest
        if "strengths" in student_profile and student_profile["strengths"]:
            # Keep only subject names from strengths (Math, Science, etc.)
            strength_subjects = [strength for strength in student_profile["strengths"] 
                              if any(subject.lower() in strength.lower() for subject in known_subjects)]
            # Add strengths that aren't already in subjects_of_interest
            for strength in strength_subjects:
                if strength not in subjects_of_interest:
                    subjects_of_interest.append(strength)
            
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
        
        user = User(
            id=student_profile_id,  # Use profile ID as user ID
            username=student_profile.get("full_name", "").replace(" ", "_").lower(),
            email=f"{student_profile_id}@example.com",  # Use placeholder email
            full_name=student_profile.get("full_name", ""),
            grade_level=student_profile.get("grade_level"),
            subjects_of_interest=subjects_of_interest,
            learning_style=learning_style_value,
            is_active=True
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
        
        # For balanced plans, we need to determine subjects and time allocation
        if plan_type == "balanced":
            # Analyze the student profile to create a balanced plan across subjects
            # For example, allocate more time to subjects in areas_for_improvement
            # and less time to subjects in strengths
            
            # Get improvement areas, strengths, and interests
            areas_for_improvement = student_profile.get("areas_for_improvement", [])
            strengths = student_profile.get("strengths", [])
            interests = student_profile.get("interests", [])
            
            # Map to main subject categories
            subject_categories = {
                "Mathematics": ["math", "mathematics", "algebra", "geometry", "calculus", "arithmetic"],
                "Science": ["science", "biology", "physics", "chemistry", "laboratory"],
                "English": ["english", "writing", "reading", "literature", "grammar", "vocabulary"],
                "History": ["history", "social studies", "geography", "civics"],
                "Art": ["art", "creative", "drawing", "painting"]
            }
            
            # Determine which subjects need more attention
            focus_subjects = []
            for area in areas_for_improvement:
                area_lower = area.lower()
                for subject, keywords in subject_categories.items():
                    if any(keyword in area_lower for keyword in keywords):
                        if subject not in focus_subjects:
                            focus_subjects.append(subject)
            
            # Determine which subjects are strengths
            strong_subjects = []
            for strength in strengths:
                strength_lower = strength.lower()
                for subject, keywords in subject_categories.items():
                    if any(keyword in strength_lower for keyword in keywords):
                        if subject not in strong_subjects:
                            strong_subjects.append(subject)
                            
            # Determine which subjects are interests
            interest_subjects = []
            for interest in interests:
                interest_lower = interest.lower()
                for subject, keywords in subject_categories.items():
                    if any(keyword in interest_lower for keyword in keywords):
                        if subject not in interest_subjects:
                            interest_subjects.append(subject)
            
            # If no focus subjects identified, use interests and strengths, then default to main subjects
            if not focus_subjects:
                # First try to use interests
                if interest_subjects:
                    focus_subjects = interest_subjects
                # Then try to use strengths
                elif strong_subjects:
                    focus_subjects = strong_subjects
                # Default to all subjects
                else:
                    focus_subjects = list(subject_categories.keys())
                
            # Generate plans for each focus subject
            all_plans = []
            time_per_subject = daily_minutes // len(focus_subjects)
            
            # Calculate time allocation - prioritize areas of improvement and interests
            subject_times = {}
            for subject in focus_subjects:
                # Base allocation
                base_time = time_per_subject
                
                # Apply multipliers based on subject categorization
                in_areas_for_improvement = subject in focus_subjects and subject not in strong_subjects
                in_interests = subject in interest_subjects
                is_strength = subject in strong_subjects
                
                # Start with base time
                adjusted_time = base_time
                
                # Apply multipliers in priority order
                if in_areas_for_improvement:
                    # Most time for subjects needing improvement
                    adjusted_time = max(15, int(base_time * 1.3))
                elif in_interests:
                    # More time for interests
                    adjusted_time = max(12, int(base_time * 1.1))
                elif is_strength:
                    # Less time for strengths (unless they're also interests)
                    adjusted_time = max(10, int(base_time * 0.7))
                
                subject_times[subject] = adjusted_time
            
            # Adjust total to match daily_minutes
            total_allocated = sum(subject_times.values())
            scaling_factor = daily_minutes / total_allocated if total_allocated > 0 else 1
            for subject in subject_times:
                subject_times[subject] = max(10, int(subject_times[subject] * scaling_factor))
                
            logger.info(f"Time allocation for subjects: {subject_times}")
            
            # Create separate plans for each subject
            combined_activities = []
            
            for subject, minutes in subject_times.items():
                # Get relevant content for the subject - ask for more content to ensure we have enough
                # Estimate how many content items we need for the entire learning period
                # For weekly planning, we need about 3-5 activities per day × 7 days × number of weeks
                weeks_in_period = (days + 6) // 7  # Ceiling division to get full weeks
                estimated_content_needed = min(30, weeks_in_period * 7 * 3)  # Maximum 30 to avoid API limits
                
                logger.info(f"Retrieving {estimated_content_needed} content items for {subject} to cover {weeks_in_period} weeks")
                
                # Flag to track if we need to use fallback content
                use_fallback = False
                try:
                    # Try to get relevant content from search
                    relevant_content = await retrieve_relevant_content(
                        student_profile=user,
                        subject=subject,
                        grade_level=student_profile.get("grade_level"),
                        k=estimated_content_needed  # Request more content to ensure we have enough for all weeks
                    )
                    
                    # If we got results, log success
                    if relevant_content:
                        logger.info(f"✅ Found {len(relevant_content)} relevant content items for {subject}")
                    else:
                        logger.warning(f"⚠️ No content found in search for subject {subject}. Will try fallback.")
                        use_fallback = True
                except Exception as e:
                    logger.error(f"Error retrieving content from search: {e}")
                    # Log detailed error for debugging
                    import traceback
                    logger.debug(f"Full error details: {traceback.format_exc()}")
                    relevant_content = []
                    use_fallback = True
                
                # Add fallback content if no content was found or there was an error
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
                        # Log detailed error for debugging
                        import traceback
                        logger.debug(f"Fallback content error details: {traceback.format_exc()}")
                
                # Get plan generator
                plan_generator = await get_plan_generator()
                
                # Create mini-plan for the subject with days
                # Note: Using generate_plan (the method that exists in LearningPlanGenerator)
                # instead of create_learning_plan which doesn't exist
                
                # For weekly planning, always use 7 days per week
                # We'll create activities for all weeks of the learning period
                weeks_in_period = (days + 6) // 7  # Ceiling division to get full weeks
                all_activities = []
                
                logger.info(f"Creating balanced plan for subject {subject} with {weeks_in_period} weeks")
                
                # For each week, generate a weekly plan
                for week_num in range(weeks_in_period):
                    week_plan_dict = await plan_generator.generate_plan(
                        student=user,
                        subject=subject,
                        relevant_content=relevant_content,
                        days=7,  # Always 7 days for a week
                        is_weekly_plan=True
                    )
                    
                    # Offset the day numbers based on the week number
                    week_activities = week_plan_dict.get("activities", [])
                    for activity in week_activities:
                        # Update day number to be relative to the full learning period
                        activity["day"] = activity["day"] + (week_num * 7)
                        all_activities.append(activity)
                
                # Create a combined plan dictionary
                plan_dict = {
                    "title": f"{subject} Learning Plan for {period.value.replace('_', ' ').title()}",
                    "description": f"A comprehensive {period.value.replace('_', ' ')} learning plan for {subject} spanning {weeks_in_period} weeks",
                    "subject": subject,
                    "topics": week_plan_dict.get("topics", [subject]),
                    "activities": all_activities
                }
                
                # Create a mini plan manually from the plan dictionary
                # The generator doesn't have parameters for max_activities,
                # so we'll limit the activities after generation
                mini_plan = LearningPlan(
                    id=str(uuid.uuid4()),
                    student_id=user.id,
                    title=plan_dict.get("title", f"{subject} Learning Plan"),
                    description=plan_dict.get("description", f"Plan for {subject}"),
                    subject=subject,
                    topics=plan_dict.get("topics", [subject]),
                    activities=[],  # Will add only the needed activities
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    status=ActivityStatus.NOT_STARTED,
                    progress_percentage=0.0,
                    owner_id=current_user["id"]  # Set the owner_id to the current user
                )
                
                # Add only up to 2 activities (for balancing across subjects)
                activities_to_add = []
                for i, activity_dict in enumerate(plan_dict.get("activities", [])[:2]):  # Limit to first 2
                    # Get content URL from either the activity or the matched content
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
                    content_metadata = {"subject": subject}
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
                    
                    # Ensure we have a good learning benefit
                    learning_benefit = activity_dict.get("learning_benefit")
                    if not learning_benefit:
                        # Create a detailed learning benefit that includes content information
                        if matching_content:
                            learning_benefit = f"This activity helps develop {subject} skills using {matching_content.title}. The educational resource is tailored to the student's learning style and grade level, providing an effective learning experience."
                        else:
                            learning_benefit = f"This activity helps develop {subject} skills by using educational resources tailored to the student's learning style and needs."
                    
                    # Create enhanced activity with appropriate duration and content reference
                    activity = LearningActivity(
                        id=str(uuid.uuid4()),
                        title=activity_dict.get("title", f"Activity {i+1}"),
                        description=activity_dict.get("description", "Complete this activity"),
                        content_id=content_id,
                        content_url=content_url,
                        # Scale duration to fit within allocated minutes
                        duration_minutes=min(activity_dict.get("duration_minutes", 15), 
                                            int(minutes / 2)),  # Cap at half the allocated time
                        order=i + 1,
                        status=ActivityStatus.NOT_STARTED,
                        learning_benefit=learning_benefit,
                        metadata=activity_dict.get("metadata", content_metadata)
                    )
                    activities_to_add.append(activity)
                
                # Set the activities on the mini plan
                mini_plan.activities = activities_to_add
                
                # Add activities to the combined list
                for i, activity in enumerate(mini_plan.activities):
                    activity.id = str(uuid.uuid4())  # Ensure unique IDs
                    activity.title = f"{subject}: {activity.title}"  # Prefix with subject
                    activity.order = len(combined_activities) + i + 1  # Update order
                    combined_activities.append(activity)
                
            # Create the combined plan
            period_name = period.value.replace('_', ' ').title()
            learning_plan = LearningPlan(
                id=str(uuid.uuid4()),
                student_id=user.id,
                title=f"Balanced Learning Plan for {user.full_name} - {period_name}",
                description=f"A personalized {period_name} learning plan with {daily_minutes} minutes of daily balanced study across multiple subjects.",
                subject="Multiple Subjects",
                topics=focus_subjects,
                activities=combined_activities,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                start_date=start_date,
                end_date=end_date,
                status=ActivityStatus.NOT_STARTED,
                progress_percentage=0.0,
                metadata={
                    "plan_type": "balanced",
                    "daily_minutes": daily_minutes,
                    "focus_areas": focus_subjects,
                    "interest_areas": interest_subjects,
                    "strength_areas": strong_subjects,
                    "improvement_areas": [s for s in focus_subjects if s not in strong_subjects],
                    "student_profile_id": student_profile_id,
                    "learning_period": period.value,
                    "period_days": days
                },
                owner_id=current_user["id"]  # Set the owner_id to the current user
            )
            
        else:
            # For single subject plans, use the specified subject
            subject = plan_data.get("subject")
            if not subject:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="subject is required for focused plans"
                )
                
            # Extract areas for improvement from student profile, if available
            areas_for_improvement = student_profile.get("areas_for_improvement", [])
            if isinstance(areas_for_improvement, str):
                # If it's a string, try to parse as JSON or split by commas
                try:
                    areas_for_improvement = json.loads(areas_for_improvement)
                except:
                    areas_for_improvement = [area.strip() for area in areas_for_improvement.split(",") if area.strip()]
            
            # Add areas_for_improvement to the user model
            user.areas_for_improvement = areas_for_improvement
            
            logger.info(f"Retrieving content for student profile: grade_level={student_profile.get('grade_level')}, subject={subject}")
            logger.info(f"Areas for improvement: {areas_for_improvement}")
            
            # Get relevant content for the subject with enhanced filtering based on student profile
            # Estimate how many content items we need for the entire learning period
            weeks_in_period = (days + 6) // 7  # Ceiling division to get full weeks
            estimated_content_needed = min(40, weeks_in_period * 7 * 3)  # Maximum 40 to avoid API limits
            
            logger.info(f"Retrieving {estimated_content_needed} content items for focused {subject} plan to cover {weeks_in_period} weeks")
            
            # Flag to track if we need to use fallback content
            use_fallback = False
            try:
                # Try to get relevant content from search
                relevant_content = await retrieve_relevant_content(
                    student_profile=user,
                    subject=subject,
                    grade_level=student_profile.get("grade_level"),
                    k=estimated_content_needed  # Get enough content for all weeks of the learning period
                )
                
                # If we got results, log success
                if relevant_content:
                    logger.info(f"✅ Found {len(relevant_content)} relevant content items for {subject}")
                else:
                    logger.warning(f"⚠️ No content found in search for subject {subject}. Will try fallback.")
                    use_fallback = True
            except Exception as e:
                logger.error(f"Error retrieving content from search: {e}")
                # Log detailed error for debugging
                import traceback
                logger.debug(f"Full error details: {traceback.format_exc()}")
                relevant_content = []
                use_fallback = True
            
            # Add fallback content if no content was found or there was an error
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
                    # Log detailed error for debugging
                    import traceback
                    logger.debug(f"Fallback content error details: {traceback.format_exc()}")
            
            logger.info(f"Retrieved {len(relevant_content)} relevant content items for learning plan")
            
            # Get plan generator
            plan_generator = await get_plan_generator()
            
            # For weekly planning, determine how many weeks we need for the full learning period
            weeks_in_period = (days + 6) // 7  # Ceiling division to get full weeks
            all_activities = []
            
            logger.info(f"Creating focused plan for subject {subject} with {weeks_in_period} weeks")
            
            # Generate a plan for each week of the learning period
            for week_num in range(weeks_in_period):
                # For each week, generate a weekly plan using 7 days
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
                "title": f"{subject} Learning Plan for {period.value.replace('_', ' ').title()}",
                "description": f"A comprehensive {period.value.replace('_', ' ')} learning plan for {subject} spanning {weeks_in_period} weeks",
                "subject": subject,
                "topics": week_plan_dict.get("topics", [subject]) if 'week_plan_dict' in locals() else [subject],
                "activities": all_activities
            }
            
            # Convert to LearningPlan object with enhanced activity details
            activities = []
            for i, activity_dict in enumerate(plan_dict.get("activities", [])):
                # Get any existing content URL and ID from the activity
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
                content_metadata = {"subject": subject}
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
                
                # Ensure we have a good learning benefit
                learning_benefit = activity_dict.get("learning_benefit")
                if not learning_benefit:
                    # Create a detailed learning benefit that includes content information
                    if matching_content:
                        learning_benefit = f"This activity helps develop skills in {subject} using {matching_content.title}. The educational resource is tailored to the student's learning style and grade level, providing an effective learning experience."
                    else:
                        learning_benefit = f"This activity helps develop skills in {subject} by using educational resources tailored to the student's learning style and needs."
                
                # Create enhanced activity with new fields and ensure it has content
                activity = LearningActivity(
                    id=str(uuid.uuid4()),
                    title=activity_dict.get("title", f"Activity {i+1}"),
                    description=activity_dict.get("description", "Complete this activity"),
                    content_id=content_id,
                    content_url=content_url,
                    duration_minutes=activity_dict.get("duration_minutes", 15),
                    order=i + 1,
                    status=ActivityStatus.NOT_STARTED,
                    learning_benefit=learning_benefit,
                    metadata=activity_dict.get("metadata", content_metadata)
                )
                activities.append(activity)
                
            # Create learning plan with the correct data
            period_name = period.value.replace('_', ' ').title()
            learning_plan = LearningPlan(
                id=str(uuid.uuid4()),
                student_id=user.id,
                title=plan_dict.get("title", f"{subject} Learning Plan - {period_name}"),
                description=plan_dict.get("description", f"A {period_name} learning plan for {subject}"),
                subject=subject,
                topics=plan_dict.get("topics", [subject]),
                activities=activities,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                start_date=start_date,
                end_date=end_date,
                status=ActivityStatus.NOT_STARTED,
                progress_percentage=0.0,
                owner_id=current_user["id"]  # Set the owner_id to the current user
            )
            
            # Update metadata
            learning_plan.metadata = {
                "plan_type": "focused",
                "daily_minutes": daily_minutes,
                "student_profile_id": student_profile_id,
                "learning_period": period.value,
                "period_days": days
            }
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating profile-based learning plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating profile-based learning plan: {str(e)}"
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning plan not found"
            )
        
        # Return the plan
        return plan.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting learning plan: {str(e)}"
        )

@router.delete("/{plan_id}")
async def delete_learning_plan(
    plan_id: str = Path(..., description="Learning plan ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a learning plan.
    
    Args:
        plan_id: Learning plan ID
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        # Get learning plan service
        learning_plan_service = await get_learning_plan_service()
        
        # Check if plan exists and belongs to user
        plan = await learning_plan_service.get_learning_plan(
            plan_id=plan_id,
            user_id=current_user["id"]
        )
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning plan not found"
            )
        
        # Delete the learning plan
        success = await learning_plan_service.delete_learning_plan(
            plan_id=plan_id,
            user_id=current_user["id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete learning plan"
            )
        
        # Return success
        return {"message": "Learning plan deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting learning plan: {str(e)}"
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning plan not found"
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update learning plan"
            )
        
        # Return the updated plan
        return updated_plan.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating learning plan: {str(e)}"
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning plan not found"
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {format}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting learning plan: {str(e)}"
        )

@router.options("/{plan_id}/activities/{activity_id}")
async def options_activity_status(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID")
):
    """Handle OPTIONS preflight request for activity status updates."""
    return {"detail": "OK"}

@router.put("/{plan_id}/activities/{activity_id}", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def update_activity_status(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID"),
    activity_status: str = Body(..., embed=True, alias="status"),  # Renamed to avoid conflict
    completed_at: Optional[str] = Body(None, embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user)
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
        
        # Parse status
        try:
            parsed_status = ActivityStatus(activity_status)
        except ValueError:
            logger.warning(f"Invalid status provided: {activity_status}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {activity_status}. Must be one of: not_started, in_progress, completed"
            )
        
        # Parse completed_at date if provided
        completion_date = None
        if completed_at:
            try:
                completion_date = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid date format: {completed_at}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid completed_at date format: {completed_at}. Must be ISO format"
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Learning plan or activity not found"
                )
            
            # Ensure we return a valid JSON response
            return {
                "success": True,
                "message": "Activity status updated successfully",
                "plan_id": plan_id,
                "activity_id": activity_id,
                "status": activity_status,
                "progress_percentage": result.get("progress_percentage", 0.0),
                "plan_status": result.get("plan_status", "unknown")
            }
        except Exception as service_error:
            logger.error(f"Service error updating activity: {service_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error in learning plan service: {str(service_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unhandled error updating activity status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating activity status: {str(e)}"
        )