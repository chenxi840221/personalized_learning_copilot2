#!/usr/bin/env python3
# backend/services/learning_integration_service.py

"""
Integration service that connects the recommendation system with the learning planner.
This service provides a simplified API for creating personalized learning plans
based on student profiles and educational content in Azure AI Search.
"""

import logging
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from models.user import User
from models.content import Content
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus
from services.recommendation_service import get_recommendation_service
from rag.learning_planner import get_learning_planner
from rag.retriever import retrieve_relevant_content
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class LearningIntegrationService:
    """
    Integration service that connects content recommendations with learning plan generation.
    Provides simplified methods for creating and managing personalized learning experiences.
    """
    
    def __init__(self):
        """Initialize the learning integration service."""
        self.recommendation_service = None
        self.learning_planner = None
    
    async def initialize(self):
        """Initialize the required components."""
        self.recommendation_service = await get_recommendation_service()
        self.learning_planner = await get_learning_planner()
    
    async def create_personalized_learning_plan(
        self,
        student: User,
        subject: str,
        content_count: int = 15,
        duration_days: int = 14
    ) -> LearningPlan:
        """
        Create a personalized learning plan for a student.
        
        Args:
            student: The student user
            subject: Subject to focus on
            content_count: Number of content items to consider
            duration_days: Duration of the plan in days
            
        Returns:
            A personalized learning plan
        """
        if not self.recommendation_service or not self.learning_planner:
            await self.initialize()
        
        try:
            # Step 1: Get relevant content tailored to the student's profile
            relevant_content = await retrieve_relevant_content(
                student_profile=student,
                subject=subject,
                k=content_count
            )
            
            logger.info(f"Retrieved {len(relevant_content)} content items for {subject}")
            
            # If no content found, try with more general retrieval
            if not relevant_content and student.grade_level:
                # Fallback to getting content for the subject without grade filtering
                no_grade_student = User(
                    id=student.id,
                    username=student.username,
                    email=student.email,
                    full_name=student.full_name,
                    subjects_of_interest=student.subjects_of_interest,
                    learning_style=student.learning_style,
                    is_active=student.is_active
                )
                relevant_content = await retrieve_relevant_content(
                    student_profile=no_grade_student,
                    subject=subject,
                    k=content_count
                )
                logger.info(f"Fallback retrieved {len(relevant_content)} content items")
            
            # Step 2: Create learning plan using relevant content
            if relevant_content:
                learning_plan = await self.learning_planner.create_learning_plan(
                    student=student,
                    subject=subject,
                    relevant_content=relevant_content,
                    duration_days=duration_days
                )
                return learning_plan
            else:
                # Create a fallback plan with no content
                logger.warning(f"No relevant content found for {subject}. Creating empty plan.")
                
                plan_id = str(uuid.uuid4())
                now = datetime.utcnow()
                
                return LearningPlan(
                    id=plan_id,
                    student_id=student.id,
                    title=f"{subject} Learning Plan",
                    description=f"A personalized learning plan for {subject}. Please check back later for content.",
                    subject=subject,
                    topics=[subject],
                    activities=[],
                    status=ActivityStatus.NOT_STARTED,
                    progress_percentage=0.0,
                    created_at=now,
                    updated_at=now,
                    start_date=now
                )
                
        except Exception as e:
            logger.error(f"Error creating personalized learning plan: {e}")
            # Return a basic plan in case of error
            plan_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            return LearningPlan(
                id=plan_id,
                student_id=student.id,
                title=f"{subject} Learning Plan",
                description=f"A basic learning plan for {subject}.",
                subject=subject,
                topics=[subject],
                activities=[],
                status=ActivityStatus.NOT_STARTED,
                progress_percentage=0.0,
                created_at=now,
                updated_at=now,
                start_date=now
            )
            
    async def create_advanced_learning_path(
        self,
        student: User,
        subject: str,
        content_count: int = 20,
        duration_weeks: int = 4
    ) -> Dict[str, Any]:
        """
        Create a comprehensive learning path with weekly structure.
        
        Args:
            student: The student user
            subject: Subject to focus on
            content_count: Number of content items to consider
            duration_weeks: Duration in weeks
            
        Returns:
            A structured learning path
        """
        if not self.recommendation_service or not self.learning_planner:
            await self.initialize()
            
        try:
            # Step 1: Get diverse and relevant content
            # We'll get content by topics if possible for better organization
            topics = await self._get_subject_topics(subject, student.grade_level)
            
            all_content = []
            # Get content by topic if topics were found
            if topics:
                for topic in topics[:5]:  # Use up to 5 topics
                    topic_content = await self.recommendation_service.get_content_by_topics(
                        topics=[topic],
                        grade_level=student.grade_level,
                        limit=content_count // len(topics[:5])
                    )
                    all_content.extend(topic_content)
            
            # If we don't have enough content by topics, use regular recommendation
            if len(all_content) < content_count:
                additional_content = await self.recommendation_service.get_personalized_recommendations(
                    user=student,
                    subject=subject,
                    limit=content_count - len(all_content)
                )
                all_content.extend([c for c in additional_content if c.id not in [existing.id for existing in all_content]])
            
            # Step 2: Create advanced learning path
            if all_content:
                learning_path = await self.learning_planner.create_advanced_learning_path(
                    student=student,
                    subject=subject,
                    relevant_content=all_content,
                    duration_weeks=duration_weeks
                )
                return learning_path
            else:
                # Create a fallback path with no content
                return {
                    "id": str(uuid.uuid4()),
                    "title": f"{subject} Learning Path",
                    "description": f"A learning path for {subject}",
                    "overall_goal": f"Learn the fundamentals of {subject}",
                    "student_id": student.id,
                    "subject": subject,
                    "created_at": datetime.utcnow().isoformat(),
                    "weeks": []
                }
                
        except Exception as e:
            logger.error(f"Error creating advanced learning path: {e}")
            # Return a basic path in case of error
            return {
                "id": str(uuid.uuid4()),
                "title": f"{subject} Learning Path",
                "description": f"A learning path for {subject}",
                "overall_goal": f"Learn the fundamentals of {subject}",
                "student_id": student.id,
                "subject": subject,
                "created_at": datetime.utcnow().isoformat(),
                "weeks": []
            }
    
    async def get_personalized_content_recommendations(
        self,
        student: User,
        subject: Optional[str] = None,
        limit: int = 10
    ) -> List[Content]:
        """
        Get personalized content recommendations for a student.
        
        Args:
            student: The student user
            subject: Optional subject filter
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended content items
        """
        if not self.recommendation_service:
            await self.initialize()
            
        try:
            # Get recommendations using enhanced ranking
            recommendations = await self.recommendation_service.get_personalized_recommendations(
                user=student,
                subject=subject,
                limit=limit
            )
            
            return recommendations
        except Exception as e:
            logger.error(f"Error getting content recommendations: {e}")
            return []
    
    async def get_learning_style_recommendations(
        self,
        student: User,
        subject: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, List[Content]]:
        """
        Get content recommendations organized by content types that match the student's learning style.
        
        Args:
            student: The student user
            subject: Optional subject filter
            limit: Maximum number of recommendations
            
        Returns:
            Dictionary mapping content types to content lists
        """
        if not self.recommendation_service:
            await self.initialize()
            
        try:
            # Get recommendations grouped by learning style
            recommendations = await self.recommendation_service.get_recommendations_by_learning_style(
                user=student,
                subject=subject,
                limit=limit
            )
            
            return recommendations
        except Exception as e:
            logger.error(f"Error getting learning style recommendations: {e}")
            return {}
    
    async def _get_subject_topics(self, subject: str, grade_level: Optional[int] = None) -> List[str]:
        """
        Get common topics for a subject based on available content.
        
        Args:
            subject: The subject to get topics for
            grade_level: Optional grade level filter
            
        Returns:
            List of common topics for the subject
        """
        if not self.recommendation_service:
            await self.initialize()
            
        try:
            # Get content for the subject
            filter_expression = f"subject eq '{subject}'"
            if grade_level:
                filter_expression += f" and grade_level/any(g: g eq {grade_level})"
                
            # Use recommendation service to execute search
            results = await self.recommendation_service.search_client.search(
                search_text="*",
                filter=filter_expression,
                select=["topics"],
                top=100
            )
            
            # Collect all topics
            topic_counts = {}
            async for result in results:
                if "topics" in result:
                    for topic in result["topics"]:
                        topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            # Sort topics by frequency
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Return the top 10 topics
            return [topic for topic, count in sorted_topics[:10]]
        except Exception as e:
            logger.error(f"Error getting subject topics: {e}")
            return [subject]  # Fall back to just the subject as a topic

# Singleton instance
learning_integration_service = None

async def get_learning_integration_service():
    """Get or create the learning integration service singleton."""
    global learning_integration_service
    if learning_integration_service is None:
        learning_integration_service = LearningIntegrationService()
        await learning_integration_service.initialize()
    return learning_integration_service