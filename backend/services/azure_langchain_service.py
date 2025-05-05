# backend/services/azure_langchain_service.py
"""
Azure LangChain Service for the Personalized Learning Co-pilot.
This module provides high-level Azure-specific LangChain functionality.
"""

import logging
from typing import List, Dict, Any, Optional
import os
import sys
import json
import uuid
from datetime import datetime, timedelta

# Add backend directory to path to resolve imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import after path resolution
from models.user import User
from models.content import Content
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from rag.azure_langchain_integration import get_azure_langchain
from utils.vector_store import get_vector_store

# Initialize logger
logger = logging.getLogger(__name__)

class AzureLangChainService:
    """
    Service for Azure-specific LangChain operations in the Personalized Learning Co-pilot.
    """
    
    def __init__(self):
        """Initialize the Azure LangChain service."""
        self.azure_langchain = None
    
    async def initialize(self):
        """Initialize Azure LangChain integration."""
        if not self.azure_langchain:
            try:
                self.azure_langchain = await get_azure_langchain()
                logger.info("Azure LangChain integration initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Azure LangChain: {e}")
                # Allow service to continue even if initialization fails
                # Methods will check for self.azure_langchain before use
    
    async def generate_personalized_learning_plan(
        self,
        student: User,
        subject: str,
        relevant_content: List[Content]
    ) -> LearningPlan:
        """
        Generate a personalized learning plan for a student using Azure LangChain.
        
        Args:
            student: The student
            subject: Subject for the learning plan
            relevant_content: List of relevant content
            
        Returns:
            Generated learning plan
        """
        try:
            # Ensure Azure LangChain is initialized
            await self.initialize()
            
            if not self.azure_langchain:
                logger.warning("Azure LangChain not available. Creating simple learning plan instead.")
                return await self._create_simple_learning_plan(student, subject, relevant_content)
            
            # Convert content objects to dictionaries for the prompt
            content_dicts = []
            for content in relevant_content:
                try:
                    content_dict = {
                        "id": content.id,
                        "title": content.title,
                        "description": content.description,
                        "content_type": str(content.content_type),
                        "difficulty_level": str(content.difficulty_level),
                        "url": str(content.url)
                    }
                    content_dicts.append(content_dict)
                except Exception as e:
                    logger.warning(f"Error converting content to dict: {e}")
            
            # Convert student to dictionary
            student_dict = {
                "full_name": student.full_name or student.username,
                "grade_level": student.grade_level,
                "learning_style": student.learning_style.value if student.learning_style else "mixed",
                "subjects_of_interest": student.subjects_of_interest
            }
            
            # Generate learning plan
            plan_dict = await self.azure_langchain.generate_learning_plan_with_rag(
                student_profile=student_dict,
                subject=subject,
                available_content=content_dicts
            )
            
            # Convert the plan dict to a LearningPlan object
            now = datetime.utcnow()
            plan_id = plan_dict.get("id", str(uuid.uuid4()))
            
            # Process activities
            activities = []
            for activity_dict in plan_dict.get("activities", []):
                activity_id = activity_dict.get("id", str(uuid.uuid4()))
                content_id = activity_dict.get("content_id")
                
                # Validate content_id exists in relevant_content
                if content_id:
                    if not any(str(content.id) == content_id for content in relevant_content):
                        content_id = None
                
                # Create activity
                activity = LearningActivity(
                    id=activity_id,
                    title=activity_dict.get("title", "Activity"),
                    description=activity_dict.get("description", "Learn about this topic"),
                    content_id=content_id,
                    duration_minutes=activity_dict.get("duration_minutes", 30),
                    order=activity_dict.get("order", 1),
                    status=ActivityStatus.NOT_STARTED,
                    completed_at=None
                )
                activities.append(activity)
            
            # Create learning plan
            learning_plan = LearningPlan(
                id=plan_id,
                student_id=student.id,
                title=plan_dict.get("title", f"{subject} Learning Plan"),
                description=plan_dict.get("description", f"A personalized learning plan for {subject}"),
                subject=subject,
                topics=plan_dict.get("topics", [subject]),
                activities=activities,
                status=ActivityStatus.NOT_STARTED,
                progress_percentage=0.0,
                created_at=now,
                updated_at=now,
                start_date=now,
                end_date=now + timedelta(days=14)  # Default to 2 weeks
            )
            
            return learning_plan
            
        except Exception as e:
            logger.error(f"Error creating learning plan: {e}", exc_info=True)
            # Create a simple plan as fallback
            return await self._create_simple_learning_plan(student, subject, relevant_content)
    
    async def _create_simple_learning_plan(
        self,
        student: User,
        subject: str,
        relevant_content: List[Content]
    ) -> LearningPlan:
        """
        Create a simple learning plan as a fallback when AI generation fails.
        
        Args:
            student: The student
            subject: Subject for the learning plan
            relevant_content: List of relevant content
            
        Returns:
            A simple learning plan
        """
        now = datetime.utcnow()
        plan_id = str(uuid.uuid4())
        
        # Create activities from the relevant content
        activities = []
        for i, content in enumerate(relevant_content[:5]):  # Use up to 5 pieces of content
            activity = LearningActivity(
                id=str(uuid.uuid4()),
                title=f"Study: {content.title}",
                description=content.description or f"Learn about {content.title}",
                content_id=content.id,
                duration_minutes=content.duration_minutes or 30,
                order=i + 1,
                status=ActivityStatus.NOT_STARTED,
                completed_at=None
            )
            activities.append(activity)
        
        # If no content is available, create a generic activity
        if not activities:
            activity = LearningActivity(
                id=str(uuid.uuid4()),
                title=f"Learn about {subject}",
                description=f"Research and study key concepts in {subject}",
                content_id=None,
                duration_minutes=45,
                order=1,
                status=ActivityStatus.NOT_STARTED,
                completed_at=None
            )
            activities.append(activity)
        
        # Create learning plan
        learning_plan = LearningPlan(
            id=plan_id,
            student_id=student.id,
            title=f"{subject} Learning Plan",
            description=f"A learning plan to help you master {subject} concepts",
            subject=subject,
            topics=[subject],
            activities=activities,
            status=ActivityStatus.NOT_STARTED,
            progress_percentage=0.0,
            created_at=now,
            updated_at=now,
            start_date=now,
            end_date=now + timedelta(days=14)  # Default to 2 weeks
        )
        
        return learning_plan
    
    async def answer_educational_question(
        self,
        question: str,
        student_grade: Optional[int] = None,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer an educational question using Azure LangChain RAG.
        
        Args:
            question: The question to answer
            student_grade: Optional grade level for context
            subject: Optional subject for context
            
        Returns:
            Answer with sources
        """
        try:
            # Ensure Azure LangChain is initialized
            await self.initialize()
            
            if not self.azure_langchain:
                return {
                    "answer": "I'm sorry, but the AI service is currently unavailable. Please try again later.",
                    "sources": []
                }
            
            # Create system prompt with context
            system_prompt = "You are an educational assistant that provides accurate, helpful information."
            
            if student_grade:
                system_prompt += f" The student is in grade {student_grade}, so tailor your response appropriately."
                
            if subject:
                system_prompt += f" The question is about {subject}."
            
            # Create RAG chain
            rag_chain = await self.azure_langchain.create_rag_chain(system_prompt)
            
            # Generate answer
            answer = await rag_chain.ainvoke(question)
            
            # Get vector store for retrieving sources
            vector_store = await get_vector_store()
            
            # Build filter expression
            filter_expression = None
            if subject:
                filter_expression = f"subject eq '{subject}'"
                
            # Get relevant sources
            sources = await vector_store.vector_search(
                query_text=question,
                filter_expression=filter_expression,
                limit=3
            )
            
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "answer": f"I wasn't able to answer that question. Error: {str(e)}",
                "sources": []
            }
    
    async def search_educational_content(
        self,
        query: str,
        student: User,
        subject: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for educational content using Azure Search with enhanced filters.
        
        Args:
            query: Search query
            student: Student information for personalization
            subject: Optional subject filter
            content_type: Optional content type filter
            limit: Maximum number of results
            
        Returns:
            List of content items
        """
        try:
            # Get vector store for content retrieval
            vector_store = await get_vector_store()
            
            # Build filter expression
            filter_parts = []
            if subject:
                filter_parts.append(f"subject eq '{subject}'")
            if content_type:
                filter_parts.append(f"content_type eq '{content_type}'")
                
            # Add grade-appropriate filter if student has a grade level
            if student.grade_level:
                grade_filters = []
                for g in range(max(1, student.grade_level - 1), min(12, student.grade_level + 2)):
                    grade_filters.append(f"grade_level/any(g: g eq {g})")
                
                if grade_filters:
                    filter_parts.append(f"({' or '.join(grade_filters)})")
            
            filter_expression = " and ".join(filter_parts) if filter_parts else None
            
            # Enhance query with learning style if available
            enhanced_query = query
            if student.learning_style:
                enhanced_query = f"{query} for {student.learning_style.value} learners"
            
            # Perform search
            results = await vector_store.vector_search(
                query_text=enhanced_query,
                filter_expression=filter_expression,
                limit=limit
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching educational content: {e}")
            return []

# Singleton instance
azure_langchain_service = None

async def get_azure_langchain_service():
    """Get or create the Azure LangChain service singleton."""
    global azure_langchain_service
    if azure_langchain_service is None:
        azure_langchain_service = AzureLangChainService()
        await azure_langchain_service.initialize()
    return azure_langchain_service