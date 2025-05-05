# backend/services/langchain_service.py
"""
LangChain Service for the Personalized Learning Co-pilot.
This module provides high-level LangChain functionality for the application.
"""

import logging
from typing import List, Dict, Any, Optional
import os
import sys
import json
from datetime import datetime

# Add backend directory to path to resolve imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import after path resolution
from models.user import User
from models.content import Content
from rag.langchain_manager import get_langchain_manager
from rag.generator import get_plan_generator
from utils.vector_store import get_vector_store

# Initialize logger
logger = logging.getLogger(__name__)

class LangChainService:
    """
    Service for LangChain operations in the Personalized Learning Co-pilot.
    """
    
    def __init__(self):
        """Initialize the LangChain service."""
        self.langchain_manager = get_langchain_manager()
    
    async def generate_learning_plan(
        self,
        student: User,
        subject: str,
        relevant_content: List[Content]
    ) -> Dict[str, Any]:
        """
        Generate a personalized learning plan for a student.
        
        Args:
            student: The student
            subject: Subject for the learning plan
            relevant_content: List of relevant content
            
        Returns:
            Generated learning plan
        """
        try:
            # Convert Content objects to dictionaries for plan generation
            content_dicts = [
                {
                    "id": content.id,
                    "title": content.title,
                    "description": content.description,
                    "content_type": content.content_type,
                    "difficulty_level": content.difficulty_level,
                    "url": content.url,
                    "duration_minutes": content.duration_minutes
                }
                for content in relevant_content
            ]
            
            # Convert student to dictionary
            student_dict = {
                "id": student.id,
                "username": student.username,
                "full_name": student.full_name,
                "grade_level": student.grade_level,
                "learning_style": student.learning_style,
                "subjects_of_interest": student.subjects_of_interest
            }
            
            # Use the LangChain manager to generate the plan
            learning_plan = await self.langchain_manager.generate_personalized_learning_plan(
                student_profile=student_dict,
                subject=subject,
                available_content=content_dicts
            )
            
            return learning_plan
            
        except Exception as e:
            logger.error(f"Error generating learning plan: {e}")
            # Return a simple default plan
            return {
                "title": f"{subject} Learning Plan",
                "description": f"A learning plan for {subject}",
                "subject": subject,
                "activities": []
            }
    
    async def generate_personalized_response(
        self,
        query: str,
        student: User,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a personalized response to a student's query.
        
        Args:
            query: The student's query
            student: The student asking the query
            chat_history: Optional chat history
            
        Returns:
            Response with answer and sources
        """
        try:
            # Create system prompt with personalization
            grade_level = student.grade_level or "unknown"
            learning_style = student.learning_style.value if student.learning_style else "mixed"
            
            system_prompt = f"""
            You are an educational assistant for a student in grade {grade_level} with a 
            {learning_style} learning style. Provide helpful, accurate information that 
            is appropriate for their educational level and learning preferences.
            
            When possible, provide explanations that cater to their learning style:
            - For visual learners: describe concepts with visual analogies and suggest diagrams
            - For auditory learners: use rhythm and emphasize how concepts would be explained verbally
            - For reading/writing learners: use precise terminology and suggest reading materials
            - For kinesthetic learners: relate concepts to physical activities and real-world applications
            - For mixed learners: provide a balanced approach
            
            Answer the student's questions accurately, but keep your responses at an appropriate 
            level for grade {grade_level}.
            """
            
            # Get vector store for content retrieval
            vector_store = await get_vector_store()
            
            # Search for relevant content
            search_results = await vector_store.vector_search(
                query_text=query,
                filter_expression=None,
                limit=5
            )
            
            # Extract context from search results
            context = "\n\n".join([
                f"Title: {result.get('title', 'Untitled')}\n"
                f"{result.get('page_content', result.get('metadata_content_text', ''))}"
                for result in search_results
            ])
            
            # Generate response using LangChain
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context information: {context}\n\nQuestion: {query}"}
            ]
            
            # Add chat history if provided
            if chat_history:
                for message in chat_history:
                    messages.append({"role": message["role"], "content": message["content"]})
            
            # Generate response
            response = await self.langchain_manager.llm.ainvoke(messages)
            
            # Format response with sources
            return {
                "answer": response.content,
                "source_documents": search_results
            }
            
        except Exception as e:
            logger.error(f"Error generating personalized response: {e}")
            return {
                "answer": f"I'm sorry, I wasn't able to generate a response. Error: {str(e)}",
                "source_documents": []
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
        Search for educational content based on a query and student profile.
        
        Args:
            query: Search query
            student: Student profile for personalization
            subject: Optional subject filter
            content_type: Optional content type filter
            limit: Maximum number of results
            
        Returns:
            List of content items
        """
        try:
            # Build filter expression
            filter_parts = []
            if subject:
                filter_parts.append(f"subject eq '{subject}'")
            if content_type:
                filter_parts.append(f"content_type eq '{content_type}'")
                
            # Add grade level filter if available
            if student.grade_level:
                grade_filters = [
                    f"grade_level/any(g: g eq {student.grade_level})",
                    f"grade_level/any(g: g eq {student.grade_level - 1})",
                    f"grade_level/any(g: g eq {student.grade_level + 1})"
                ]
                filter_parts.append(f"({' or '.join(grade_filters)})")
                
            filter_expression = " and ".join(filter_parts) if filter_parts else None
            
            # Enhance query with learning style
            enhanced_query = query
            if student.learning_style:
                enhanced_query = f"{query} for {student.learning_style.value} learners"
            
            # Get vector store for content retrieval
            vector_store = await get_vector_store()
            
            # Perform search
            search_results = await vector_store.vector_search(
                query_text=enhanced_query,
                filter_expression=filter_expression,
                limit=limit
            )
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching educational content: {e}")
            return []
    
    async def index_educational_content(self, contents: List[Content]) -> bool:
        """
        Index educational content for search and retrieval.
        
        Args:
            contents: List of content to index
            
        Returns:
            Success status
        """
        try:
            # Convert content objects to dictionaries
            content_dicts = []
            
            for content in contents:
                # Create dictionary from content object
                content_dict = content.dict()
                
                # Extract text for embedding
                text = (
                    f"Title: {content.title}\n"
                    f"Subject: {content.subject}\n"
                    f"Description: {content.description}\n"
                )
                
                # Add the dictionary to the list
                content_dicts.append((text, content_dict))
            
            # Index each content item
            success_count = 0
            for text, metadata in content_dicts:
                result = await self.langchain_manager.add_documents([text], [metadata])
                if result:
                    success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error indexing educational content: {e}")
            return False
    
    async def answer_educational_question(
        self,
        question: str,
        student_grade: Optional[int] = None,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer an educational question using RAG.
        
        Args:
            question: The question to answer
            student_grade: Optional grade level for context
            subject: Optional subject for context
            
        Returns:
            Answer with sources
        """
        try:
            # Build system prompt
            system_prompt = "You are an educational assistant that provides accurate, helpful information."
            
            if student_grade:
                system_prompt += f" The student is in grade {student_grade}, so tailor your response appropriately."
                
            if subject:
                system_prompt += f" The question is about {subject}."
                
            # Create RAG query
            # Get vector store for content retrieval
            vector_store = await get_vector_store()
            
            # Build filter expression
            filter_expression = None
            if subject:
                filter_expression = f"subject eq '{subject}'"
                
            # Perform search
            search_results = await vector_store.vector_search(
                query_text=question,
                filter_expression=filter_expression,
                limit=5
            )
            
            # Extract context from search results
            context = "\n\n".join([
                f"Title: {result.get('title', 'Untitled')}\n"
                f"{result.get('page_content', result.get('metadata_content_text', ''))}"
                for result in search_results
            ])
            
            # Generate answer using LangChain
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
                Context information:
                {context}
                
                Based on the above context and your knowledge, please answer the following question:
                {question}
                """}
            ]
            
            # Generate response
            response = await self.langchain_manager.llm.ainvoke(messages)
            
            return {
                "answer": response.content,
                "sources": search_results
            }
            
        except Exception as e:
            logger.error(f"Error answering educational question: {e}")
            return {
                "answer": f"I wasn't able to answer that question. Error: {str(e)}",
                "sources": []
            }

# Singleton instance
langchain_service = None

async def get_langchain_service():
    """Get or create the LangChain service singleton."""
    global langchain_service
    if langchain_service is None:
        langchain_service = LangChainService()
    return langchain_service