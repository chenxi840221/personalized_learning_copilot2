# backend/api/student_profile_routes.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Body
from typing import List, Dict, Any, Optional
import json
import logging
import traceback
import uuid
from datetime import datetime

from auth.entra_auth import get_current_user
from utils.student_profile_manager import get_student_profile_manager
from config.settings import Settings
from services.search_service import get_search_service

# Initialize settings
settings = Settings()

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/student-profiles", tags=["student-profiles"])

@router.post("/")
async def create_student_profile(
    profile_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a new student profile manually.
    
    Args:
        profile_data: Student profile data
        current_user: Current authenticated user
        
    Returns:
        Created student profile
    """
    logger.info(f"Create student profile request received for user: {current_user}")
    
    # Ensure the user is authorized
    if not current_user or not current_user.get("id"):
        logger.warning("User not authenticated or missing ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Get profile manager
        profile_manager = await get_student_profile_manager()
        
        # Validate profile data has required fields
        if not profile_data.get("full_name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="full_name is required for student profile"
            )
        
        # Add owner_id to profile data
        profile_data["owner_id"] = current_user["id"]
        
        # Get vector embedding for the profile
        try:
            from rag.openai_adapter import get_openai_adapter
            openai_client = await get_openai_adapter()
            
            # Prepare text for embedding
            text_parts = [
                f"Student Profile for: {profile_data.get('full_name', 'Unknown Student')}",
                f"Gender: {profile_data.get('gender', 'Unknown')}",
                f"Grade Level: {profile_data.get('grade_level', 'Unknown')}",
                f"Learning Style: {profile_data.get('learning_style', 'Unknown')}",
                f"School: {profile_data.get('school_name', 'Unknown')}",
            ]
            
            # Add strengths
            strengths = profile_data.get("strengths", [])
            if strengths:
                text_parts.append("Strengths:")
                for strength in strengths:
                    text_parts.append(f"- {strength}")
            
            # Add interests
            interests = profile_data.get("interests", [])
            if interests:
                text_parts.append("Interests:")
                for interest in interests:
                    text_parts.append(f"- {interest}")
            
            # Add areas for improvement
            areas_for_improvement = profile_data.get("areas_for_improvement", [])
            if areas_for_improvement:
                text_parts.append("Areas for Improvement:")
                for area in areas_for_improvement:
                    text_parts.append(f"- {area}")
            
            # Combine text parts
            text = "\n".join(text_parts)
            
            # Generate embedding
            embedding = await openai_client.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=text
            )
            
            if embedding:
                profile_data["embedding"] = embedding
        except Exception as embedding_err:
            logger.warning(f"Failed to generate embedding for profile: {embedding_err}")
        
        # Add timestamps
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        profile_data["created_at"] = now
        profile_data["updated_at"] = now
        profile_data["last_report_date"] = now
        
        # Generate a UUID for the profile
        profile_data["id"] = str(uuid.uuid4())
        
        # Create historical data
        if profile_data.get("current_school_year") and profile_data.get("current_term"):
            year_term_id = f"{profile_data['current_school_year']}-{profile_data['current_term']}"
            years_and_terms = [year_term_id]
            profile_data["years_and_terms"] = years_and_terms
            
            # Create current term data for historical records
            current_term_data = {
                "school_year": profile_data.get("current_school_year"),
                "term": profile_data.get("current_term"),
                "grade_level": profile_data.get("grade_level"),
                "learning_style": profile_data.get("learning_style"),
                "school_name": profile_data.get("school_name"),
                "teacher_name": profile_data.get("teacher_name"),
                "strengths": profile_data.get("strengths", []),
                "interests": profile_data.get("interests", []),
                "areas_for_improvement": profile_data.get("areas_for_improvement", []),
                "updated_at": now
            }
            
            # Create historical data JSON
            historical_data = {year_term_id: current_term_data}
            profile_data["historical_data"] = json.dumps(historical_data)
        
        # Get search service
        search_service = await get_search_service()
        
        # Check if search service is available
        if not search_service:
            logger.warning("Search service not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service is currently unavailable. Please try again later."
            )
        
        # Index the profile
        success = await search_service.index_document(
            index_name="student-profiles",
            document=profile_data
        )
        
        if not success:
            logger.error("Failed to index student profile")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create student profile"
            )
        
        # Return the created profile
        return {
            "message": "Student profile created successfully",
            "profile": profile_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating student profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating student profile: {str(e)}"
        )

@router.get("/")
async def get_student_profiles(
    current_user: Dict = Depends(get_current_user),
    name_filter: Optional[str] = Query(None, description="Filter profiles by name"),
    school_year: Optional[str] = Query(None, description="Filter by school year"),
    term: Optional[str] = Query(None, description="Filter by term"),
    limit: int = Query(50, description="Maximum number of profiles to return"),
    skip: int = Query(0, description="Number of profiles to skip")
):
    """Get all student profiles."""
    logger.info(f"Get student profiles request received for user: {current_user}")
    
    # Ensure the user is authorized
    if not current_user or not current_user.get("id"):
        logger.warning("User not authenticated or missing ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Get search service
        search_service = await get_search_service()
        
        # Check if search service is available
        if not search_service:
            logger.warning("Search service not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service is currently unavailable. Please try again later."
            )
        
        # Build filter parts - restrict to profiles owned by this user
        filter_parts = [f"owner_id eq '{current_user['id']}'"]
        
        # Add name filter if provided
        if name_filter:
            # Use contains instead of eq for partial name match
            filter_parts.append(f"search.ismatchscoring('{name_filter}', 'full_name')")
        
        # Add school year filter if provided
        if school_year:
            # Filter by either current school year or any year in the years_and_terms collection
            year_term_conditions = [f"current_school_year eq '{school_year}'"]
            
            # Also check for year in the years_and_terms collection
            if term:
                year_term_id = f"{school_year}-{term}"
                year_term_conditions.append(f"years_and_terms/any(y: y eq '{year_term_id}')")
            else:
                # If no term specified, match any term for the given year
                year_term_conditions.append(f"years_and_terms/any(y: y ge '{school_year}-' and y lt '{int(school_year)+1}-')")
                
            filter_parts.append(f"({' or '.join(year_term_conditions)})")
        
        # Add term filter if provided (only if school_year is not provided, as it's handled above)
        elif term:
            filter_parts.append(f"current_term eq '{term}'")
        
        # Combine filter parts
        filter_expression = " and ".join(filter_parts) if filter_parts else None
        
        # Search for profiles
        logger.info(f"Searching for profiles with filter: {filter_expression}")
        profiles = await search_service.search_documents(
            index_name="student-profiles",
            query="*",
            filter=filter_expression,
            top=limit,
            skip=skip
        )
        
        if not profiles:
            logger.info("No profiles found")
            return []
        
        # Process each profile to extract current term data
        for profile in profiles:
            if "historical_data" in profile and profile["historical_data"]:
                try:
                    # Parse historical data
                    historical_data = json.loads(profile["historical_data"])
                    
                    # Add current term details if available
                    current_year = profile.get("current_school_year")
                    current_term = profile.get("current_term")
                    
                    if current_year and current_term:
                        year_term_id = f"{current_year}-{current_term}"
                        
                        if year_term_id in historical_data:
                            # Add current term data to the profile for easier access
                            profile["current_term_data"] = historical_data[year_term_id]
                    
                    # Remove large historical_data field from response to reduce payload size
                    profile.pop("historical_data", None)
                    
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse historical data for profile {profile.get('id')}")
            
            # Remove embedding from response
            profile.pop("embedding", None)
        
        return profiles
    
    except Exception as e:
        logger.exception(f"Error getting student profiles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting student profiles: {str(e)}"
        )

@router.get("/{profile_id}")
async def get_student_profile(
    profile_id: str = Path(..., description="Profile ID"),
    current_user: Dict = Depends(get_current_user),
    school_year: Optional[str] = Query(None, description="Filter history by school year"),
    term: Optional[str] = Query(None, description="Filter history by term")
):
    """Get a specific student profile with optional term/year filtering."""
    logger.info(f"Get student profile request for ID: {profile_id}")
    
    # Ensure the user is authorized
    if not current_user or not current_user.get("id"):
        logger.warning("User not authenticated or missing ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Get search service
        search_service = await get_search_service()
        
        # Check if search service is available
        if not search_service:
            logger.warning("Search service not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service is currently unavailable. Please try again later."
            )
        
        # Get the profile by ID and ensure it belongs to the current user
        filter_expression = f"id eq '{profile_id}' and owner_id eq '{current_user['id']}'"
        profiles = await search_service.search_documents(
            index_name="student-profiles",
            query="*",
            filter=filter_expression,
            top=1
        )
        
        if not profiles:
            logger.warning(f"Profile not found for ID: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found"
            )
        
        profile = profiles[0]
        
        # Process historical data if available
        if "historical_data" in profile and profile["historical_data"]:
            try:
                # Parse historical data
                historical_data = json.loads(profile["historical_data"])
                
                # Filter by school year and term if provided
                if school_year and term:
                    year_term_id = f"{school_year}-{term}"
                    filtered_data = {k: v for k, v in historical_data.items() if k == year_term_id}
                    profile["historical_data_filtered"] = filtered_data
                elif school_year:
                    # Filter by school year only
                    filtered_data = {k: v for k, v in historical_data.items() 
                                    if k.startswith(f"{school_year}-")}
                    profile["historical_data_filtered"] = filtered_data
                elif term:
                    # Filter by term only
                    filtered_data = {k: v for k, v in historical_data.items() 
                                    if k.endswith(f"-{term}")}
                    profile["historical_data_filtered"] = filtered_data
                else:
                    # No filters, return all historical data
                    profile["historical_data_filtered"] = historical_data
                
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse historical data for profile {profile_id}")
                profile["historical_data_filtered"] = {}
        
        # Remove embedding from response
        profile.pop("embedding", None)
        
        return profile
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting student profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting student profile: {str(e)}"
        )

@router.put("/{profile_id}")
async def update_student_profile(
    profile_id: str = Path(..., description="Profile ID"),
    profile_data: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_current_user)
):
    """
    Update an existing student profile.
    
    Args:
        profile_id: ID of the profile to update
        profile_data: Updated profile data
        current_user: Current authenticated user
        
    Returns:
        Updated student profile
    """
    logger.info(f"Update student profile request for ID: {profile_id}")
    
    # Ensure the user is authorized
    if not current_user or not current_user.get("id"):
        logger.warning("User not authenticated or missing ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Get search service
        search_service = await get_search_service()
        
        # Check if search service is available
        if not search_service:
            logger.warning("Search service not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service is currently unavailable. Please try again later."
            )
        
        # Check if the profile exists and belongs to the current user
        filter_expression = f"id eq '{profile_id}' and owner_id eq '{current_user['id']}'"
        profiles = await search_service.search_documents(
            index_name="student-profiles",
            query="*",
            filter=filter_expression,
            top=1
        )
        
        if not profiles:
            logger.warning(f"Profile not found for ID: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found"
            )
        
        existing_profile = profiles[0]
        
        # Preserve fields that should not be changed directly
        profile_data["id"] = profile_id
        profile_data["owner_id"] = current_user["id"]
        profile_data["created_at"] = existing_profile.get("created_at")
        
        # Update timestamp
        profile_data["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Ensure historical data is preserved
        if existing_profile.get("historical_data") and "historical_data" not in profile_data:
            profile_data["historical_data"] = existing_profile["historical_data"]
            
        # Update years_and_terms if needed
        if existing_profile.get("years_and_terms") and "years_and_terms" not in profile_data:
            profile_data["years_and_terms"] = existing_profile["years_and_terms"]
            
        # Check if current_school_year and current_term have changed
        if (profile_data.get("current_school_year") != existing_profile.get("current_school_year") or
            profile_data.get("current_term") != existing_profile.get("current_term")):
            
            # Create or update historical data
            historical_data = {}
            if existing_profile.get("historical_data"):
                try:
                    historical_data = json.loads(existing_profile["historical_data"])
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Create a new entry for the current term
            if profile_data.get("current_school_year") and profile_data.get("current_term"):
                year_term_id = f"{profile_data['current_school_year']}-{profile_data['current_term']}"
                
                # Add to years_and_terms list
                years_and_terms = profile_data.get("years_and_terms", [])
                if year_term_id not in years_and_terms:
                    years_and_terms.append(year_term_id)
                    profile_data["years_and_terms"] = years_and_terms
                
                # Create term data
                current_term_data = {
                    "school_year": profile_data.get("current_school_year"),
                    "term": profile_data.get("current_term"),
                    "grade_level": profile_data.get("grade_level"),
                    "learning_style": profile_data.get("learning_style"),
                    "school_name": profile_data.get("school_name"),
                    "teacher_name": profile_data.get("teacher_name"),
                    "strengths": profile_data.get("strengths", []),
                    "interests": profile_data.get("interests", []),
                    "areas_for_improvement": profile_data.get("areas_for_improvement", []),
                    "updated_at": profile_data["updated_at"]
                }
                
                # Add to historical data
                historical_data[year_term_id] = current_term_data
                profile_data["historical_data"] = json.dumps(historical_data)
        
        # Update vector embedding for the profile
        try:
            from rag.openai_adapter import get_openai_adapter
            openai_client = await get_openai_adapter()
            
            # Prepare text for embedding
            text_parts = [
                f"Student Profile for: {profile_data.get('full_name', 'Unknown Student')}",
                f"Gender: {profile_data.get('gender', 'Unknown')}",
                f"Grade Level: {profile_data.get('grade_level', 'Unknown')}",
                f"Learning Style: {profile_data.get('learning_style', 'Unknown')}",
                f"School: {profile_data.get('school_name', 'Unknown')}",
            ]
            
            # Add strengths
            strengths = profile_data.get("strengths", [])
            if strengths:
                text_parts.append("Strengths:")
                for strength in strengths:
                    text_parts.append(f"- {strength}")
            
            # Add interests
            interests = profile_data.get("interests", [])
            if interests:
                text_parts.append("Interests:")
                for interest in interests:
                    text_parts.append(f"- {interest}")
            
            # Add areas for improvement
            areas_for_improvement = profile_data.get("areas_for_improvement", [])
            if areas_for_improvement:
                text_parts.append("Areas for Improvement:")
                for area in areas_for_improvement:
                    text_parts.append(f"- {area}")
            
            # Combine text parts
            text = "\n".join(text_parts)
            
            # Generate embedding
            embedding = await openai_client.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=text
            )
            
            if embedding:
                profile_data["embedding"] = embedding
        except Exception as embedding_err:
            logger.warning(f"Failed to generate embedding for profile: {embedding_err}")
            
            # Keep existing embedding if available
            if existing_profile.get("embedding"):
                profile_data["embedding"] = existing_profile["embedding"]
        
        # Update the profile
        success = await search_service.index_document(
            index_name="student-profiles",
            document=profile_data
        )
        
        if not success:
            logger.error(f"Failed to update profile with ID: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update student profile"
            )
        
        return {
            "message": "Student profile updated successfully",
            "profile": profile_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating student profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating student profile: {str(e)}"
        )

@router.delete("/{profile_id}")
async def delete_student_profile(
    profile_id: str = Path(..., description="Profile ID"),
    current_user: Dict = Depends(get_current_user)
):
    """Delete a student profile."""
    logger.info(f"Delete student profile request for ID: {profile_id}")
    
    # Ensure the user is authorized
    if not current_user or not current_user.get("id"):
        logger.warning("User not authenticated or missing ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Get search service
        search_service = await get_search_service()
        
        # Check if search service is available
        if not search_service:
            logger.warning("Search service not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service is currently unavailable. Please try again later."
            )
        
        # Check if the profile exists and belongs to the current user
        filter_expression = f"id eq '{profile_id}' and owner_id eq '{current_user['id']}'"
        profiles = await search_service.search_documents(
            index_name="student-profiles",
            query="*",
            filter=filter_expression,
            top=1
        )
        
        if not profiles:
            logger.warning(f"Profile not found for ID: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found"
            )
        
        # Delete the profile
        success = await search_service.delete_document(
            index_name="student-profiles",
            document_id=profile_id
        )
        
        if not success:
            logger.error(f"Failed to delete profile with ID: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete student profile"
            )
        
        return {"message": f"Profile with ID {profile_id} successfully deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting student profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting student profile: {str(e)}"
        )

@router.get("/history/{profile_id}")
async def get_student_profile_history(
    profile_id: str = Path(..., description="Profile ID"),
    current_user: Dict = Depends(get_current_user)
):
    """Get the complete history for a student profile."""
    logger.info(f"Get student profile history request for ID: {profile_id}")
    
    # Ensure the user is authorized
    if not current_user or not current_user.get("id"):
        logger.warning("User not authenticated or missing ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Get search service
        search_service = await get_search_service()
        
        # Check if search service is available
        if not search_service:
            logger.warning("Search service not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search service is currently unavailable. Please try again later."
            )
        
        # Get the profile by ID and ensure it belongs to the current user
        filter_expression = f"id eq '{profile_id}' and owner_id eq '{current_user['id']}'"
        profiles = await search_service.search_documents(
            index_name="student-profiles",
            query="*",
            filter=filter_expression,
            top=1
        )
        
        if not profiles:
            logger.warning(f"Profile not found for ID: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile with ID {profile_id} not found"
            )
        
        profile = profiles[0]
        
        # Process historical data
        if "historical_data" in profile and profile["historical_data"]:
            try:
                # Parse historical data
                historical_data = json.loads(profile["historical_data"])
                
                # Convert to list for easier frontend processing
                history_list = []
                for year_term_id, term_data in historical_data.items():
                    # Add the year_term_id to the data for reference
                    term_data["year_term_id"] = year_term_id
                    history_list.append(term_data)
                
                # Sort by school year and term
                history_list.sort(key=lambda x: (x.get("school_year", ""), x.get("term", "")))
                
                return {
                    "profile_id": profile_id,
                    "full_name": profile.get("full_name"),
                    "history": history_list
                }
                
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse historical data for profile {profile_id}")
                return {
                    "profile_id": profile_id,
                    "full_name": profile.get("full_name"),
                    "history": []
                }
        
        # No historical data
        return {
            "profile_id": profile_id,
            "full_name": profile.get("full_name"),
            "history": []
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting student profile history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting student profile history: {str(e)}"
        )

# Include router in app
student_profile_router = router