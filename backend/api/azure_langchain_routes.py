# backend/api/azure_langchain_routes.py
"""
API routes for Azure LangChain integration in the Personalized Learning Co-pilot.
These endpoints provide access to AI-powered educational features.
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query, status
from typing import List, Dict, Any, Optional
import logging

from models.user import User
from auth.authentication import get_current_user
from services.azure_langchain_service import get_azure_langchain_service
from utils.vector_store import get_vector_store

# Initialize logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/learning-plan")
async def create_learning_plan(
    subject: str = Body(..., embed=True),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a personalized learning plan for a student using AI.
    
    Args:
        subject: Subject for the learning plan
        current_user: Current authenticated user
        
    Returns:
        A personalized learning plan
    """
    try:
        # Ensure we have a valid user
        if not current_user:
            logger.error("Authentication failed: No current user")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Log the request for debugging
        logger.info(f"Creating learning plan for user ID: {current_user.get('id')} and subject: {subject}")
        
        # Convert user dict to User model
        user = User(**current_user)
        
        # Get vector store for content retrieval
        vector_store = await get_vector_store()
        
        # Retrieve relevant content for the subject
        query_text = f"Educational content for {subject} appropriate for a student in grade {user.grade_level}"
        
        # Build filter for content
        filter_expression = f"subject eq '{subject}'"
        
        # Add grade level filter if available
        if user.grade_level:
            grade_filters = [
                f"grade_level/any(g: g eq {user.grade_level})",
                f"grade_level/any(g: g eq {user.grade_level - 1})",
                f"grade_level/any(g: g eq {user.grade_level + 1})"
            ]
            grade_filter = f"({' or '.join(grade_filters)})"
            filter_expression = f"{filter_expression} and {grade_filter}"
        
        # Get content items
        content_items = await vector_store.vector_search(
            query_text=query_text,
            filter_expression=filter_expression,
            limit=15  # Get enough content for a good learning plan
        )
        
        # Convert to Content objects
        from models.content import Content, ContentType, DifficultyLevel
        
        contents = []
        for item in content_items:
            try:
                # Convert string enums to proper enum values
                item["content_type"] = ContentType(item["content_type"])
                item["difficulty_level"] = DifficultyLevel(item["difficulty_level"])
                contents.append(Content(**item))
            except Exception as e:
                logger.error(f"Error converting content item: {e}")
        
        # Get Azure LangChain service
        langchain_service = await get_azure_langchain_service()
        
        # Generate learning plan
        learning_plan = await langchain_service.generate_personalized_learning_plan(
            student=user,
            subject=subject,
            relevant_content=contents
        )
        
        # Save learning plan to database or storage
        # This would typically involve saving to a database
        
        # For now, just return the plan
        return learning_plan.dict() if hasattr(learning_plan, "dict") else learning_plan
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating AI learning plan: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating learning plan: {str(e)}"
        )

@router.post("/ask")
async def ask_question(
    question: str = Body(..., embed=True),
    subject: Optional[str] = Body(None, embed=True),
    current_user: Dict = Depends(get_current_user)
):
    """
    Ask an educational question and get an AI-powered answer.
    
    Args:
        question: The question to ask
        subject: Optional subject for context
        current_user: Current authenticated user
        
    Returns:
        Answer with sources
    """
    try:
        # Convert user dict to User model
        user = User(**current_user)
        
        # Get Azure LangChain service
        langchain_service = await get_azure_langchain_service()
        
        # Get answer with grade level and subject context
        response = await langchain_service.answer_educational_question(
            question=question,
            student_grade=user.grade_level,
            subject=subject
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error answering question: {str(e)}"
        )

@router.post("/search")
async def search_content(
    query: str = Body(..., embed=True),
    subject: Optional[str] = Body(None, embed=True),
    content_type: Optional[str] = Body(None, embed=True),
    limit: int = Body(10, embed=True),
    current_user: Dict = Depends(get_current_user)
):
    """
    Search for educational content using AI.
    
    Args:
        query: Search query
        subject: Optional subject filter
        content_type: Optional content type filter
        limit: Maximum number of results
        current_user: Current authenticated user
        
    Returns:
        List of relevant content items
    """
    try:
        # Convert user dict to User model
        user = User(**current_user)
        
        # Get Azure LangChain service
        langchain_service = await get_azure_langchain_service()
        
        # Search for content
        results = await langchain_service.search_educational_content(
            query=query,
            student=user,
            subject=subject,
            content_type=content_type,
            limit=limit
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching content: {str(e)}"
        )

@router.get("/personalized-recommendations")
async def personalized_recommendations(
    subject: Optional[str] = Query(None),
    limit: int = Query(10),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get personalized content recommendations using AI.
    
    Args:
        subject: Optional subject filter
        limit: Maximum number of results
        current_user: Current authenticated user
        
    Returns:
        List of personalized recommendations
    """
    try:
        # Convert user dict to User model
        user = User(**current_user)
        
        # Get recommendation service - import here to avoid circular imports
        from services.recommendation_service import get_recommendation_service
        recommendation_service = await get_recommendation_service()
        
        # Get recommendations
        results = await recommendation_service.get_personalized_recommendations(
            user=user,
            subject=subject,
            limit=limit
        )
        
        # Return as dictionaries for JSON serialization
        return [item.dict() for item in results]
        
    except Exception as e:
        logger.error(f"Error getting personalized recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting recommendations: {str(e)}"
        )

# Export router
azure_langchain_router = router