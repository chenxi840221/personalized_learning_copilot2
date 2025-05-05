import logging
from typing import Dict, Any, List, Optional
from azure.ai.textanalytics import TextAnalyticsClient, ExtractSummaryAction
from azure.core.credentials import AzureKeyCredential
import json
from models.content import Content
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class ContentAnalyzer:
    """
    Analyze educational content using Azure Cognitive Services
    """
    def __init__(self):
        """Initialize the content analyzer with Azure Text Analytics client."""
        # Initialize Text Analytics client if credentials are available
        if settings.TEXT_ANALYTICS_ENDPOINT and settings.TEXT_ANALYTICS_KEY:
            self.text_analytics_client = TextAnalyticsClient(
                endpoint=settings.TEXT_ANALYTICS_ENDPOINT,
                credential=AzureKeyCredential(settings.TEXT_ANALYTICS_KEY)
            )
        else:
            self.text_analytics_client = None
            logger.warning("Text Analytics credentials not provided. Some analysis features will be unavailable.")
    
    async def analyze_content(self, content: Content) -> Dict[str, Any]:
        """
        Analyze content using Azure Text Analytics.
        Args:
            content: The content to analyze
        Returns:
            Analysis results including key phrases, sentiment, and summary
        """
        if not self.text_analytics_client:
            logger.warning("Text Analytics client not initialized. Skipping content analysis.")
            return {}
        try:
            # Prepare text for analysis
            text = self._prepare_text_for_analysis(content)
            
            # Extract key phrases
            key_phrase_response = self.text_analytics_client.extract_key_phrases([text])[0]
            key_phrases = key_phrase_response.key_phrases if not key_phrase_response.is_error else []
            
            # Analyze sentiment
            sentiment_response = self.text_analytics_client.analyze_sentiment([text])[0]
            sentiment = None
            if not sentiment_response.is_error:
                sentiment = {
                    "sentiment": sentiment_response.sentiment,
                    "positive_score": sentiment_response.confidence_scores.positive,
                    "neutral_score": sentiment_response.confidence_scores.neutral,
                    "negative_score": sentiment_response.confidence_scores.negative
                }
            
            # Generate summary
            summary_actions = [ExtractSummaryAction()]
            poller = self.text_analytics_client.begin_analyze_actions([text], summary_actions)
            summary_results = list(poller.result())[0]
            summary = []
            for result in summary_results:
                if not result.is_error:
                    summary = [sentence.text for sentence in result.sentences]
            
            # Return analysis results
            return {
                "key_phrases": key_phrases,
                "sentiment": sentiment,
                "summary": summary
            }
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            return {}
    
    def _prepare_text_for_analysis(self, content: Content) -> str:
        """
        Prepare content text for analysis.
        Args:
            content: Content item
        Returns:
            Processed text ready for analysis
        """
        return f"{content.title}. {content.description}"
    
    async def categorize_content_difficulty(self, text: str, grade_level: int) -> str:
        """
        Determine appropriate difficulty level based on text analysis.
        Args:
            text: Content text
            grade_level: Target grade level
        Returns:
            Difficulty level (beginner, intermediate, advanced)
        """
        if not self.text_analytics_client:
            # Default to grade-based difficulty when Text Analytics is unavailable
            if grade_level <= 5:
                return "beginner"
            elif grade_level <= 8:
                return "intermediate"
            else:
                return "advanced"
        try:
            # Analyze text complexity using entities and lexical statistics
            entity_response = self.text_analytics_client.recognize_entities([text])[0]
            entities = entity_response.entities if not entity_response.is_error else []
            
            # Count entities by category
            entity_categories = {}
            for entity in entities:
                category = entity.category
                entity_categories[category] = entity_categories.get(category, 0) + 1
            
            # Calculate complexity score based on entity density and types
            total_entities = len(entities)
            words = text.split()
            total_words = len(words)
            
            # Entity density per 100 words
            entity_density = (total_entities / total_words) * 100 if total_words > 0 else 0
            
            # Technical entities (like DateTime, Quantity, etc. indicate more complex content)
            technical_entities = sum([
                entity_categories.get("DateTime", 0),
                entity_categories.get("Quantity", 0),
                entity_categories.get("PhoneNumber", 0),
                entity_categories.get("Address", 0)
            ])
            
            # Calculate technical density
            tech_density = (technical_entities / total_words) * 100 if total_words > 0 else 0
            
            # Calculate average word length
            avg_word_length = sum(len(word) for word in words) / total_words if total_words > 0 else 0
            
            # Combine metrics into complexity score
            complexity_score = (entity_density * 0.4) + (tech_density * 0.3) + (avg_word_length * 10)
            
            # Adjust based on grade level
            if grade_level <= 5:
                # For younger students, lower thresholds
                if complexity_score < 10:
                    return "beginner"
                elif complexity_score < 20:
                    return "intermediate"
                else:
                    return "advanced"
            elif grade_level <= 8:
                # For middle grade students
                if complexity_score < 15:
                    return "beginner"
                elif complexity_score < 25:
                    return "intermediate"
                else:
                    return "advanced"
            else:
                # For high school students
                if complexity_score < 20:
                    return "beginner"
                elif complexity_score < 30:
                    return "intermediate"
                else:
                    return "advanced"
        except Exception as e:
            logger.error(f"Error categorizing content difficulty: {e}")
            # Fall back to grade-based difficulty
            if grade_level <= 5:
                return "beginner"
            elif grade_level <= 8:
                return "intermediate"
            else:
                return "advanced"
    
    async def analyze_student_progress(self, writing_samples: List[str], quiz_scores: List[float]) -> Dict[str, Any]:
        """
        Analyze student progress based on writing samples and quiz scores.
        Args:
            writing_samples: Student writing samples
            quiz_scores: Student quiz scores
        Returns:
            Analysis results
        """
        if not self.text_analytics_client or not writing_samples:
            # Basic analysis without Text Analytics
            return {
                "avg_quiz_score": sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0,
                "completion_rate": len(quiz_scores) / 10 if quiz_scores else 0,  # Assuming 10 is total
                "writing_quality": None,
                "areas_for_improvement": [],
                "strengths": []
            }
        try:
            # Analyze writing samples
            sentiment_results = []
            entity_results = []
            language_results = []
            
            # Get sentiment for writing samples
            sentiment_response = self.text_analytics_client.analyze_sentiment(writing_samples)
            sentiment_results = [doc for doc in sentiment_response if not doc.is_error]
            
            # Get entities
            entity_response = self.text_analytics_client.recognize_entities(writing_samples)
            entity_results = [doc for doc in entity_response if not doc.is_error]
            
            # Get language assessment
            language_response = self.text_analytics_client.detect_language(writing_samples)
            language_results = [doc for doc in language_response if not doc.is_error]
            
            # Calculate writing quality score (0-100)
            writing_quality = 0
            if sentiment_results:
                # Higher confidence scores indicate better writing
                avg_confidence = sum(max(doc.confidence_scores.positive, 
                                         doc.confidence_scores.negative, 
                                         doc.confidence_scores.neutral) 
                                    for doc in sentiment_results) / len(sentiment_results)
                writing_quality += avg_confidence * 30  # Up to 30 points for clear sentiment
            
            if entity_results:
                # More entities typically indicate more detailed writing
                avg_entities = sum(len(doc.entities) for doc in entity_results) / len(entity_results)
                # Cap at 20 entities for max score
                entity_score = min(avg_entities / 20, 1.0) * 40
                writing_quality += entity_score  # Up to 40 points for detailed content
            
            if language_results:
                # Higher confidence in language detection indicates more fluent writing
                avg_language_confidence = sum(doc.primary_language.confidence_score 
                                             for doc in language_results) / len(language_results)
                writing_quality += avg_language_confidence * 30  # Up to 30 points for fluency
            
            # Identify strengths and areas for improvement
            strengths = []
            areas_for_improvement = []
            
            # Quiz performance analysis
            avg_quiz_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
            if avg_quiz_score > 0.8:
                strengths.append("Strong quiz performance")
            elif avg_quiz_score < 0.6:
                areas_for_improvement.append("Quiz performance needs improvement")
            
            # Writing analysis
            if writing_quality > 70:
                strengths.append("Good writing skills")
            else:
                areas_for_improvement.append("Writing skills need development")
            
            # Entity usage analysis
            if entity_results:
                avg_entity_count = sum(len(doc.entities) for doc in entity_results) / len(entity_results)
                if avg_entity_count > 10:
                    strengths.append("Good use of specific terms and concepts")
                else:
                    areas_for_improvement.append("Could use more specific examples and terminology")
            
            return {
                "avg_quiz_score": avg_quiz_score,
                "completion_rate": len(quiz_scores) / 10 if quiz_scores else 0,  # Assuming 10 is total
                "writing_quality": writing_quality,
                "areas_for_improvement": areas_for_improvement,
                "strengths": strengths
            }
        except Exception as e:
            logger.error(f"Error analyzing student progress: {e}")
            return {
                "avg_quiz_score": sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0,
                "completion_rate": len(quiz_scores) / 10 if quiz_scores else 0,
                "writing_quality": None,
                "areas_for_improvement": [],
                "strengths": []
            }

# Singleton instance
content_analyzer = None

async def get_content_analyzer():
    """Get or create the content analyzer singleton."""
    global content_analyzer
    if content_analyzer is None:
        content_analyzer = ContentAnalyzer()
    return content_analyzer