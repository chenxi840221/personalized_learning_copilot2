# api/endpoints.py
from fastapi import Depends, HTTPException, Query, Path, Body, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import httpx
import json
import logging

from models.user import User
from models.content import Content, ContentType
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from auth.authentication import get_current_user
from services.search_service import get_search_service, SearchService, AzureSearchService
from rag.openai_adapter import get_openai_adapter
from rag.generator import get_plan_generator
from config.settings import Settings

# Initialize settings
settings = Settings()

# Setup logging
logger = logging.getLogger(__name__)

# User endpoints
async def get_user_endpoint(current_user: Dict = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    search_service = await get_search_service()
    
    # Get user from search index
    user = await search_service.get_user(current_user["id"])
    
    if not user:
        # Create user if it doesn't exist in our system
        user_data = {
            "id": current_user["id"],
            "ms_object_id": current_user["id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "full_name": current_user.get("full_name", ""),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        user = await search_service.create_user(user_data)
        
    return user

async def update_user_profile_endpoint(
    profile_data: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_current_user)
):
    """Update the user profile in Azure AI Search."""
    search_service = await get_search_service()
    
    # Get existing user
    user = await search_service.get_user(current_user["id"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    # Update fields
    user.update({
        "full_name": profile_data.get("full_name", user.get("full_name")),
        "grade_level": profile_data.get("grade_level", user.get("grade_level")),
        "subjects_of_interest": profile_data.get("subjects_of_interest", user.get("subjects_of_interest", [])),
        "learning_style": profile_data.get("learning_style", user.get("learning_style")),
        "updated_at": datetime.utcnow().isoformat()
    })
    
    # Generate embedding for user profile
    profile_text = f"User {user['username']} is in grade {user.get('grade_level')} with interests in {', '.join(user.get('subjects_of_interest', []))}. Learning style: {user.get('learning_style')}"
    embedding = await search_service.openai_adapter.create_embedding(
        model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        text=profile_text
    )
    
    # Add embedding to user data
    user["embedding"] = embedding
    
    # Save updated user
    result = await search_service.users_index_client.upload_documents(documents=[user])
    
    if not result[0].succeeded:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )
    
    return user

# Content endpoints
async def get_content_endpoint(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    grade_level: Optional[int] = Query(None, description="Filter by grade level"),
    page: int = Query(1, description="Page number for pagination"),
    limit: int = Query(100, description="Number of items per page")
    # Remove authentication for now
    # current_user: Dict = Depends(get_current_user)
):
    """Get content with optional filters."""
    try:
        search_service = await get_search_service()
        
        # Build filter expression
        filter_parts = []
        if subject:
            # Check for subject aliases that might be in the database differently
            if subject == "Math" or subject == "Mathematics":
                # Try all variations of Mathematics subject
                filter_parts.append("(subject eq 'Math' or subject eq 'Mathematics' or subject eq 'Maths')")
            elif subject == "Maths":
                # This is the actual name in the Azure Search index
                filter_parts.append("subject eq 'Maths'")
            else:
                filter_parts.append(f"subject eq '{subject}'")
        
        if content_type:
            filter_parts.append(f"content_type eq '{content_type.lower()}'")
        if difficulty:
            filter_parts.append(f"difficulty_level eq '{difficulty.lower()}'")
        if grade_level:
            filter_parts.append(f"grade_level/any(g: g eq {grade_level})")
        
        filter_expression = " and ".join(filter_parts) if filter_parts else None
        
        # Add debugging for the filter expression
        logger.info(f"Using filter expression: {filter_expression}")
        
        # Use the search_documents method which is available on SearchService
        content_index_name = settings.CONTENT_INDEX_NAME or "educational-content"
        
        # First, search more broadly without subject filter to see what we have
        if subject in ["Mathematics", "Math", "Maths", "History"] and filter_parts:
            # Log all available subjects for debugging
            all_content = await search_service.search_documents(
                index_name=content_index_name,
                query="*",
                top=100,
                select="subject"
            )
            
            subjects_in_index = set()
            for item in all_content:
                if "subject" in item:
                    subjects_in_index.add(item["subject"])
            
            logger.info(f"Available subjects in index: {subjects_in_index}")
        
        # Calculate skip value for pagination (0-indexed)
        skip_value = (page - 1) * limit
        logger.info(f"Pagination: page={page}, limit={limit}, skip={skip_value}")
        
        # When no subject is provided, use a more direct approach to get all content
        if not subject:
            logger.info("No subject filter, getting all content directly")
            
            # For pagination without subject filter, use direct query with skip/limit
            contents = await search_service.search_documents(
                index_name=content_index_name,
                query="*",
                filter=None,  # No filter means get everything
                top=limit, 
                skip=skip_value,
                select="id,title,description,subject,content_type,difficulty_level,grade_level,topics,url,duration_minutes,keywords,source"
            )
            
            logger.info(f"Direct pagination: fetched page {page} with {len(contents)} items")
        else:
            # For subject-specific search, we can paginate directly via the Azure Search API
            contents = await search_service.search_documents(
                index_name=content_index_name,
                query="*",
                filter=filter_expression,
                top=limit,
                skip=skip_value,
                select="id,title,description,subject,content_type,difficulty_level,grade_level,topics,url,duration_minutes,keywords,source"
            )
        
        if not contents:
            # Log the empty result situation with details
            logger.info(f"No content found with filters: {filter_expression}")
            
            # Return empty list with HTTP 200
            return []
        
        logger.info(f"Found {len(contents)} content items with filters: {filter_expression}")
        return contents
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving content: {str(e)}"
        )

# Mock content functions removed as they're no longer needed

async def get_content_by_id_endpoint(
    content_id: str = Path(..., description="Content ID")
    # Remove authentication for now
    # current_user: Dict = Depends(get_current_user)
):
    """Get content by ID."""
    try:
        # Get the search service
        search_service = await get_search_service()
        
        # Use filter search to get the content by ID
        content_index_name = settings.CONTENT_INDEX_NAME or "educational-content"
        filter_expression = f"id eq '{content_id}'"
        
        # Log the filter being used
        logger.info(f"Searching for content with filter: {filter_expression}")
        
        # Specify explicit fields to ensure consistency in results
        results = await search_service.search_documents(
            index_name=content_index_name,
            query="*",
            filter=filter_expression,
            top=1,
            select="id,title,description,subject,content_type,difficulty_level,grade_level,topics,url,duration_minutes,keywords,source"
        )
        
        if not results or len(results) == 0:
            logger.warning(f"Content with ID {content_id} not found in Azure Search")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content with ID {content_id} not found"
            )
        
        logger.info(f"Retrieved content item from Azure Search with ID {content_id}")
        return results[0]
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving content by ID: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving content: {str(e)}"
        )

async def get_recommendations_endpoint(
    subject: Optional[str] = Query(None, description="Optional subject filter"),
    page: int = Query(1, description="Page number for pagination"),
    limit: int = Query(100, description="Number of items per page")
    # Remove authentication for now
    # current_user: Dict = Depends(get_current_user)
):
    """Get personalized content recommendations."""
    try:
        search_service = await get_search_service()
        
        # Build filter expression
        filter_parts = []
        
        if subject:
            # Check for subject aliases that might be in the database differently
            if subject == "Math" or subject == "Mathematics":
                # Try all variations of Mathematics subject
                filter_parts.append("(subject eq 'Math' or subject eq 'Mathematics' or subject eq 'Maths')")
            elif subject == "Maths":
                # This is the actual name in the Azure Search index
                filter_parts.append("subject eq 'Maths'")
            else:
                filter_parts.append(f"subject eq '{subject}'")
        
        filter_expression = " and ".join(filter_parts) if filter_parts else None
        
        # Add debugging for the filter expression
        logger.info(f"Recommendations using filter expression: {filter_expression}")
        
        # If debugging Math or History subject issues
        if subject in ["Mathematics", "Math", "Maths", "History"] and filter_parts:
            # Log all available subjects for debugging
            content_index_name = settings.CONTENT_INDEX_NAME or "educational-content"
            all_content = await search_service.search_documents(
                index_name=content_index_name,
                query="*",
                top=100,
                select="subject"
            )
            
            subjects_in_index = set()
            for item in all_content:
                if "subject" in item:
                    subjects_in_index.add(item["subject"])
            
            logger.info(f"Available subjects in index for recommendations: {subjects_in_index}")
        
        # For now, instead of personalized recommendations, just return general content
        # Use the search_documents method which is available on SearchService
        content_index_name = settings.CONTENT_INDEX_NAME or "educational-content"
        
        # Calculate skip value for pagination (0-indexed)
        skip_value = (page - 1) * limit
        logger.info(f"Recommendations pagination: page={page}, limit={limit}, skip={skip_value}")
        
        # When no subject is provided, we want to return a balanced mix of content from all subjects
        if not subject:
            logger.info("No subject specified for recommendations, getting content from all subjects")
            
            # Get all available subjects first
            all_subjects = await search_service.search_documents(
                index_name=content_index_name,
                query="*",
                top=100,
                select="subject"
            )
            
            # Extract unique subjects
            unique_subjects = set()
            for item in all_subjects:
                if "subject" in item and item["subject"]:
                    unique_subjects.add(item["subject"])
            
            logger.info(f"Found {len(unique_subjects)} unique subjects: {unique_subjects}")
            
            # Get more items from each subject for pagination support
            items_per_subject = 1000  # Significantly increased to show all available content
            all_recommendations = []
            
            for subj in unique_subjects:
                subj_filter = f"subject eq '{subj}'"
                subject_content = await search_service.search_documents(
                    index_name=content_index_name,
                    query="*",
                    filter=subj_filter,
                    top=items_per_subject, 
                    select="id,title,description,subject,content_type,difficulty_level,grade_level,topics,url,duration_minutes,keywords,source"
                )
                
                if subject_content:
                    logger.info(f"Adding {len(subject_content)} items from subject '{subj}'")
                    all_recommendations.extend(subject_content)
            
            # Shuffle the recommendations with a fixed seed for consistent ordering
            import random
            random_gen = random.Random(42)  # Use fixed seed for consistent shuffling
            random_gen.shuffle(all_recommendations)
            
            # Get total count for pagination info
            total_count = len(all_recommendations)
            
            # Get the page of results
            start_idx = min(skip_value, total_count)
            end_idx = min(start_idx + limit, total_count)
            
            recommendations = all_recommendations[start_idx:end_idx]
            logger.info(f"Recommendations paginated results: {start_idx+1}-{end_idx} of {total_count} total items")
        else:
            # Normal filter-based search for specified subject with pagination
            recommendations = await search_service.search_documents(
                index_name=content_index_name,
                query="*",
                filter=filter_expression,
                top=limit,
                skip=skip_value,
                select="id,title,description,subject,content_type,difficulty_level,grade_level,topics,url,duration_minutes,keywords,source"
            )
        
        if not recommendations:
            # Log the empty result situation with details
            logger.info(f"No recommendations found with filters: {filter_expression}")
            
            # Return empty list with HTTP 200
            return []
        
        logger.info(f"Found {len(recommendations)} recommendation items for subject: {subject}")
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting recommendations: {str(e)}"
        )

async def search_content_endpoint(
    query: str = Query(..., description="Search query"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    content_type: Optional[str] = Query(None, description="Filter by content type", alias="content_type"),
    page: int = Query(1, description="Page number for pagination"),
    limit: int = Query(100, description="Number of items per page")
    # Remove authentication for now
    # current_user: Dict = Depends(get_current_user)
):
    """Search for content using text search."""
    try:
        search_service = await get_search_service()
        
        # Build filter expression
        filter_parts = []
        if subject:
            # Check for subject aliases that might be in the database differently
            if subject == "Math" or subject == "Mathematics":
                # Try all variations of Mathematics subject
                filter_parts.append("(subject eq 'Math' or subject eq 'Mathematics' or subject eq 'Maths')")
            elif subject == "Maths":
                # This is the actual name in the Azure Search index
                filter_parts.append("subject eq 'Maths'")
            else:
                filter_parts.append(f"subject eq '{subject}'")
                
        if content_type:
            filter_parts.append(f"content_type eq '{content_type.lower()}'")
        
        filter_expression = " and ".join(filter_parts) if filter_parts else None
        
        # Add debugging for the filter expression
        logger.info(f"Search using filter expression: {filter_expression}, query: {query}")
        
        # Use the search_documents method which is available on SearchService
        content_index_name = settings.CONTENT_INDEX_NAME or "educational-content"
        
        # For Math and History, try additional approaches if needed
        if subject in ["Mathematics", "Math", "Maths", "History"]:
            # First try a more aggressive search with looser filters
            logger.info(f"Using broader search for {subject} with query: {query}")
            
            # Determine actual subject name for expansive search
            search_subject_name = subject
            if subject in ["Mathematics", "Math"]:
                search_subject_name = "Maths"  # Use the name stored in Azure AI Search
            
            # Try a more expansive search query by including the subject name in the query
            expanded_query = f"{query} {search_subject_name}"
            
            contents = await search_service.search_documents(
                index_name=content_index_name,
                query=expanded_query,
                filter=None,  # Remove filter for this search to get more results
                top=20,
                select="id,title,description,subject,content_type,difficulty_level,grade_level,topics,url,duration_minutes,keywords,source"
            )
            
            if contents and len(contents) > 0:
                logger.info(f"Found {len(contents)} results using broader search approach")
                # Filter the results programmatically to match the subject
                filtered_contents = [
                    item for item in contents
                    if item.get("subject") == subject or 
                    (subject in ["Math", "Mathematics"] and item.get("subject") == "Maths") or
                    (subject == "Maths" and item.get("subject") in ["Math", "Mathematics"])
                ]
                
                if filtered_contents:
                    logger.info(f"Returning {len(filtered_contents)} filtered results from broader search")
                    return filtered_contents
        
        # Standard search if the above didn't work or for other subjects
        # Calculate skip value for pagination
        skip_value = (page - 1) * limit
        logger.info(f"Search pagination: page={page}, limit={limit}, skip={skip_value}")
        
        contents = await search_service.search_documents(
            index_name=content_index_name,
            query=query,
            filter=filter_expression,
            top=limit,
            skip=skip_value,
            select="id,title,description,subject,content_type,difficulty_level,grade_level,topics,url,duration_minutes,keywords,source"
        )
        
        if not contents:
            # Log the empty result situation with details
            logger.info(f"No search results found for query: {query}, filters: {filter_expression}")
            
            # Return empty list with HTTP 200
            return []
        
        logger.info(f"Found {len(contents)} search results for query: {query}")
        return contents
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching content: {str(e)}"
        )

# Learning plan endpoints
async def get_learning_plans_endpoint(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    current_user: Dict = Depends(get_current_user)
):
    """Get all learning plans for the current user."""
    search_service = await get_search_service()
    
    try:
        # Build filter expression
        filter_expression = f"student_id eq '{current_user['id']}'"
        if subject:
            filter_expression += f" and subject eq '{subject}'"
        
        # Execute search
        results = await search_service.plans_index_client.search(
            search_text="*",
            filter=filter_expression,
            order_by=["created_at desc"],
            include_total_count=True
        )
        
        # Convert results to list
        plans = []
        async for result in results:
            plans.append(dict(result))
        
        return plans
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting learning plans: {str(e)}"
        )

async def create_learning_plan_endpoint(
    subject: str = Body(..., embed=True),
    current_user: Dict = Depends(get_current_user)
):
    """Create a new personalized learning plan."""
    search_service = await get_search_service()
    openai_adapter = await get_openai_adapter()
    
    try:
        # Get user profile
        user = await search_service.get_user(current_user["id"])
        
        # Generate query for content
        query_text = f"Educational content for {subject} appropriate for a student in grade {user.get('grade_level', 'any')} "
        
        if user.get("learning_style"):
            query_text += f"with {user.get('learning_style')} learning style. "
        
        if user.get("subjects_of_interest"):
            interests = ", ".join(user.get("subjects_of_interest"))
            query_text += f"Interested in {interests}."
        
        # Generate embedding for query
        embedding = await openai_adapter.create_embedding(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            text=query_text
        )
        
        # Get relevant content using vector search
        filter_expression = f"subject eq '{subject}'"
        if user.get("grade_level"):
            grade = user.get("grade_level")
            grade_filters = [
                f"grade_level/any(g: g eq {grade})",
                f"grade_level/any(g: g eq {grade - 1})",
                f"grade_level/any(g: g eq {grade + 1})"
            ]
            filter_expression += f" and ({' or '.join(grade_filters)})"
        
        results = await search_service.content_index_client.search(
            search_text=None,
            vectors=[{"value": embedding, "fields": "embedding", "k": 15}],
            filter=filter_expression,
            select=["id", "title", "description", "subject", "content_type", 
                    "difficulty_level", "url", "duration_minutes"],
            top=15
        )
        
        # Extract content items
        content_items = []
        async for result in results:
            content_items.append(dict(result))
        
        # Get plan generator
        plan_generator = await get_plan_generator()
        
        # Generate learning plan
        plan_dict = await plan_generator.generate_plan(
            student=user,
            subject=subject,
            relevant_content=content_items
        )
        
        # Add metadata
        plan_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        plan_dict["id"] = plan_id
        plan_dict["student_id"] = current_user["id"]
        plan_dict["created_at"] = now
        plan_dict["updated_at"] = now
        plan_dict["start_date"] = now
        plan_dict["end_date"] = now  # Would be calculated based on activities
        plan_dict["status"] = "not_started"
        plan_dict["progress_percentage"] = 0.0
        
        # Generate embedding for plan
        plan_text = f"{plan_dict['title']} {plan_dict['description']} for {plan_dict['subject']}"
        plan_embedding = await openai_adapter.create_embedding(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            text=plan_text
        )
        plan_dict["embedding"] = plan_embedding
        
        # Save to Azure AI Search
        result = await search_service.plans_index_client.upload_documents(documents=[plan_dict])
        
        if not result[0].succeeded:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save learning plan"
            )
        
        return plan_dict
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating learning plan: {str(e)}"
        )

async def get_learning_plan_endpoint(
    plan_id: str = Path(..., description="Learning plan ID"),
    current_user: Dict = Depends(get_current_user)
):
    """Get a specific learning plan."""
    search_service = await get_search_service()
    
    try:
        # Get plan from index
        plan = await search_service.plans_index_client.get_document(key=plan_id)
        
        # Check ownership
        if plan.get("student_id") != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this plan"
            )
        
        return dict(plan)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning plan not found"
        )

async def update_activity_status_endpoint(
    plan_id: str = Path(..., description="Learning plan ID"),
    activity_id: str = Path(..., description="Activity ID"),
    status: str = Body(..., embed=True),
    completed_at: Optional[str] = Body(None, embed=True),
    current_user: Dict = Depends(get_current_user)
):
    """Update the status of a learning activity."""
    search_service = await get_search_service()
    
    try:
        # Get plan from index
        plan = await search_service.plans_index_client.get_document(key=plan_id)
        
        # Check ownership
        if plan.get("student_id") != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this plan"
            )
        
        # Find and update activity
        activities = plan.get("activities", [])
        activity_found = False
        
        for i, activity in enumerate(activities):
            if activity.get("id") == activity_id:
                activities[i]["status"] = status
                if status == "completed":
                    activities[i]["completed_at"] = completed_at or datetime.utcnow().isoformat()
                activity_found = True
                break
        
        if not activity_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activity not found in learning plan"
            )
        
        # Calculate progress percentage
        total_activities = len(activities)
        completed_activities = sum(1 for a in activities if a.get("status") == "completed")
        progress_percentage = (completed_activities / total_activities) * 100 if total_activities > 0 else 0
        
        # Determine plan status
        plan_status = "not_started"
        if completed_activities == total_activities:
            plan_status = "completed"
        elif completed_activities > 0:
            plan_status = "in_progress"
        
        # Update plan
        plan["activities"] = activities
        plan["progress_percentage"] = progress_percentage
        plan["status"] = plan_status
        plan["updated_at"] = datetime.utcnow().isoformat()
        
        # Save updated plan
        result = await search_service.plans_index_client.upload_documents(documents=[plan])
        
        if not result[0].succeeded:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update activity status"
            )
        
        return {
            "success": True,
            "message": "Activity status updated",
            "progress_percentage": progress_percentage,
            "plan_status": plan_status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating activity status: {str(e)}"
        )

# Admin endpoints
async def trigger_scraper_endpoint(
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Manually trigger the content scraper.
    Available only to admin users.
    """
    # Check if user is admin (would be in roles from Entra ID token)
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can trigger the scraper"
        )
    
    # Run scraper in background
    from scrapers.abc_edu_scraper import run_scraper
    background_tasks.add_task(run_scraper)
    
    return {"message": "Content scraper started in background"}

async def get_content_stats_endpoint(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get statistics about the content database.
    Available only to admin users.
    """
    # Check if user is admin
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can access content statistics"
        )
    
    search_service = await get_search_service()
    
    try:
        # Get subject counts
        subject_counts = {}
        for subject in ["Mathematics", "Science", "English", "History", "Geography", "Arts"]:
            result = await search_service.content_index_client.search(
                search_text="*",
                filter=f"subject eq '{subject}'",
                include_total_count=True,
                top=0
            )
            subject_counts[subject] = result.get_count()
        
        # Get content type counts
        content_type_counts = {}
        for content_type in ["article", "video", "interactive", "quiz", "worksheet", "lesson", "activity"]:
            result = await search_service.content_index_client.search(
                search_text="*",
                filter=f"content_type eq '{content_type}'",
                include_total_count=True,
                top=0
            )
            content_type_counts[content_type] = result.get_count()
        
        # Get total count
        total_result = await search_service.content_index_client.search(
            search_text="*",
            include_total_count=True,
            top=0
        )
        total_count = total_result.get_count()
        
        # Get last updated date
        latest_result = await search_service.content_index_client.search(
            search_text="*",
            order_by=["updated_at desc"],
            select=["updated_at"],
            top=1
        )
        
        latest_date = None
        async for item in latest_result:
            latest_date = item.get("updated_at")
            break
        
        return {
            "total_count": total_count,
            "subject_counts": subject_counts,
            "content_type_counts": content_type_counts,
            "last_updated": latest_date
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving content statistics: {str(e)}"
        )

async def get_student_progress_endpoint(
    current_user: Dict = Depends(get_current_user)
):
    """Get student progress analytics."""
    search_service = await get_search_service()
    
    try:
        # Get all user's learning plans
        results = await search_service.plans_index_client.search(
            search_text="*",
            filter=f"student_id eq '{current_user['id']}'",
            include_total_count=True
        )
        
        # Extract plans
        plans = []
        async for result in results:
            plans.append(dict(result))
        
        # Calculate overall stats
        total_plans = len(plans)
        completed_plans = sum(1 for p in plans if p.get("status") == "completed")
        in_progress_plans = sum(1 for p in plans if p.get("status") == "in_progress")
        overall_completion = (completed_plans / total_plans) * 100 if total_plans > 0 else 0
        
        # Get subject-specific progress
        subjects = {}
        for plan in plans:
            subject = plan.get("subject")
            if subject not in subjects:
                subjects[subject] = {
                    "total": 0,
                    "completed": 0,
                    "in_progress": 0,
                    "percentage": 0
                }
            
            subjects[subject]["total"] += 1
            
            if plan.get("status") == "completed":
                subjects[subject]["completed"] += 1
            elif plan.get("status") == "in_progress":
                subjects[subject]["in_progress"] += 1
        
        # Calculate percentages for each subject
        for subject, stats in subjects.items():
            if stats["total"] > 0:
                stats["percentage"] = (stats["completed"] / stats["total"]) * 100
        
        return {
            "total_plans": total_plans,
            "completed_plans": completed_plans,
            "in_progress_plans": in_progress_plans,
            "overall_completion": overall_completion,
            "subjects": subjects
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving progress: {str(e)}"
        )