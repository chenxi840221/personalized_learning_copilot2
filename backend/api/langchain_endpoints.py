# backend/api/langchain_endpoints.py
"""
API endpoints for LangChain-based functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from typing import List, Dict, Any, Optional
import logging

from models.user import User
from services.langchain_service import get_langchain_service
from auth.authentication import get_current_user
from utils.vector_store import get_vector_store
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/langchain", tags=["langchain"])

@router.post("/learning-plan")
async def create_learning_plan(
    subject: str = Body(..., embed=True),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a personalized learning plan using LangChain.
    
    Args:
        subject: Subject for the learning plan
        current_user: Current authenticated user
        
    Returns:
        A personalized learning plan
    """
    try:
        # Convert user dict to User model
        user = User(**current_user)
        
        # Get vector store for content retrieval
        vector_store = await get_vector_store()
        
        # Prepare query text for content retrieval
        query_text = f"Educational content for {subject} for a student in grade {user.grade_level if user.grade_level else 'unknown'}"
        
        # Get relevant content for the subject
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
        
        # Get content
        content_items = await vector_store.vector_search(
            query_text=query_text,
            filter_expression=filter_expression,
            limit=10
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
        
        # Get LangChain service
        langchain_service = await get_langchain_service()
        
        # Generate learning plan
        learning_plan = await langchain_service.generate_learning_plan(
            student=user,
            subject=subject,
            relevant_content=contents
        )
        
        # Save learning plan to database or storage
        # This would typically involve saving to a database
        
        # For now, return the plan
        return learning_plan.dict() if hasattr(learning_plan, "dict") else learning_plan
        
    except Exception as e:
        logger.error(f"Error creating learning plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating learning plan: {str(e)}"
        )

@router.post("/query")
async def query_assistant(
    query: str = Body(..., embed=True),
    chat_history: Optional[List[Dict[str, str]]] = Body(None, embed=True),
    current_user: Dict = Depends(get_current_user)
):
    """
    Query the educational assistant using LangChain RAG.
    
    Args:
        query: User query
        chat_history: Optional chat history
        current_user: Current authenticated user
        
    Returns:
        Response with answer and sources
    """
    try:
        # Convert user dict to User model
        user = User(**current_user)
        
        # Get LangChain service
        langchain_service = await get_langchain_service()
        
        # Generate personalized response
        response = await langchain_service.generate_personalized_response(
            query=query,
            student=user,
            chat_history=chat_history
        )
        
        # Format source documents if available
        sources = []
        if "source_documents" in response and response["source_documents"]:
            for doc in response["source_documents"]:
                source = {
                    "title": doc.metadata.get("title", "Unknown source"),
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "url": doc.metadata.get("url", "")
                }
                sources.append(source)
        
        # Return the response
        return {
            "answer": response["answer"],
            "sources": sources
        }
        
    except Exception as e:
        logger.error(f"Error querying assistant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying assistant: {str(e)}"
        )

@router.post("/embed")
async def generate_embedding(
    text: str = Body(..., embed=True),
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate an embedding for text using LangChain's embedding model.
    
    Args:
        text: Text to embed
        current_user: Current authenticated user
        
    Returns:
        Text embedding
    """
    try:
        # Get LangChain service
        langchain_service = await get_langchain_service()
        
        # Generate embedding
        embedding = await langchain_service.langchain_manager.generate_embedding(text)
        
        return {
            "embedding": embedding,
            "dimensions": len(embedding)
        }
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating embedding: {str(e)}"
        )

# Export router
langchain_router = router