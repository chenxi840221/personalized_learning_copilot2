"""Direct profile indexer for immediate debugging.

This module provides a direct way to index student profiles in Azure AI Search,
bypassing any potential issues in the normal indexing flow.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import JSONResponse
import logging
import os
import traceback
from typing import Dict, Any
import json
import uuid
from datetime import datetime

from config.settings import Settings
from auth.entra_auth import get_current_user
from services.search_service import get_search_service
from rag.openai_adapter import get_openai_adapter
from utils.student_profile_manager import get_student_profile_manager

# Initialize settings
settings = Settings()

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/direct-index", tags=["direct-index"])

@router.post("/profile")
async def direct_index_profile(
    profile_data: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_current_user)
):
    """Directly index a student profile in Azure AI Search."""
    logger.info(f"Direct index profile request from user: {current_user}")
    
    # Ensure the user is authenticated
    if not current_user or not current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
        
    try:
        # Get search service
        search_service = await get_search_service()
        
        if not search_service:
            logger.error("Search service not available")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"message": "Search service is not available"}
            )
            
        # Check if the index exists
        index_exists = await search_service.check_index_exists("student-profiles")
        
        if not index_exists:
            logger.error("student-profiles index does not exist")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "student-profiles index does not exist"}
            )
            
        # Prepare the profile document
        profile_id = profile_data.get("id") or str(uuid.uuid4())
        
        # Format datetime for Edm.DateTimeOffset (ISO 8601 format with 'Z' for UTC timezone)
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Helper function to format datetime strings properly
        def format_datetime(dt_str):
            if not dt_str:
                return now
            try:
                if isinstance(dt_str, str):
                    # Parse the string to datetime and then format correctly
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                elif isinstance(dt_str, datetime):
                    return dt_str.strftime("%Y-%m-%dT%H:%M:%SZ")
                else:
                    return now
            except:
                return now
        
        profile_document = {
            "id": profile_id,
            "full_name": profile_data.get("full_name") or "Test Student",
            "gender": profile_data.get("gender") or "Unknown",
            "grade_level": profile_data.get("grade_level") or 5,
            "learning_style": profile_data.get("learning_style") or "Visual",
            "strengths": profile_data.get("strengths") or ["Mathematics", "Critical Thinking"],
            "interests": profile_data.get("interests") or ["Science", "Art"],
            "areas_for_improvement": profile_data.get("areas_for_improvement") or ["Writing", "Organization"],
            "school_name": profile_data.get("school_name") or "Test School",
            "teacher_name": profile_data.get("teacher_name") or "Test Teacher",
            "report_ids": profile_data.get("report_ids") or [],
            "created_at": format_datetime(profile_data.get("created_at")),
            "updated_at": now,
            "last_report_date": format_datetime(profile_data.get("last_report_date")),
            "current_school_year": profile_data.get("current_school_year") or "2025",
            "current_term": profile_data.get("current_term") or "S1",
            "years_and_terms": profile_data.get("years_and_terms") or ["2025-S1"],
            "historical_data": profile_data.get("historical_data") or json.dumps({
                "2025-S1": {
                    "school_year": "2025",
                    "term": "S1",
                    "grade_level": 5,
                    "updated_at": now  # already formatted correctly
                }
            }),
            # Ensure owner_id is set from current user
            "owner_id": profile_data.get("owner_id") or current_user.get("id")
        }
        
        # Generate an embedding for the profile
        openai_client = await get_openai_adapter()
        if openai_client and settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT:
            try:
                text_parts = [
                    f"Student Profile for: {profile_document.get('full_name', 'Unknown Student')}",
                    f"Gender: {profile_document.get('gender', 'Unknown')}",
                    f"Grade Level: {profile_document.get('grade_level', 'Unknown')}",
                    f"Learning Style: {profile_document.get('learning_style', 'Unknown')}",
                    f"School: {profile_document.get('school_name', 'Unknown')}",
                ]
                
                # Add strengths
                strengths = profile_document.get("strengths", [])
                if strengths:
                    text_parts.append("Strengths:")
                    for strength in strengths:
                        text_parts.append(f"- {strength}")
                
                # Add interests
                interests = profile_document.get("interests", [])
                if interests:
                    text_parts.append("Interests:")
                    for interest in interests:
                        text_parts.append(f"- {interest}")
                
                # Add areas for improvement
                areas_for_improvement = profile_document.get("areas_for_improvement", [])
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
                
                profile_document["embedding"] = embedding
                logger.info("Generated embedding for profile")
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
                # Continue without embedding
                
        # Index the profile document - raw direct indexing
        try:
            logger.info(f"Directly indexing profile with ID: {profile_id}")
            try:
                index_result = await search_service.index_document(
                    index_name="student-profiles",
                    document=profile_document
                )
            except Exception as index_error:
                logger.error(f"Direct indexing failed: {index_error}")
                logger.error(traceback.format_exc())
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"message": f"Direct indexing failed: {str(index_error)}"}
                )
            
            if index_result:
                logger.info("Direct profile indexing successful")
                return {
                    "message": "Profile indexed successfully",
                    "profile_id": profile_id,
                    "status": "success"
                }
            else:
                logger.error("Direct profile indexing failed")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"message": "Profile indexing failed"}
                )
                
        except Exception as e:
            logger.error(f"Error indexing profile: {e}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": f"Error indexing profile: {str(e)}"}
            )
            
    except Exception as e:
        logger.error(f"Error in direct_index_profile: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Error: {str(e)}"}
        )

# Include router in app
direct_index_router = router