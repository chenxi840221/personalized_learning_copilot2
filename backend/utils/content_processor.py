# Content Processor (content_processor.py)
# ./personalized_learning_copilot/backend/utils/content_processor.py
import logging
from typing import List, Dict, Any, Optional, Tuple
import re
from bs4 import BeautifulSoup
import asyncio
import aiohttp
from datetime import datetime
from models.content import Content, ContentType, DifficultyLevel
from config.settings import Settings
# Initialize settings
settings = Settings()
# Initialize logger
logger = logging.getLogger(__name__)
class ContentProcessor:
    """
    Process educational content for indexing and retrieval.
    """
    def __init__(self):
        """Initialize the content processor."""
        # HTTP session for content fetching
        self.session = None
    async def initialize(self):
        """Initialize HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": settings.USER_AGENT}
            )
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    async def process_url(self, url: str) -> Tuple[str, Dict[str, Any]]:
        """
        Fetch and process content from a URL.
        Args:
            url: URL to fetch
        Returns:
            Tuple of (HTML content, metadata)
        """
        await self.initialize()
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch {url}: {response.status}")
                    raise Exception(f"Failed to fetch URL: {response.status}")
                html = await response.text()
                # Extract metadata
                metadata = self._extract_metadata(html, url)
                return html, metadata
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            raise
    def _extract_metadata(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract metadata from HTML content.
        Args:
            html: HTML content
            url: Source URL
        Returns:
            Extracted metadata
        """
        soup = BeautifulSoup(html, "html.parser")
        metadata = {
            "url": url,
            "title": None,
            "description": None,
            "keywords": [],
            "fetch_time": datetime.utcnow().isoformat()
        }
        # Extract title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.text.strip()
        # Extract meta description
        description_tag = soup.find("meta", attrs={"name": "description"})
        if description_tag and "content" in description_tag.attrs:
            metadata["description"] = description_tag["content"].strip()
        # Extract meta keywords
        keywords_tag = soup.find("meta", attrs={"name": "keywords"})
        if keywords_tag and "content" in keywords_tag.attrs:
            keywords = keywords_tag["content"].split(",")
            metadata["keywords"] = [k.strip() for k in keywords if k.strip()]
        return metadata
    def extract_content_type(self, html: str, url: str) -> ContentType:
        """
        Determine content type based on HTML and URL.
        Args:
            html: HTML content
            url: Source URL
        Returns:
            Determined content type
        """
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text().lower()
        url_lower = url.lower()
        # Check for specific content type indicators
        if any(word in text for word in ["quiz", "test", "assessment"]) or "quiz" in url_lower:
            return ContentType.QUIZ
        elif any(word in text for word in ["video", "watch", "tutorial"]) or "video" in url_lower:
            return ContentType.VIDEO
        elif any(word in text for word in ["worksheet", "practice", "exercise"]) or "worksheet" in url_lower:
            return ContentType.WORKSHEET
        elif any(word in text for word in ["interactive", "game", "simulation"]) or "interactive" in url_lower:
            return ContentType.INTERACTIVE
        elif any(word in text for word in ["lesson", "lecture", "class"]) or "lesson" in url_lower:
            return ContentType.LESSON
        elif any(word in text for word in ["activity", "project", "lab"]) or "activity" in url_lower:
            return ContentType.ACTIVITY
        else:
            return ContentType.ARTICLE
    def determine_difficulty_level(self, text: str, subject: str) -> Tuple[DifficultyLevel, List[int]]:
        """
        Determine difficulty level and grade level range for content.
        Args:
            text: Content text
            subject: Content subject
        Returns:
            Tuple of (difficulty level, grade levels)
        """
        text = text.lower()
        # Check for explicit difficulty indicators
        if any(word in text for word in ["basic", "beginner", "elementary", "introduction", "easy"]):
            difficulty = DifficultyLevel.BEGINNER
            grade_levels = [3, 4, 5]
        elif any(word in text for word in ["advanced", "complex", "difficult", "challenging", "college"]):
            difficulty = DifficultyLevel.ADVANCED
            grade_levels = [9, 10, 11, 12]
        else:
            difficulty = DifficultyLevel.INTERMEDIATE
            grade_levels = [6, 7, 8]
        # Look for grade level indicators
        grade_matches = re.findall(r'grade\s+(\d+)', text) or re.findall(r'year\s+(\d+)', text)
        if grade_matches:
            try:
                grade = int(grade_matches[0])
                if 1 <= grade <= 12:
                    if grade <= 5:
                        difficulty = DifficultyLevel.BEGINNER
                        grade_levels = list(range(max(1, grade - 1), min(12, grade + 2)))
                    elif grade <= 8:
                        difficulty = DifficultyLevel.INTERMEDIATE
                        grade_levels = list(range(max(1, grade - 1), min(12, grade + 2)))
                    else:
                        difficulty = DifficultyLevel.ADVANCED
                        grade_levels = list(range(max(1, grade - 1), min(12, grade + 2)))
            except ValueError:
                pass
        # Subject-specific adjustments
        if subject.lower() == "mathematics":
            if any(term in text for term in ["calculus", "trigonometry", "algebra 2"]):
                difficulty = DifficultyLevel.ADVANCED
                grade_levels = [9, 10, 11, 12]
            elif any(term in text for term in ["algebra", "geometry", "pre-algebra"]):
                difficulty = DifficultyLevel.INTERMEDIATE
                grade_levels = [6, 7, 8, 9]
            elif any(term in text for term in ["fraction", "decimal", "arithmetic"]):
                difficulty = DifficultyLevel.BEGINNER
                grade_levels = [3, 4, 5, 6]
        return difficulty, grade_levels
    async def extract_and_save_content(self, url: str, subject: str) -> Content:
        """
        Fetch, process, and save content from a URL.
        Args:
            url: URL to fetch
            subject: Subject of the content
        Returns:
            Saved Content object
        """
        try:
            # Fetch and process URL
            html, metadata = await self.process_url(url)
            # Extract text
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text()
            # Determine content properties
            title = metadata.get("title") or "Untitled Content"
            description = metadata.get("description") or self._generate_description(text)
            content_type = self.extract_content_type(html, url)
            difficulty_level, grade_levels = self.determine_difficulty_level(text, subject)
            # Extract topics
            topics = self._extract_topics(text, subject)
            # Extract keywords
            keywords = metadata.get("keywords") or self._extract_keywords(text)
            # Create content object
            content = Content(
                title=title,
                description=description,
                content_type=content_type,
                subject=subject,
                topics=topics,
                url=url,
                source="ABC Education",
                difficulty_level=difficulty_level,
                grade_level=grade_levels,
                duration_minutes=self._estimate_duration(content_type),
                keywords=keywords
            )
            # Save to database
            db = 
            result = await db.contents.insert_one(content.dict())
            # Get the saved content
            saved_content = await db.contents.find_one({"_id": result.inserted_id})
            return Content(**saved_content)
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            raise
    def _generate_description(self, text: str) -> str:
        """Generate a brief description from content text."""
        # Take first 500 characters and truncate at the last period
        description = text[:500].strip()
        last_period = description.rfind('.')
        if last_period > 100:  # Ensure we have a reasonable description length
            description = description[:last_period + 1]
        return description
    def _extract_topics(self, text: str, subject: str) -> List[str]:
        """Extract relevant topics from content text."""
        # This would ideally use NLP or a taxonomy
        # For simplicity, we'll just extract some common topics per subject
        topics = []
        text_lower = text.lower()
        subject_topics = {
            "Mathematics": ["Algebra", "Geometry", "Statistics", "Calculus", "Arithmetic", 
                           "Numbers", "Fractions", "Equations", "Probability", "Functions"],
            "Science": ["Biology", "Chemistry", "Physics", "Earth Science", "Astronomy",
                       "Ecology", "Genetics", "Elements", "Energy", "Matter"],
            "English": ["Grammar", "Literature", "Writing", "Reading", "Poetry",
                       "Fiction", "Non-fiction", "Vocabulary", "Comprehension", "Analysis"]
        }
        # Get the possible topics for this subject
        possible_topics = subject_topics.get(subject, [])
        # Check which topics appear in the text
        for topic in possible_topics:
            if topic.lower() in text_lower:
                topics.append(topic)
        # Return at least one topic
        if not topics and possible_topics:
            topics = [possible_topics[0]]  # Default to first topic
        return topics
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from content text."""
        # Simple keyword extraction - in production, use NLP techniques
        words = re.findall(r'\b[a-zA-Z]{4,15}\b', text.lower())
        # Remove common words
        stopwords = {'about', 'above', 'after', 'again', 'against', 'all', 'and', 'any', 'are', 'because',
                    'been', 'before', 'being', 'below', 'between', 'both', 'but', 'cannot', 'could', 'did',
                    'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'has',
                    'have', 'having', 'here', 'how', 'into', 'just', 'more', 'most', 'not', 'now', 'off',
                    'once', 'only', 'other', 'out', 'over', 'own', 'same', 'should', 'some', 'such', 'than',
                    'that', 'the', 'then', 'there', 'these', 'they', 'this', 'those', 'through', 'too', 'under',
                    'until', 'very', 'was', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom',
                    'why', 'will', 'with', 'would', 'you', 'your'}
        # Filter words and count frequencies
        word_count = {}
        for word in words:
            if word not in stopwords:
                word_count[word] = word_count.get(word, 0) + 1
        # Get top keywords
        keywords = sorted(word_count.keys(), key=lambda k: word_count[k], reverse=True)[:10]
        return keywords
    def _estimate_duration(self, content_type: ContentType) -> int:
        """Estimate content duration in minutes based on content type."""
        duration_map = {
            ContentType.VIDEO: 15,
            ContentType.ARTICLE: 10,
            ContentType.INTERACTIVE: 20,
            ContentType.QUIZ: 10,
            ContentType.WORKSHEET: 30,
            ContentType.LESSON: 45,
            ContentType.ACTIVITY: 30
        }
        return duration_map.get(content_type, 15)
# Singleton instance
content_processor = None
async def get_content_processor():
    """Get or create the content processor singleton."""
    global content_processor
    if content_processor is None:
        content_processor = ContentProcessor()
        await content_processor.initialize()
    return content_processor