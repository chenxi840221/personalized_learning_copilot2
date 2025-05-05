# backend/scrapers/content_extractor.py
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import re
import uuid
import json
import os
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

# Playwright imports for browser automation
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Setup path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import necessary components, with fallbacks for testing
try:
    # Import the multimedia content processor
    from utils.multimedia_content_processor import get_content_processor, process_and_index_content
    
    # Import models and settings
    from models.content import Content, ContentType, DifficultyLevel
    from config.settings import Settings
    
    # Initialize settings
    settings = Settings()
except ImportError:
    # Fallback ContentType enum for testing
    class ContentType:
        ARTICLE = "article"
        VIDEO = "video"
        AUDIO = "audio"
        INTERACTIVE = "interactive"
        WORKSHEET = "worksheet"
        QUIZ = "quiz"
        LESSON = "lesson"
        ACTIVITY = "activity"
    
    # Fallback DifficultyLevel enum for testing
    class DifficultyLevel:
        BEGINNER = "beginner"
        INTERMEDIATE = "intermediate"
        ADVANCED = "advanced"
    
    # Mock process_and_index_content function
    async def process_and_index_content(url, content_info):
        return content_info

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('content_extractor.log')
    ]
)

logger = logging.getLogger(__name__)

class EducationContentExtractor:
    """Extracts detailed content from educational resource links."""
    
    def __init__(self):
        """Initialize the content extractor."""
        self.browser = None
        self.context = None
        self.page = None
        self.content_processor = None
        
        # Create output directories
        self.output_dir = os.path.join(os.getcwd(), "education_resources")
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.debug_dir = os.path.join(os.getcwd(), "debug_output")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        self.extracted_dir = os.path.join(self.output_dir, "extracted_content")
        os.makedirs(self.extracted_dir, exist_ok=True)
        
        # Common stop words for keyword extraction
        self.stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
            "with", "by", "about", "as", "of", "from", "this", "that", "these", 
            "those", "is", "are", "was", "were", "be", "been", "being", "have", 
            "has", "had", "do", "does", "did", "will", "would", "should", "can", 
            "could", "may", "might", "must", "shall"
        }
    
    async def setup(self, headless=True):
        """Initialize Playwright browser and content processor."""
        logger.info(f"Setting up Playwright browser (headless={headless})...")
        
        # Initialize Playwright
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless, 
            slow_mo=50  # Add slight delay between actions for stability
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        
        self.page = await self.context.new_page()
        
        # Set default timeout (120 seconds)
        self.page.set_default_timeout(120000)
        
        # Try to initialize content processor if available
        try:
            self.content_processor = await get_content_processor()
            logger.info("Content processor initialized")
        except Exception as e:
            logger.warning(f"Content processor not available. Running in extraction mode only: {e}")
    
    async def teardown(self):
        """Close browser and other resources."""
        logger.info("Tearing down browser...")
        
        if self.page:
            await self.page.close()
        
        if self.context:
            await self.context.close()
        
        if self.browser:
            await self.browser.close()
    
    async def save_screenshot(self, name):
        """Save a screenshot for debugging."""
        if self.page:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(self.debug_dir, f"{name}_{timestamp}.png")
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
    
    async def save_html(self, name):
        """Save the current page HTML for debugging."""
        if self.page:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = os.path.join(self.debug_dir, f"{name}_{timestamp}.html")
            html_content = await self.page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"HTML saved to {html_path}")
    
    async def extract_content_details(self, resource: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract detailed content from a resource page.
        
        Args:
            resource: Dictionary with resource title, URL, subject, and age_group
            
        Returns:
            Dictionary with extracted content details
        """
        resource_url = resource["url"]
        resource_title = resource["title"]
        subject_name = resource["subject"]
        age_group = resource.get("age_group", "All Years")  # Default to "All Years" if no age group specified
        
        logger.info(f"Extracting content from: {resource_title[:30]}{'...' if len(resource_title) > 30 else ''}")
        
        # Navigate to the resource page
        await self.page.goto(resource_url, wait_until="networkidle")
        await self.page.wait_for_selector("body", state="visible")
        
        # Take screenshot and save HTML for debugging
        safe_title = resource_title.replace(" ", "_").replace("/", "_")[:30]
        await self.save_screenshot(f"resource_{safe_title}")
        await self.save_html(f"resource_{safe_title}")
        
        # Format dates properly for Azure Search - ISO format with Z suffix
        current_time = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        
        # Extract basic metadata
        metadata = {
            "title": resource_title,
            "url": resource_url,
            "subject": subject_name,
            "age_group": age_group,  # Include age group in metadata
            "source": "ABC Education",
            "id": str(uuid.uuid4()),
            "created_at": current_time,
            "updated_at": current_time
        }
        
        # Extract description
        description = await self._extract_description()
        if description:
            metadata["description"] = description
        else:
            # If no description found, use a generic one
            metadata["description"] = f"Educational resource about {subject_name} for {age_group}"
        
        # Determine content type
        content_type = await self._determine_content_type()
        metadata["content_type"] = content_type.value
        
        # Extract topics
        topics = await self._extract_topics(subject_name)
        metadata["topics"] = topics
        
        # Determine difficulty level and grade levels
        difficulty, grade_levels = self._determine_difficulty_and_grade(
            resource_title, 
            metadata.get("description", ""), 
            subject_name,
            age_group  # Pass age group to improve grade level detection
        )
        metadata["difficulty_level"] = difficulty.value
        metadata["grade_level"] = grade_levels
        
        # Extract duration
        duration = await self._extract_duration()
        if duration:
            metadata["duration_minutes"] = duration
        else:
            # Estimate based on content type
            metadata["duration_minutes"] = self._estimate_duration(content_type)
        
        # Extract keywords
        keywords = self._extract_keywords(
            resource_title, 
            metadata.get("description", "")
        )
        metadata["keywords"] = keywords
        
        # Extract content based on content type
        content_data = {}
        
        if content_type == ContentType.VIDEO:
            video_info = await self._extract_video_content()
            content_data = video_info
            
        elif content_type == ContentType.AUDIO:
            audio_info = await self._extract_audio_content()
            content_data = audio_info
            
        elif content_type in [ContentType.ARTICLE, ContentType.WORKSHEET]:
            article_text = await self._extract_article_text()
            content_data = {"content_text": article_text}
            
        elif content_type in [ContentType.INTERACTIVE, ContentType.ACTIVITY]:
            interactive_info = await self._extract_interactive_content()
            content_data = interactive_info
            
        elif content_type == ContentType.QUIZ:
            quiz_info = await self._extract_quiz_content()
            content_data = quiz_info
            
        # Get current page content for processing
        html_content = await self.page.content()
        content_data["content_html"] = html_content[:2000] + "..." if len(html_content) > 2000 else html_content
        
        # Extract author if available
        author = await self._extract_author()
        if author:
            metadata["author"] = author
        
        # Add content data to metadata
        metadata["metadata"] = content_data
        
        logger.info(f"Extracted content details for: {resource_title[:30]}{'...' if len(resource_title) > 30 else ''}")
        return metadata
    
    async def _extract_description(self) -> Optional[str]:
        """Extract description from the current page."""
        description_selectors = [
            "meta[name='description']",
            ".description",
            ".summary",
            ".content-block-article__summary",
            "p.intro",
            ".intro p",
            "article p:first-of-type"
        ]
        
        for selector in description_selectors:
            if selector.startswith("meta"):
                # Handle meta tags
                meta = await self.page.query_selector(selector)
                if meta:
                    content = await meta.get_attribute("content")
                    if content and content.strip():
                        return content.strip()
            else:
                # Handle regular elements
                elem = await self.page.query_selector(selector)
                if elem:
                    text = await elem.text_content()
                    if text and text.strip():
                        return text.strip()
        
        return None
    
    async def _determine_content_type(self) -> ContentType:
        """Determine the content type of the current page."""
        url = self.page.url
        
        # Check URL for indicators
        if any(video_term in url for video_term in ['/video/', '/watch/', '.mp4', '/iview/']):
            return ContentType.VIDEO
        elif any(audio_term in url for audio_term in ['/audio/', '/podcast/', '.mp3', '/radio/']):
            return ContentType.AUDIO
        elif any(quiz_term in url for quiz_term in ['/quiz/', '/test/', '/assessment/']):
            return ContentType.QUIZ
        elif any(worksheet_term in url for worksheet_term in ['/worksheet/', '/exercise/', '/printable/']):
            return ContentType.WORKSHEET
        elif any(interactive_term in url for interactive_term in ['/interactive/', '/game/', '/simulation/']):
            return ContentType.INTERACTIVE
        elif any(lesson_term in url for lesson_term in ['/lesson/', '/class/', '/course/']):
            return ContentType.LESSON
        elif any(activity_term in url for activity_term in ['/activity/', '/project/', '/lab/']):
            return ContentType.ACTIVITY
        
        # Check for specific elements in the page
        has_video = await self.page.query_selector("video, .video-player, iframe[src*='youtube'], iframe[src*='vimeo']")
        if has_video:
            return ContentType.VIDEO
            
        has_audio = await self.page.query_selector("audio, .audio-player")
        if has_audio:
            return ContentType.AUDIO
            
        has_quiz = await self.page.query_selector(".quiz, .assessment, form[data-quiz]")
        if has_quiz:
            return ContentType.QUIZ
            
        has_interactive = await self.page.query_selector("iframe[src*='interactive'], canvas, .interactive, [data-component-name='Interactive']")
        if has_interactive:
            return ContentType.INTERACTIVE
            
        # Default to article if no specific indicators found
        return ContentType.ARTICLE
    
    async def _extract_topics(self, subject_name: str) -> List[str]:
        """Extract topics from the current page."""
        topics = []
        
        # Look for topic tags
        topic_selectors = [
            ".tag",
            ".topic",
            ".category",
            ".subject",
            "[data-testid='tag']",
            "[data-testid='topic']",
            "meta[name='keywords']"
        ]
        
        for selector in topic_selectors:
            if selector.startswith("meta"):
                # Handle meta tags
                meta = await self.page.query_selector(selector)
                if meta:
                    content = await meta.get_attribute("content")
                    if content:
                        # Split by commas
                        keywords = [k.strip() for k in content.split(",")]
                        topics.extend([k for k in keywords if k])
            else:
                # Handle regular elements
                elems = await self.page.query_selector_all(selector)
                for elem in elems:
                    text = await elem.text_content()
                    if text and text.strip():
                        topics.append(text.strip())
        
        # Clean up and remove duplicates
        unique_topics = list(set(topics))
        
        # Always include the main subject as a topic
        if subject_name not in unique_topics:
            unique_topics.append(subject_name)
        
        return unique_topics
    
    def _determine_difficulty_and_grade(self, title: str, description: str, subject: str, age_group: str = "All Years") -> Tuple[DifficultyLevel, List[int]]:
        """
        Determine difficulty level and grade levels from text and age group.
        
        Args:
            title: Resource title
            description: Resource description
            subject: Subject name
            age_group: Age group (e.g., "Years F-2", "Years 3-4")
            
        Returns:
            Tuple of (difficulty_level, grade_levels)
        """
        text = f"{title} {description}".lower()
        extracted_grades = []
        
        # First, try to extract grade levels from the age_group
        if age_group and age_group != "All Years":
            # Handle foundation year
            if "f-" in age_group.lower():
                extracted_grades.append(0)  # Use 0 to represent foundation/prep
                
                # Extract upper grade if present (e.g., "Years F-2" → [0, 1, 2])
                match = re.search(r'f-(\d+)', age_group.lower())
                if match:
                    upper_grade = int(match.group(1))
                    extracted_grades.extend(range(1, upper_grade + 1))
            else:
                # Extract grade ranges (e.g., "Years 3-4" → [3, 4])
                match = re.search(r'(\d+)-(\d+)', age_group.lower())
                if match:
                    lower_grade = int(match.group(1))
                    upper_grade = int(match.group(2))
                    extracted_grades.extend(range(lower_grade, upper_grade + 1))
        
        # If no grades extracted from age_group, try from content text
        if not extracted_grades:
            # Extract grade/year level patterns from text
            grade_patterns = [
                r'year (\d+)',
                r'grade (\d+)',
                r'years? (\d+)[- ](\d+)',
                r'grades? (\d+)[- ](\d+)',
                r'years? (\d+),? (\d+)(?:,? and (\d+))?',
                r'grades? (\d+),? (\d+)(?:,? and (\d+))?',
                r'foundation',  # For Australian foundation year
                r'prep',  # Alternative name for foundation
                r'reception', # Alternative name for foundation
                r'kindergarten'  # Alternative name for foundation
            ]
            
            # Check for specific grade mentions
            for pattern in grade_patterns:
                if pattern in ['foundation', 'prep', 'reception', 'kindergarten']:
                    if re.search(pattern, text):
                        extracted_grades.append(0)  # Use 0 to represent foundation/prep
                        continue
                        
                matches = re.findall(pattern, text)
                for match in matches:
                    if isinstance(match, tuple):
                        # Process each number in the tuple
                        for grade_str in match:
                            if grade_str and grade_str.strip() and grade_str.isdigit():
                                grade = int(grade_str)
                                if 1 <= grade <= 12:  # Valid grade range
                                    extracted_grades.append(grade)
                        
                        # If it's a range (just two numbers), fill in the range
                        if len(match) == 2 and all(m.isdigit() for m in match):
                            start, end = int(match[0]), int(match[1])
                            if 1 <= start <= end <= 12 and end - start <= 6:  # Reasonable range
                                extracted_grades.extend(range(start, end + 1))
                    elif isinstance(match, str) and match.isdigit():
                        grade = int(match)
                        if 1 <= grade <= 12:
                            extracted_grades.append(grade)
        
        # Remove duplicates and sort
        extracted_grades = sorted(list(set(extracted_grades)))
        
        # Determine difficulty based on extracted grades
        if extracted_grades:
            # Calculate average grade level
            avg_grade = sum(extracted_grades) / len(extracted_grades)
            
            if avg_grade <= 2:  # Foundation to Year 2
                difficulty = DifficultyLevel.BEGINNER
            elif avg_grade <= 6:  # Year 3 to Year 6
                difficulty = DifficultyLevel.INTERMEDIATE
            else:  # Year 7+
                difficulty = DifficultyLevel.ADVANCED
        else:
            # No grades extracted, use text indicators
            if any(word in text for word in ['basic', 'beginner', 'easy', 'introduction', 'start', 'simple']):
                difficulty = DifficultyLevel.BEGINNER
                extracted_grades = [3, 4, 5]  # Default beginner grades
            elif any(word in text for word in ['advanced', 'complex', 'difficult', 'challenging', 'hard']):
                difficulty = DifficultyLevel.ADVANCED
                extracted_grades = [9, 10, 11, 12]  # Default advanced grades
            else:
                difficulty = DifficultyLevel.INTERMEDIATE
                extracted_grades = [6, 7, 8]  # Default intermediate grades
            
            # Subject-specific adjustments
            subject_lower = subject.lower()
            if 'math' in subject_lower:
                # Math-specific topic indicators
                if any(term in text for term in ['calculus', 'trigonometry', 'quadratic', 'polynomial']):
                    difficulty = DifficultyLevel.ADVANCED
                    if not extracted_grades:
                        extracted_grades = [10, 11, 12]
                elif any(term in text for term in ['algebra', 'geometry', 'equation', 'function']):
                    difficulty = DifficultyLevel.INTERMEDIATE
                    if not extracted_grades:
                        extracted_grades = [7, 8, 9]
                elif any(term in text for term in ['fraction', 'decimal', 'arithmetic', 'counting']):
                    difficulty = DifficultyLevel.BEGINNER
                    if not extracted_grades:
                        extracted_grades = [3, 4, 5, 6]
        
        return difficulty, extracted_grades
    
    async def _extract_duration(self) -> Optional[int]:
        """Extract duration from the current page."""
        duration_selectors = [
            ".duration",
            ".video-duration",
            ".audio-duration",
            "[data-testid='duration']"
        ]
        
        for selector in duration_selectors:
            elem = await self.page.query_selector(selector)
            if elem:
                duration_text = await elem.text_content()
                if duration_text and duration_text.strip():
                    # Try to parse duration
                    return self._parse_duration_text(duration_text.strip())
        
        return None
    
    def _parse_duration_text(self, duration_text: str) -> Optional[int]:
        """Parse duration text to extract minutes."""
        try:
            # Clean up the text
            duration_text = duration_text.strip().lower()
            
            # Check for MM:SS format
            if ":" in duration_text:
                parts = duration_text.split(":")
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    return minutes + (1 if seconds >= 30 else 0)  # Round up for 30+ seconds
                elif len(parts) == 3:  # HH:MM:SS format
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = int(parts[2])
                    return hours * 60 + minutes + (1 if seconds >= 30 else 0)
            
            # Check for "X min Y sec" format
            minutes_match = re.search(r'(\d+)\s*(?:min|m)', duration_text)
            seconds_match = re.search(r'(\d+)\s*(?:sec|s)', duration_text)
            
            if minutes_match:
                minutes = int(minutes_match.group(1))
                if seconds_match:
                    seconds = int(seconds_match.group(1))
                    return minutes + (1 if seconds >= 30 else 0)
                return minutes
            
            # Check for just seconds
            if seconds_match:
                seconds = int(seconds_match.group(1))
                return 1 if seconds > 0 else 0  # At least 1 minute for any duration
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing duration text '{duration_text}': {e}")
            return None
    
    def _estimate_duration(self, content_type: ContentType) -> int:
        """Estimate duration based on content type."""
        if content_type == ContentType.VIDEO:
            return 10  # 10 minutes for video
        elif content_type == ContentType.AUDIO:
            return 15  # 15 minutes for audio
        elif content_type == ContentType.INTERACTIVE:
            return 20  # 20 minutes for interactive content
        elif content_type == ContentType.QUIZ:
            return 10  # 10 minutes for quiz
        elif content_type == ContentType.WORKSHEET:
            return 30  # 30 minutes for worksheet
        elif content_type == ContentType.LESSON:
            return 45  # 45 minutes for lesson
        elif content_type == ContentType.ACTIVITY:
            return 30  # 30 minutes for activity
        else:  # Article
            return 15  # 15 minutes for article
    
    def _extract_keywords(self, title: str, description: str) -> List[str]:
        """Extract keywords from title and description."""
        if not title and not description:
            return []
            
        text = f"{title} {description}".lower()
        
        # Extract words and filter out short words and stop words
        words = re.findall(r'\b\w+\b', text)
        keywords = [word for word in words if len(word) > 3 and word not in self.stop_words]
        
        # Remove duplicates and return top keywords (up to 15)
        unique_keywords = sorted(list(set(keywords)), key=lambda x: text.count(x), reverse=True)
        return unique_keywords[:15]
    
    async def _extract_video_content(self) -> Dict[str, Any]:
        """Extract video content from the current page."""
        video_info = {}
        
        # Look for video elements
        video_selectors = [
            "video",
            ".video-player",
            ".media-player",
            "iframe[src*='youtube']",
            "iframe[src*='vimeo']",
            "iframe[src*='iview']",
            "[data-component-name='VideoPlayer']"
        ]
        
        for selector in video_selectors:
            video_elem = await self.page.query_selector(selector)
            if video_elem:
                # For video element
                if selector == "video":
                    src = await video_elem.get_attribute("src")
                    if src:
                        video_info["video_url"] = src
                    
                    poster = await video_elem.get_attribute("poster")
                    if poster:
                        video_info["thumbnail_url"] = poster
                
                # For iframe (YouTube, Vimeo, etc.)
                if selector.startswith("iframe"):
                    src = await video_elem.get_attribute("src")
                    if src:
                        video_info["video_url"] = src
                
                break
        
        # Look for transcript
        transcript_selectors = [
            ".transcript",
            ".video-transcript",
            "[data-testid='transcript']",
            ".closed-captions"
        ]
        
        for selector in transcript_selectors:
            transcript_elem = await self.page.query_selector(selector)
            if transcript_elem:
                transcript = await transcript_elem.text_content()
                if transcript and transcript.strip():
                    video_info["transcription"] = transcript.strip()
                break
        
        return video_info
    
    async def _extract_audio_content(self) -> Dict[str, Any]:
        """Extract audio content from the current page."""
        audio_info = {}
        
        # Look for audio elements
        audio_selectors = [
            "audio",
            ".audio-player",
            "[data-component-name='AudioPlayer']",
            ".podcast-player"
        ]
        
        for selector in audio_selectors:
            audio_elem = await self.page.query_selector(selector)
            if audio_elem:
                # For audio element
                if selector == "audio":
                    src = await audio_elem.get_attribute("src")
                    if src:
                        audio_info["audio_url"] = src
                
                break
        
        # Look for transcript
        transcript_selectors = [
            ".transcript",
            ".audio-transcript",
            "[data-testid='transcript']"
        ]
        
        for selector in transcript_selectors:
            transcript_elem = await self.page.query_selector(selector)
            if transcript_elem:
                transcript = await transcript_elem.text_content()
                if transcript and transcript.strip():
                    audio_info["transcription"] = transcript.strip()
                break
        
        return audio_info
    
    async def _extract_article_text(self) -> str:
        """Extract article text from the current page."""
        # Look for article content
        content_selectors = [
            "article",
            "main",
            ".content-block-article__content",
            ".article__body",
            ".content-main",
            "#content-main",
            ".main-content"
        ]
        
        for selector in content_selectors:
            content_elem = await self.page.query_selector(selector)
            if content_elem:
                # Get all paragraphs
                paragraphs = await content_elem.query_selector_all("p")
                if paragraphs:
                    text_parts = []
                    for p in paragraphs:
                        text = await p.text_content()
                        if text and text.strip():
                            text_parts.append(text.strip())
                    
                    if text_parts:
                        return "\n\n".join(text_parts)
                
                # If no paragraphs found, get all text content
                text = await content_elem.text_content()
                if text and text.strip():
                    return text.strip()
        
        return ""
    
    async def _extract_interactive_content(self) -> Dict[str, Any]:
        """Extract interactive content from the current page."""
        interactive_info = {}
        
        # Check for interactive elements
        interactive_selectors = [
            "iframe",
            ".interactive",
            ".game",
            "canvas",
            "[data-component-name='Interactive']"
        ]
        
        for selector in interactive_selectors:
            elem = await self.page.query_selector(selector)
            if elem:
                if selector == "iframe":
                    src = await elem.get_attribute("src")
                    if src:
                        interactive_info["iframe_src"] = src
                
                interactive_info["has_interactive"] = True
                break
        
        # Extract instructions
        instruction_selectors = [
            ".instructions",
            ".description",
            ".how-to-play",
            ".guidelines"
        ]
        
        for selector in instruction_selectors:
            elem = await self.page.query_selector(selector)
            if elem:
                instructions = await elem.text_content()
                if instructions and instructions.strip():
                    interactive_info["instructions"] = instructions.strip()
                    break
        
        return interactive_info
    
    async def _extract_quiz_content(self) -> Dict[str, Any]:
        """Extract quiz content from the current page."""
        quiz_info = {}
        
        # Look for quiz elements
        quiz_selectors = [
            ".quiz",
            ".assessment",
            ".questions",
            "form[data-quiz]",
            "[data-component-name='Quiz']"
        ]
        
        for selector in quiz_selectors:
            quiz_elem = await self.page.query_selector(selector)
            if quiz_elem:
                quiz_info["has_quiz"] = True
                
                # Try to extract number of questions
                questions = await quiz_elem.query_selector_all(".question, .quiz-question")
                if questions:
                    quiz_info["question_count"] = len(questions)
                
                break
        
        # Extract instructions
        instruction_selectors = [
            ".quiz-instructions",
            ".quiz-intro",
            ".instructions",
            ".description"
        ]
        
        for selector in instruction_selectors:
            elem = await self.page.query_selector(selector)
            if elem:
                instructions = await elem.text_content()
                if instructions and instructions.strip():
                    quiz_info["instructions"] = instructions.strip()
                    break
        
        return quiz_info
    
    async def _extract_author(self) -> Optional[str]:
        """Extract author from the current page."""
        author_selectors = [
            ".author",
            ".byline",
            ".content-block-article__byline",
            "[data-testid='author']",
            "meta[name='author']"
        ]
        
        for selector in author_selectors:
            if selector.startswith("meta"):
                elem = await self.page.query_selector(selector)
                if elem:
                    author = await elem.get_attribute("content")
                    if author and author.strip():
                        return author.strip()
            else:
                elem = await self.page.query_selector(selector)
                if elem:
                    author = await elem.text_content()
                    if author and author.strip():
                        # Remove "By" prefix if present
                        author = author.strip()
                        if author.lower().startswith("by "):
                            author = author[3:].strip()
                        return author
        
        return None
    
    def save_extracted_content(self, content: Dict[str, Any], subject_name: str, age_group: str = None):
        """Save extracted content to a JSON file."""
        if not content:
            return
            
        # Create a safe subject name for the filename
        safe_subject = subject_name.replace(" ", "_").replace("/", "_")
        
        # Create a safe title for the filename
        safe_title = content["title"].replace(" ", "_").replace("/", "_")[:30]
        
        # Add age group to filename if available
        age_group_part = ""
        if age_group and age_group != "All Years":
            safe_age_group = age_group.replace(" ", "_").replace("/", "_")
            age_group_part = f"_{safe_age_group}"
        
        # Create filename
        filename = os.path.join(self.extracted_dir, f"{safe_subject}{age_group_part}_{safe_title}_{content['id'][:8]}.json")
        
        # Create a copy without large content
        content_copy = content.copy()
        
        # Remove large HTML content
        if "metadata" in content_copy and "content_html" in content_copy["metadata"]:
            content_copy["metadata"]["content_html"] = content_copy["metadata"]["content_html"][:500] + "... [truncated]"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(content_copy, f, indent=2)
                
            logger.info(f"Saved extracted content to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving extracted content to JSON: {e}")
    
    async def process_resources(self, resources: List[Dict[str, str]], batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Process a batch of resources to extract content.
        
        Args:
            resources: List of resource dictionaries with title, URL, subject, and age_group
            batch_size: Number of resources to process in a batch
            
        Returns:
            List of processed content items
        """
        processed_items = []
        
        # Process in batches
        for i in range(0, len(resources), batch_size):
            batch = resources[i:i+batch_size]
            
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} resources)")
            
            for j, resource in enumerate(batch):
                try:
                    logger.info(f"Processing resource {j+1}/{len(batch)}: {resource['title'][:30]}{'...' if len(resource['title']) > 30 else ''}")
                    
                    # Extract content
                    content = await self.extract_content_details(resource)
                    
                    # Save extracted content
                    self.save_extracted_content(
                        content, 
                        resource["subject"], 
                        resource.get("age_group", "All Years")
                    )
                    
                    # Process and index content if processor is available
                    if self.content_processor:
                        try:
                            # Set a system owner_id for scraped content
                            system_owner_id = "system"
                            
                            # Process and index the content with system owner_id
                            processed_content = await process_and_index_content(
                                resource["url"], 
                                content, 
                                owner_id=system_owner_id
                            )
                            processed_items.append(processed_content)
                            logger.info(f"Successfully processed and indexed: {resource['title'][:30]}{'...' if len(resource['title']) > 30 else ''}")
                        except Exception as e:
                            logger.error(f"Error processing and indexing content: {e}")
                            # Still add the extracted content
                            processed_items.append(content)
                    else:
                        # Just add the extracted content
                        processed_items.append(content)
                    
                except Exception as e:
                    logger.error(f"Error extracting content: {e}")
            
            # Add a small delay between batches
            await asyncio.sleep(2)
        
        return processed_items
    
    async def process_from_index(self, index_path: str, subject_limit: Optional[int] = None, resource_limit: Optional[int] = None, age_groups: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Process resources from an index file.
        
        Args:
            index_path: Path to the resource index JSON file
            subject_limit: Optional limit on number of subjects to process
            resource_limit: Optional limit on number of resources per subject/age group
            age_groups: Optional list of age groups to process (e.g., ["Years F-2", "Years 3-4"])
            
        Returns:
            Dictionary with processing results
        """
        results = {
            "processed_count": 0,
            "subjects_processed": 0,
            "age_groups_processed": 0,
            "errors": 0
        }
        
        try:
            # Load the index file
            with open(index_path, 'r', encoding='utf-8') as f:
                index = json.load(f)
            
            # Get subjects
            subjects = list(index["subjects"].keys())
            
            # Apply subject limit if specified
            if subject_limit and isinstance(subject_limit, int) and subject_limit > 0:
                subjects = subjects[:subject_limit]
            
            subjects_processed = 0
            age_groups_processed = 0
            
            for subject in subjects:
                try:
                    logger.info(f"Processing resources for subject: {subject}")
                    
                    # Process by age group if available in the index
                    if "age_groups" in index["subjects"][subject] and index["subjects"][subject]["age_groups"]:
                        available_age_groups = list(index["subjects"][subject]["age_groups"].keys())
                        
                        # Filter age groups if specified
                        if age_groups:
                            available_age_groups = [ag for ag in available_age_groups if ag in age_groups]
                        
                        if available_age_groups:
                            logger.info(f"Processing {len(available_age_groups)} age groups for {subject}: {available_age_groups}")
                            
                            for age_group in available_age_groups:
                                try:
                                    # Get resources for this subject and age group
                                    resources = index["subjects"][subject]["age_groups"][age_group]["resources"]
                                    
                                    # Apply resource limit if specified
                                    if resource_limit and isinstance(resource_limit, int) and resource_limit > 0:
                                        resources = resources[:resource_limit]
                                    
                                    # Process resources
                                    processed = await self.process_resources(resources)
                                    
                                    # Update results
                                    results["processed_count"] += len(processed)
                                    age_groups_processed += 1
                                    
                                    logger.info(f"Processed {len(processed)} resources for {subject} - {age_group}")
                                    
                                except Exception as e:
                                    logger.error(f"Error processing age group {age_group} for subject {subject}: {e}")
                                    results["errors"] += 1
                        else:
                            logger.info(f"No matching age groups for {subject}")
                            
                    else:
                        # Process all resources for the subject without age group separation
                        resources = index["subjects"][subject]["resources"]
                        
                        # Apply resource limit if specified
                        if resource_limit and isinstance(resource_limit, int) and resource_limit > 0:
                            resources = resources[:resource_limit]
                        
                        # Process resources
                        processed = await self.process_resources(resources)
                        
                        # Update results
                        results["processed_count"] += len(processed)
                        
                        logger.info(f"Processed {len(processed)} resources for subject {subject}")
                    
                    subjects_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing subject {subject}: {e}")
                    results["errors"] += 1
            
            results["subjects_processed"] = subjects_processed
            results["age_groups_processed"] = age_groups_processed
            
        except Exception as e:
            logger.error(f"Error processing index file: {e}")
            results["errors"] += 1
        
        return results


async def run_extractor(
    index_path: str, 
    subject_limit=None, 
    resource_limit=None, 
    age_groups=None, 
    headless=True
):
    """
    Run the content extractor using an index file.
    
    Args:
        index_path: Path to the resource index JSON file
        subject_limit: Optional limit on number of subjects to process
        resource_limit: Optional limit on number of resources per subject/age group
        age_groups: Optional list of age groups to process
        headless: Whether to run browser in headless mode
        
    Returns:
        Dictionary with extraction results
    """
    extractor = EducationContentExtractor()
    
    try:
        # Setup extractor
        await extractor.setup(headless=headless)
        
        # Process resources from index
        results = await extractor.process_from_index(index_path, subject_limit, resource_limit, age_groups)
        
        logger.info(f"Extraction completed. Processed {results['processed_count']} resources across {results['subjects_processed']} subjects and {results['age_groups_processed']} age groups.")
        return results
        
    except Exception as e:
        logger.error(f"Error running extractor: {e}")
        return {"error": str(e)}
        
    finally:
        # Clean up resources
        await extractor.teardown()

if __name__ == "__main__":
    # Run the extractor using the index file
    index_path = os.path.join(os.getcwd(), "education_resources", "resource_index.json")
    
    if not os.path.exists(index_path):
        logger.error(f"Index file not found: {index_path}")
        print(f"Index file not found: {index_path}")
        print("Please run the indexer (edu_resource_indexer.py) first to create the index.")
        sys.exit(1)
    
    # Specify age groups to process (optional)
    target_age_groups = None  # Set to None to process all age groups
    # target_age_groups = ["Years F-2", "Years 3-4"]  # Uncomment to process specific age groups
    
    asyncio.run(run_extractor(
        index_path=index_path,
        subject_limit=2,  # Process 2 subjects for testing
        resource_limit=5,  # Process 5 resources per subject/age group
        age_groups=target_age_groups,
        headless=False  # Run with visible browser for debugging
    ))