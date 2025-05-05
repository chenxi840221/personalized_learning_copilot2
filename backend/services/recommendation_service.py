import logging
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import Vector

from models.user import User
from models.content import Content, ContentType, DifficultyLevel
from config.settings import Settings
from rag.openai_adapter import get_openai_adapter

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class RecommendationService:
    """Service for generating content recommendations using Azure AI Search."""
    
    def __init__(self):
        """Initialize recommendation service."""
        self.search_client = None
        self.openai_adapter = None
    
    async def initialize(self):
        """Initialize Azure AI Search client and OpenAI adapter."""
        self.search_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            index_name=settings.AZURE_SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
        )
        
        self.openai_adapter = await get_openai_adapter()
    
    async def close(self):
        """Close Azure AI Search client."""
        if self.search_client:
            await self.search_client.close()
    
    async def get_personalized_recommendations(
        self,
        user: User,
        subject: Optional[str] = None,
        limit: int = 10
    ) -> List[Content]:
        """
        Get personalized content recommendations for a user using Azure AI Search.
        
        Args:
            user: User to get recommendations for
            subject: Optional subject filter
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended content items
        """
        if not self.search_client:
            await self.initialize()
        
        try:
            # Generate a query based on user profile - enhanced with more student details
            query_text = self._generate_query_text(user, subject)
            
            # Generate embedding for the query
            query_embedding = await self._generate_embedding(query_text)
            
            # Build filter based on user and subject
            filter_expression = self._build_filter_expression(user, subject)
            
            # Create the vector query for semantic search
            vector_query = Vector(
                value=query_embedding,
                k=limit * 2,  # Request more to allow for post-filtering
                fields="embedding",
                exhaustive=True
            )
            
            # Execute the search with vector and filtering
            results = await self.search_client.search(
                search_text=None,
                vectors=[vector_query],
                filter=filter_expression,
                select=["id", "title", "description", "subject", "content_type", 
                        "difficulty_level", "grade_level", "topics", "url", 
                        "duration_minutes", "keywords", "source", "metadata"],
                top=limit * 2  # Request more to allow for filtering
            )
            
            # Convert results to Content objects
            content_items = []
            async for result in results:
                content_dict = dict(result)
                
                # Convert to proper enum types for model
                try:
                    content_dict["content_type"] = ContentType(content_dict["content_type"])
                    content_dict["difficulty_level"] = DifficultyLevel(content_dict["difficulty_level"])
                    content_items.append(Content(**content_dict))
                except Exception as e:
                    logger.warning(f"Error converting search result to Content: {e}")
            
            # Apply additional ranking and filtering
            ranked_items = self._rank_recommendations(content_items, user)
            
            # Return only the requested number of recommendations
            return ranked_items[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            # Return empty list on error
            return []
    
    def _generate_query_text(self, user: User, subject: Optional[str] = None) -> str:
        """Generate query text for embedding based on user profile."""
        grade_level = str(user.grade_level) if user.grade_level else "unknown"
        learning_style = user.learning_style.value if user.learning_style else "mixed"
        interests = ", ".join(user.subjects_of_interest) if user.subjects_of_interest else "general learning"
        
        # Build a more comprehensive query to better match student needs
        query = f"Educational content for a student in grade {grade_level} "
        
        # Add learning style details to better match content types
        if learning_style == "visual":
            query += f"with a {learning_style} learning style who learns best through videos, diagrams, and visual aids. "
        elif learning_style == "auditory":
            query += f"with a {learning_style} learning style who learns best through listening, discussions, and spoken explanations. "
        elif learning_style == "reading_writing":
            query += f"with a {learning_style} learning style who learns best through reading and writing text-based materials. "
        elif learning_style == "kinesthetic":
            query += f"with a {learning_style} learning style who learns best through hands-on activities, experiments, and interactive exercises. "
        else:
            query += f"with a {learning_style} learning style. "
        
        # Add interests for better personalization
        query += f"Interested in {interests}. "
        
        # Add subject if specified
        if subject:
            query += f"Looking specifically for {subject} content. "
            # If the student has another interest in their profile, try to find content that connects both
            if user.subjects_of_interest and subject in user.subjects_of_interest:
                other_interests = [s for s in user.subjects_of_interest if s != subject]
                if other_interests:
                    query += f"Especially content that connects {subject} with {other_interests[0]}. "
        
        # Add grade-appropriate context
        if user.grade_level:
            if user.grade_level <= 5:
                query += "Content should be accessible for elementary school students with simple language and engaging activities. "
            elif user.grade_level <= 8:
                query += "Content should be appropriate for middle school students with moderate complexity and some hands-on applications. "
            else:
                query += "Content should be suitable for high school students with more complex concepts and real-world applications. "
        
        return query
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI adapter."""
        try:
            if not self.openai_adapter:
                self.openai_adapter = await get_openai_adapter()
                
            embedding = await self.openai_adapter.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=text
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Fall back to empty vector
            return [0.0] * 1536  # Default dimension for text-embedding-ada-002
    
    def _build_filter_expression(self, user: User, subject: Optional[str] = None) -> str:
        """
        Build OData filter expression for Azure AI Search with enhanced grade-level filtering.
        
        Args:
            user: The user to filter for
            subject: Optional subject filter
            
        Returns:
            OData filter expression
        """
        filters = []
        
        # Add subject filter if specified
        if subject:
            filters.append(f"subject eq '{subject}'")
        
        # Add grade level filter based on user's grade - expanded range for more natural progression
        if user.grade_level:
            # Include content for this grade level, two below, and one above
            # This gives more basic content to ensure mastery of fundamentals
            grade_filters = []
            
            # For younger students (grades 1-5), keep a narrower range
            if user.grade_level <= 5:
                grade_range = range(max(1, user.grade_level - 1), min(12, user.grade_level + 2))
            # For middle school students (grades 6-8), provide a bit more range
            elif user.grade_level <= 8:
                grade_range = range(max(1, user.grade_level - 2), min(12, user.grade_level + 2))
            # For high school students, provide even more range
            else:
                grade_range = range(max(1, user.grade_level - 2), min(12, user.grade_level + 3))
                
            for grade in grade_range:
                grade_filters.append(f"grade_level/any(g: g eq {grade})")
            
            filters.append(f"({' or '.join(grade_filters)})")
        
        # Filter for difficulty level based on user's grade
        # More nuanced approach based on grade level
        if user.grade_level:
            if user.grade_level <= 3:  # Early elementary
                filters.append("difficulty_level eq 'beginner'")
            elif user.grade_level <= 5:  # Upper elementary
                filters.append("(difficulty_level eq 'beginner' or difficulty_level eq 'intermediate')")
            elif user.grade_level <= 8:  # Middle school
                # Emphasis on intermediate with some beginner and advanced
                difficulty_filter = "(difficulty_level eq 'intermediate'"
                difficulty_filter += " or difficulty_level eq 'beginner'"
                if user.grade_level >= 7:  # 7-8th grade can handle some advanced
                    difficulty_filter += " or difficulty_level eq 'advanced'"
                difficulty_filter += ")"
                filters.append(difficulty_filter)
            else:  # High school
                # Allow all difficulty levels with emphasis on intermediate and advanced
                filters.append("(difficulty_level eq 'intermediate' or difficulty_level eq 'advanced' or difficulty_level eq 'beginner')")
        
        # Combine all filters with AND
        if filters:
            return " and ".join(filters)
        
        return None
    
    def _rank_recommendations(self, content_items: List[Content], user: User) -> List[Content]:
        """
        Apply advanced ranking to content items based on user profile.
        Incorporates learning style, content relevance, and educational progression.
        
        Args:
            content_items: List of content items from search
            user: User to rank for
            
        Returns:
            Ranked list of content items
        """
        if not content_items:
            return []
        
        # Create a scoring function based on multiple factors
        def score_content(content: Content) -> float:
            base_score = 1.0  # Start with base score
            
            # FACTOR 1: Learning style match
            if user.learning_style:
                learning_style = user.learning_style.value
                content_type = content.content_type.value
                
                # Visual learners prefer videos and visual content
                if learning_style == "visual" and content_type in ["video", "interactive"]:
                    base_score += 0.4
                
                # Auditory learners prefer audio content
                elif learning_style == "auditory" and content_type in ["video", "audio", "podcast"]:
                    base_score += 0.4
                
                # Reading/writing learners prefer text content
                elif learning_style == "reading_writing" and content_type in ["article", "worksheet", "lesson"]:
                    base_score += 0.4
                
                # Kinesthetic learners prefer interactive content
                elif learning_style == "kinesthetic" and content_type in ["interactive", "activity", "quiz"]:
                    base_score += 0.4
            
            # FACTOR 2: Grade level appropriateness
            if user.grade_level and content.grade_level:
                # Check if the user's grade level is in the content's target grade levels
                if user.grade_level in content.grade_level:
                    base_score += 0.3
                # Small bonus for content targeted at adjacent grade levels
                elif (user.grade_level - 1) in content.grade_level or (user.grade_level + 1) in content.grade_level:
                    base_score += 0.1
            
            # FACTOR 3: Subject interest alignment
            if user.subjects_of_interest:
                # Major bonus if content matches a specific interest
                if content.subject in user.subjects_of_interest:
                    base_score += 0.3
                
                # Check if any of the user's interests appear in the content topics
                for interest in user.subjects_of_interest:
                    if any(interest.lower() in topic.lower() for topic in content.topics):
                        base_score += 0.2
                        break
            
            # FACTOR 4: Content freshness
            if hasattr(content, "created_at"):
                # Small bonus for newer content (if created_at is available)
                try:
                    content_date = content.created_at
                    current_date = datetime.utcnow()
                    if (current_date - content_date).days < 180:  # Less than 6 months old
                        base_score += 0.1
                except (TypeError, AttributeError):
                    pass
            
            # FACTOR 5: Content engagement (duration)
            if content.duration_minutes:
                # Prefer content of appropriate duration based on grade
                if user.grade_level:
                    if user.grade_level <= 5:  # Elementary
                        # Younger students need shorter content
                        if 5 <= content.duration_minutes <= 15:
                            base_score += 0.2
                        elif content.duration_minutes > 30:
                            base_score -= 0.2
                    elif user.grade_level <= 8:  # Middle school
                        if 10 <= content.duration_minutes <= 25:
                            base_score += 0.2
                        elif content.duration_minutes > 45:
                            base_score -= 0.1
                    else:  # High school
                        if 15 <= content.duration_minutes <= 45:
                            base_score += 0.2
            
            # FACTOR 6: Difficulty level appropriateness
            if user.grade_level:
                # Match difficulty to grade level
                difficulty = content.difficulty_level.value
                if user.grade_level <= 5:  # Elementary
                    if difficulty == "beginner":
                        base_score += 0.3
                    elif difficulty == "advanced":
                        base_score -= 0.2
                elif user.grade_level <= 8:  # Middle school
                    if difficulty == "intermediate":
                        base_score += 0.3
                    elif difficulty == "advanced" and user.grade_level < 7:
                        base_score -= 0.1
                else:  # High school
                    if difficulty in ["intermediate", "advanced"]:
                        base_score += 0.3
                    elif difficulty == "beginner" and user.grade_level > 10:
                        base_score -= 0.1
            
            return base_score
        
        # Score and rank content items
        scored_items = [(item, score_content(item)) for item in content_items]
        ranked_items = [item for item, score in sorted(scored_items, key=lambda x: x[1], reverse=True)]
        
        # Add diversity - ensure we have a mix of content types in the top results
        # This prevents all recommendations being the same type
        diversified_results = []
        content_type_counts = {}
        
        # First, add one of each content type to ensure diversity
        for item in ranked_items:
            content_type = item.content_type.value
            if content_type not in content_type_counts:
                content_type_counts[content_type] = 1
                diversified_results.append(item)
                
                # Once we've added one of each available type, break
                if len(content_type_counts) >= min(5, len(set(c.content_type.value for c in content_items))):
                    break
        
        # Then, fill in with the highest-ranked remaining items
        remaining_slots = min(len(content_items), 10) - len(diversified_results)
        if remaining_slots > 0:
            # Get items not already in the diversified results
            remaining_items = [item for item in ranked_items if item not in diversified_results]
            diversified_results.extend(remaining_items[:remaining_slots])
        
        return diversified_results
    
    async def get_content_by_id(self, content_id: str) -> Optional[Content]:
        """Get content by ID."""
        if not self.search_client:
            await self.initialize()
        
        try:
            result = await self.search_client.get_document(key=content_id)
            
            if result:
                content_dict = dict(result)
                # Convert to proper enum types for model
                content_dict["content_type"] = ContentType(content_dict["content_type"])
                content_dict["difficulty_level"] = DifficultyLevel(content_dict["difficulty_level"])
                return Content(**content_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting content by ID: {e}")
            return None
    
    async def get_content_by_topics(
        self, 
        topics: List[str], 
        grade_level: Optional[int] = None,
        difficulty_level: Optional[str] = None,
        limit: int = 5
    ) -> List[Content]:
        """
        Get content by specific topics with additional filtering.
        
        Args:
            topics: List of topics to search for
            grade_level: Optional grade level filter
            difficulty_level: Optional difficulty level
            limit: Maximum items to return
            
        Returns:
            List of content items matching the topics
        """
        if not self.search_client:
            await self.initialize()
            
        try:
            # Build filter for topics
            topic_filters = []
            for topic in topics:
                topic_filters.append(f"topics/any(t: t eq '{topic}')")
                
            filter_expression = f"({' or '.join(topic_filters)})"
            
            # Add grade level filter if specified
            if grade_level:
                filter_expression += f" and grade_level/any(g: g eq {grade_level})"
                
            # Add difficulty level filter if specified
            if difficulty_level:
                filter_expression += f" and difficulty_level eq '{difficulty_level}'"
                
            # Execute search
            results = await self.search_client.search(
                search_text="*",
                filter=filter_expression,
                select=["id", "title", "description", "subject", "content_type", 
                        "difficulty_level", "grade_level", "topics", "url", 
                        "duration_minutes", "keywords", "source"],
                top=limit
            )
            
            # Convert to Content objects
            content_items = []
            async for result in results:
                content_dict = dict(result)
                # Convert to proper enum types for model
                content_dict["content_type"] = ContentType(content_dict["content_type"])
                content_dict["difficulty_level"] = DifficultyLevel(content_dict["difficulty_level"])
                content_items.append(Content(**content_dict))
                
            return content_items
            
        except Exception as e:
            logger.error(f"Error getting content by topics: {e}")
            return []
    
    async def get_similar_content(self, content_id: str, limit: int = 5) -> List[Content]:
        """
        Get content similar to a specified item based on embeddings.
        
        Args:
            content_id: ID of the content to find similar items for
            limit: Maximum number of similar items to return
            
        Returns:
            List of similar content items
        """
        if not self.search_client:
            await self.initialize()
            
        try:
            # Get the source content item
            source_content = await self.get_content_by_id(content_id)
            if not source_content:
                logger.error(f"Content item {content_id} not found")
                return []
                
            # Get embedding for the item
            source_embedding = None
            try:
                # Try to get the embedding from the item
                result = await self.search_client.get_document(key=content_id)
                if result and "embedding" in result:
                    source_embedding = result["embedding"]
            except Exception:
                pass
                
            # If no embedding found, generate one
            if not source_embedding:
                # Create text representation for embedding
                text_for_embedding = (
                    f"{source_content.title} {source_content.description} "
                    f"{' '.join(source_content.topics)}"
                )
                source_embedding = await self._generate_embedding(text_for_embedding)
                
            # Create vector query
            vector_query = Vector(
                value=source_embedding,
                k=limit + 1,  # +1 to account for the source document
                fields="embedding",
                exhaustive=True
            )
            
            # Build filter to exclude the source document and match subject
            filter_expression = f"id ne '{content_id}'"
            if source_content.subject:
                filter_expression += f" and subject eq '{source_content.subject}'"
                
            # Execute the search
            results = await self.search_client.search(
                search_text=None,
                vectors=[vector_query],
                filter=filter_expression,
                select=["id", "title", "description", "subject", "content_type", 
                        "difficulty_level", "grade_level", "topics", "url", 
                        "duration_minutes", "keywords", "source"],
                top=limit
            )
            
            # Convert to Content objects
            content_items = []
            async for result in results:
                content_dict = dict(result)
                # Convert to proper enum types for model
                content_dict["content_type"] = ContentType(content_dict["content_type"])
                content_dict["difficulty_level"] = DifficultyLevel(content_dict["difficulty_level"])
                content_items.append(Content(**content_dict))
                
            return content_items
            
        except Exception as e:
            logger.error(f"Error getting similar content: {e}")
            return []
    
    async def get_learning_progression(
        self, 
        subject: str, 
        topic: str, 
        start_grade: int,
        end_grade: int,
        limit_per_grade: int = 3
    ) -> Dict[int, List[Content]]:
        """
        Get content that forms a learning progression across grade levels.
        Useful for creating sequential learning paths.
        
        Args:
            subject: Subject area
            topic: Specific topic
            start_grade: Starting grade level
            end_grade: Ending grade level
            limit_per_grade: Maximum content items per grade level
            
        Returns:
            Dictionary mapping grade levels to content lists
        """
        if not self.search_client:
            await self.initialize()
            
        result = {}
        
        try:
            # Build the base filter for subject and topic
            base_filter = f"subject eq '{subject}' and topics/any(t: t eq '{topic}')"
            
            # Query for each grade level in the range
            for grade in range(start_grade, end_grade + 1):
                # Add grade filter
                grade_filter = f"{base_filter} and grade_level/any(g: g eq {grade})"
                
                # Execute search for this grade
                results = await self.search_client.search(
                    search_text="*",
                    filter=grade_filter,
                    select=["id", "title", "description", "subject", "content_type", 
                            "difficulty_level", "grade_level", "topics", "url", 
                            "duration_minutes", "keywords", "source"],
                    top=limit_per_grade
                )
                
                # Convert to Content objects
                grade_items = []
                async for item in results:
                    content_dict = dict(item)
                    # Convert to proper enum types for model
                    content_dict["content_type"] = ContentType(content_dict["content_type"])
                    content_dict["difficulty_level"] = DifficultyLevel(content_dict["difficulty_level"])
                    grade_items.append(Content(**content_dict))
                
                # Add to result if items found
                if grade_items:
                    result[grade] = grade_items
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting learning progression: {e}")
            return {}
    
    async def get_recommendations_by_learning_style(
        self,
        user: User,
        subject: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, List[Content]]:
        """
        Get recommendations grouped by content types that match the user's learning style.
        
        Args:
            user: User to get recommendations for
            subject: Optional subject filter
            limit: Maximum number of recommendations
            
        Returns:
            Dictionary mapping content types to content lists
        """
        if not self.search_client:
            await self.initialize()
            
        try:
            # Get user's learning style
            learning_style = user.learning_style.value if user.learning_style else "mixed"
            
            # Determine content types to prioritize based on learning style
            priority_types = []
            if learning_style == "visual":
                priority_types = ["video", "interactive"]
            elif learning_style == "auditory":
                priority_types = ["video", "audio", "podcast"]
            elif learning_style == "reading_writing":
                priority_types = ["article", "worksheet", "lesson"]
            elif learning_style == "kinesthetic":
                priority_types = ["interactive", "activity", "quiz"]
            else:  # mixed or unknown
                priority_types = ["video", "article", "interactive", "lesson", "quiz"]
                
            # Get regular recommendations
            all_recommendations = await self.get_personalized_recommendations(
                user=user,
                subject=subject,
                limit=limit * 2  # Get more to have enough to categorize
            )
            
            # Group by content type
            result = {}
            for content_type in priority_types:
                # Filter to matching content type
                matching_items = [item for item in all_recommendations 
                                 if item.content_type.value == content_type]
                
                # Add to result if items found (limited to what was requested)
                if matching_items:
                    result[content_type] = matching_items[:limit // len(priority_types) + 1]
            
            # Add "other" category for any remaining types
            other_types = [item for item in all_recommendations 
                          if item.content_type.value not in priority_types]
            
            if other_types:
                result["other"] = other_types[:limit // 4]  # Limit the "other" category
                
            return result
            
        except Exception as e:
            logger.error(f"Error getting recommendations by learning style: {e}")
            return {}

# Singleton instance
recommendation_service = None

async def get_recommendation_service():
    """Get or create recommendation service singleton."""
    global recommendation_service
    if recommendation_service is None:
        recommendation_service = RecommendationService()
        await recommendation_service.initialize()
    return recommendation_service