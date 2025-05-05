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

class EnhancedRecommendationService:
    """
    Enhanced service for generating content recommendations leveraging multimedia content.
    Uses Azure AI Search with vector search for semantic matching.
    """
    
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
        content_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Content]:
        """
        Get personalized content recommendations for a user using Azure AI Search.
        
        Args:
            user: User to get recommendations for
            subject: Optional subject filter
            content_type: Optional content type filter (video, audio, article, etc.)
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended content items
        """
        if not self.search_client:
            await self.initialize()
        
        try:
            # Generate a query based on user profile and learning style
            query_text = self._generate_query_text(user, subject, content_type)
            
            # Generate embedding for the query
            query_embedding = await self._generate_embedding(query_text)
            
            # Build filter based on user, subject, and content type
            filter_expression = self._build_filter_expression(user, subject, content_type)
            
            # Create the vector query for semantic search
            vector_query = Vector(
                value=query_embedding,
                k=limit * 2,  # Request more items than needed to allow for filtering
                fields="embedding",
                exhaustive=True
            )
            
            # Execute the search with vector and filtering
            results = await self.search_client.search(
                search_text=None,
                vectors=[vector_query],
                filter=filter_expression,
                select=[
                    "id", "title", "description", "subject", "content_type", 
                    "difficulty_level", "grade_level", "topics", "url", 
                    "duration_minutes", "keywords", "source", "metadata"
                ],
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
            
            # Apply additional filtering and ranking
            ranked_items = self._rank_recommendations(content_items, user)
            
            # Return only the requested number of recommendations
            return ranked_items[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            # Return empty list on error
            return []
    
    async def get_content_by_media_type(
        self,
        media_type: str,
        subject: Optional[str] = None,
        limit: int = 10
    ) -> List[Content]:
        """
        Get content of a specific media type (video, audio, text)
        
        Args:
            media_type: Type of media to retrieve (video, audio, text)
            subject: Optional subject filter
            limit: Maximum number of items to return
            
        Returns:
            List of content items matching the specified media type
        """
        if not self.search_client:
            await self.initialize()
        
        try:
            # Map the media type to the corresponding content types
            content_type_filter = None
            if media_type.lower() == "video":
                content_type_filter = "content_type eq 'video'"
            elif media_type.lower() == "audio":
                content_type_filter = "content_type eq 'audio'"
            elif media_type.lower() == "text":
                content_type_filter = "(content_type eq 'article' or content_type eq 'worksheet')"
            elif media_type.lower() == "interactive":
                content_type_filter = "(content_type eq 'interactive' or content_type eq 'quiz' or content_type eq 'activity')"
            else:
                # Invalid media type
                logger.warning(f"Invalid media type: {media_type}")
                return []
            
            # Add subject filter if specified
            filter_expression = content_type_filter
            if subject:
                filter_expression += f" and subject eq '{subject}'"
            
            # Execute search
            results = await self.search_client.search(
                search_text="*",
                filter=filter_expression,
                select=[
                    "id", "title", "description", "subject", "content_type", 
                    "difficulty_level", "grade_level", "topics", "url", 
                    "duration_minutes", "keywords", "source", "metadata"
                ],
                top=limit
            )
            
            # Convert results to Content objects
            content_items = []
            async for result in results:
                try:
                    content_dict = dict(result)
                    content_dict["content_type"] = ContentType(content_dict["content_type"])
                    content_dict["difficulty_level"] = DifficultyLevel(content_dict["difficulty_level"])
                    content_items.append(Content(**content_dict))
                except Exception as e:
                    logger.warning(f"Error converting search result to Content: {e}")
            
            return content_items
            
        except Exception as e:
            logger.error(f"Error getting content by media type: {e}")
            return []
    
    async def analyze_content_metadata(self, content_id: str) -> Dict[str, Any]:
        """
        Analyze content metadata for a specific content item.
        Useful for understanding what data is available for recommendation.
        
        Args:
            content_id: ID of the content to analyze
            
        Returns:
            Dictionary with metadata analysis
        """
        if not self.search_client:
            await self.initialize()
        
        try:
            # Get the content item
            result = await self.search_client.get_document(key=content_id)
            
            if not result:
                logger.error(f"Could not find content with ID {content_id}")
                return {"error": "Content not found"}
            
            content_dict = dict(result)
            
            # Extract and analyze metadata
            analysis = {
                "id": content_id,
                "title": content_dict.get("title", "Unknown"),
                "content_type": content_dict.get("content_type", "Unknown"),
                "has_embedding": "embedding" in content_dict,
                "metadata_available": {}
            }
            
            # Check what metadata is available
            metadata = content_dict.get("metadata", {})
            
            # Content text/transcription
            if metadata.get("content_text"):
                analysis["metadata_available"]["content_text"] = {
                    "available": True,
                    "length": len(metadata["content_text"]),
                    "sample": metadata["content_text"][:100] + "..." if len(metadata["content_text"]) > 100 else metadata["content_text"]
                }
            
            if metadata.get("transcription"):
                analysis["metadata_available"]["transcription"] = {
                    "available": True,
                    "length": len(metadata["transcription"]),
                    "sample": metadata["transcription"][:100] + "..." if len(metadata["transcription"]) > 100 else metadata["transcription"]
                }
            
            # Thumbnail
            if metadata.get("thumbnail_url"):
                analysis["metadata_available"]["thumbnail"] = {
                    "available": True,
                    "url": metadata["thumbnail_url"]
                }
            
            # Other metadata
            for key, value in metadata.items():
                if key not in ["content_text", "transcription", "thumbnail_url"]:
                    analysis["metadata_available"][key] = {
                        "available": True,
                        "type": type(value).__name__,
                        "sample": str(value)[:100] + "..." if isinstance(value, str) and len(value) > 100 else value
                    }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing content metadata: {e}")
            return {"error": str(e)}

# Singleton instance
recommendation_service = None

async def get_recommendation_service():
    """Get or create recommendation service singleton."""
    global recommendation_service
    if recommendation_service is None:
        recommendation_service = EnhancedRecommendationService()
        await recommendation_service.initialize()
    return recommendation_service
    
    def _generate_query_text(self, user: User, subject: Optional[str] = None, content_type: Optional[str] = None) -> str:
        """
        Generate query text for embedding based on user profile, subject, and content type.
        
        Args:
            user: The user to generate recommendations for
            subject: Optional subject filter
            content_type: Optional content type filter
            
        Returns:
            Query text for generating embeddings
        """
        grade_level = str(user.grade_level) if user.grade_level else "any"
        learning_style = user.learning_style.value if user.learning_style else "mixed"
        interests = ", ".join(user.subjects_of_interest) if user.subjects_of_interest else "general learning"
        
        # Build query with user information
        query = f"Educational content for a student in grade {grade_level} "
        query += f"with a {learning_style} learning style. "
        query += f"Interested in {interests}. "
        
        # Add subject if specified
        if subject:
            query += f"Looking specifically for {subject} content. "
        
        # Add content type preference based on learning style and explicit request
        if content_type:
            query += f"Preferred content type: {content_type}. "
        else:
            # Suggest content type based on learning style if not explicitly requested
            if learning_style == "visual":
                query += f"Prefer visual content like videos and interactive resources. "
            elif learning_style == "auditory":
                query += f"Prefer audio content like podcasts and video lectures. "
            elif learning_style == "reading_writing":
                query += f"Prefer text-based content like articles and worksheets. "
            elif learning_style == "kinesthetic":
                query += f"Prefer interactive content and activities. "
        
        return query
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding using OpenAI adapter.
        
        Args:
            text: Text to embed
            
        Returns:
            Vector embedding
        """
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
    
    def _build_filter_expression(self, user: User, subject: Optional[str] = None, content_type: Optional[str] = None) -> str:
        """
        Build OData filter expression for Azure AI Search.
        
        Args:
            user: The user to filter for
            subject: Optional subject filter
            content_type: Optional content type filter
            
        Returns:
            OData filter expression
        """
        filters = []
        
        # Add subject filter if specified
        if subject:
            filters.append(f"subject eq '{subject}'")
        
        # Add content type filter if specified
        if content_type:
            filters.append(f"content_type eq '{content_type}'")
        
        # Add grade level filter based on user's grade
        if user.grade_level:
            # Include content for this grade level, one below, and one above
            grade_filters = [
                f"grade_level/any(g: g eq {user.grade_level})",
                f"grade_level/any(g: g eq {user.grade_level - 1})",
                f"grade_level/any(g: g eq {user.grade_level + 1})"
            ]
            filters.append(f"({' or '.join(grade_filters)})")
        
        # Filter for difficulty level based on user's grade
        if user.grade_level:
            if user.grade_level <= 6:
                filters.append("(difficulty_level eq 'beginner' or difficulty_level eq 'intermediate')")
            elif user.grade_level <= 9:
                filters.append("difficulty_level eq 'intermediate'")
            else:
                filters.append("(difficulty_level eq 'intermediate' or difficulty_level eq 'advanced')")
        
        # Combine all filters with AND
        if filters:
            return " and ".join(filters)
        
        return None
    
    def _rank_recommendations(self, content_items: List[Content], user: User) -> List[Content]:
        """
        Apply custom ranking to content items based on user profile.
        
        Args:
            content_items: List of content items from search
            user: User to rank for
            
        Returns:
            Ranked list of content items
        """
        if not content_items:
            return []
        
        # Create a scoring function based on learning style and content type
        def score_content(content: Content) -> float:
            base_score = 1.0  # Start with base score
            
            # Bonus for matching user's learning style
            if user.learning_style:
                learning_style = user.learning_style.value
                content_type = content.content_type.value
                
                # Visual learners prefer videos and visual content
                if learning_style == "visual" and content_type in ["video", "interactive"]:
                    base_score += 0.3
                
                # Auditory learners prefer audio content
                elif learning_style == "auditory" and content_type in ["video", "audio", "podcast"]:
                    base_score += 0.3
                
                # Reading/writing learners prefer text content
                elif learning_style == "reading_writing" and content_type in ["article", "worksheet"]:
                    base_score += 0.3
                
                # Kinesthetic learners prefer interactive content
                elif learning_style == "kinesthetic" and content_type in ["interactive", "activity"]:
                    base_score += 0.3
            
            # Bonus for having transcription for video/audio content
            if content.content_type.value in ["video", "audio"] and hasattr(content, "metadata"):
                metadata = getattr(content, "metadata", {})
                if metadata and metadata.get("transcription"):
                    base_score += 0.2
            
            # Bonus for duration appropriate for the user's grade level
            # Younger students generally need shorter content
            if user.grade_level and content.duration_minutes:
                if user.grade_level <= 5:  # Elementary
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
            
            # Bonus for content in user's subjects of interest
            if user.subjects_of_interest and content.subject in user.subjects_of_interest:
                base_score += 0.2
            
            return base_score
        
        # Score and rank content items
        scored_items = [(item, score_content(item)) for item in content_items]
        ranked_items = [item for item, score in sorted(scored_items, key=lambda x: x[1], reverse=True)]
        
        return ranked_items
    
    async def get_recommendations_by_type(
        self,
        user: User,
        subject: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, List[Content]]:
        """
        Get recommendations organized by content type.
        
        Args:
            user: User to get recommendations for
            subject: Optional subject filter
            limit: Maximum recommendations per type
            
        Returns:
            Dictionary of content type to list of content items
        """
        if not self.search_client:
            await self.initialize()
        
        organized_recommendations = {}
        
        # First, get general recommendations
        general_recs = await self.get_personalized_recommendations(
            user=user,
            subject=subject,
            limit=limit * 3  # Get more to distribute among types
        )
        
        # Organize by content type
        for content in general_recs:
            content_type = content.content_type.value
            if content_type not in organized_recommendations:
                organized_recommendations[content_type] = []
            
            # Add if we haven't reached the limit yet
            if len(organized_recommendations[content_type]) < limit:
                organized_recommendations[content_type].append(content)
        
        # Ensure we have recommendations for key content types
        key_types = ["video", "audio", "article", "interactive", "worksheet"]
        
        for content_type in key_types:
            # If we don't have enough of this type, get more specific recommendations
            if content_type not in organized_recommendations or len(organized_recommendations[content_type]) < limit:
                specific_recs = await self.get_personalized_recommendations(
                    user=user,
                    subject=subject,
                    content_type=content_type,
                    limit=limit
                )
                
                # Create or append to the list
                if content_type not in organized_recommendations:
                    organized_recommendations[content_type] = []
                
                # Add unique items up to the limit
                existing_ids = {item.id for item in organized_recommendations[content_type]}
                for item in specific_recs:
                    if item.id not in existing_ids and len(organized_recommendations[content_type]) < limit:
                        organized_recommendations[content_type].append(item)
                        existing_ids.add(item.id)
        
        return organized_recommendations
    
    async def get_similar_content(self, content_id: str, limit: int = 5) -> List[Content]:
        """
        Get content similar to a specified content item.
        
        Args:
            content_id: ID of the content to find similar items for
            limit: Maximum number of similar items to return
            
        Returns:
            List of similar content items
        """
        if not self.search_client:
            await self.initialize()
        
        try:
            # First, get the content item we're finding similar content for
            result = await self.search_client.get_document(key=content_id)
            
            if not result:
                logger.error(f"Could not find content with ID {content_id}")
                return []
            
            content_dict = dict(result)
            
            # Use its embedding to find similar content
            if "embedding" not in content_dict:
                logger.warning(f"Content item {content_id} does not have embedding. Generating embedding from content.")
                # Generate embedding from content
                text_for_embedding = f"{content_dict.get('title', '')} {content_dict.get('subject', '')} "
                text_for_embedding += content_dict.get('description', '')
                
                embedding = await self._generate_embedding(text_for_embedding)
            else:
                embedding = content_dict["embedding"]
            
            # Create filter to exclude the current content item
            filter_expression = f"id ne '{content_id}'"
            
            # Add subject filter to get related content in the same subject
            subject = content_dict.get("subject")
            if subject:
                filter_expression += f" and subject eq '{subject}'"
            
            # Create the vector query
            vector_query = Vector(
                value=embedding,
                k=limit,
                fields="embedding",
                exhaustive=True
            )
            
            # Execute the search
            results = await self.search_client.search(
                search_text=None,
                vectors=[vector_query],
                filter=filter_expression,
                select=[
                    "id", "title", "description", "subject", "content_type", 
                    "difficulty_level", "grade_level", "topics", "url", 
                    "duration_minutes", "keywords", "source", "metadata"
                ],
                top=limit
            )
            
            # Convert results to Content objects
            similar_items = []
            async for result in results:
                try:
                    similar_dict = dict(result)
                    similar_dict["content_type"] = ContentType(similar_dict["content_type"])
                    similar_dict["difficulty_level"] = DifficultyLevel(similar_dict["difficulty_level"])
                    similar_items.append(Content(**similar_dict))
                except Exception as e:
                    logger.warning(f"Error converting search result to Content: {e}")
            
            return similar_items
            
        except Exception as e:
            logger.error(f"Error getting similar content: {e}")
            return []