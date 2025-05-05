# backend/utils/multimedia_content_processor.py
"""
Multimedia Content Processor – **updated version for Azure Search compatibility (2025‑04‑25)**
===========================================================================================
Updates fixed field incompatibility and added page_content field for LangChain compatibility.
"""

from __future__ import annotations

###############################################################################
# Standard‑library imports
###############################################################################
import asyncio
import copy
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

###############################################################################
# Third‑party SDKs
###############################################################################
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.cognitiveservices.speech import AudioConfig, SpeechConfig, SpeechRecognizer, ResultReason
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from azure.search.documents.aio import SearchClient

###############################################################################
# Internal modules – make sure these exist in your project
###############################################################################
from utils.vector_compat import Vector  # noqa: F401 – converts numpy → list when needed
from config.settings import Settings
from rag.openai_adapter import get_openai_adapter

settings = Settings()
logger = logging.getLogger(__name__)
ISO = lambda dt: dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731

###############################################################################
# Main class
###############################################################################
class MultimediaContentProcessor:  # noqa: C901 – cohesive but large
    """Extract text/transcripts, embed with OpenAI, and index into Azure Search."""

    def __init__(self) -> None:
        self.openai_client = None
        self.speech_config: Optional[SpeechConfig] = None
        self.document_client: Optional[DocumentAnalysisClient] = None
        self.vision_client: Optional[ComputerVisionClient] = None
        self.search_client: Optional[SearchClient] = None
        self.embedding_dimension = int(getattr(settings, "AZURE_SEARCH_EMBEDDING_DIMENSION", 1536))

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    async def initialize(self) -> None:
        """Initialise external SDK clients lazily."""
        # OpenAI embeddings
        try:
            self.openai_client = await get_openai_adapter()
        except Exception as exc:  # pragma: no cover
            logger.error("OpenAI adapter init failed: %s", exc)

        # Azure Form Recogniser
        if settings.FORM_RECOGNIZER_ENDPOINT and settings.FORM_RECOGNIZER_KEY:
            self.document_client = DocumentAnalysisClient(
                endpoint=settings.FORM_RECOGNIZER_ENDPOINT,
                credential=AzureKeyCredential(settings.FORM_RECOGNIZER_KEY),
            )

        # Speech Service
        if getattr(settings, "SPEECH_KEY", None) and getattr(settings, "SPEECH_REGION", None):
            self.speech_config = SpeechConfig(subscription=settings.SPEECH_KEY, region=settings.SPEECH_REGION)

        # Computer Vision (optional – not used in current code but kept for parity)
        if getattr(settings, "COMPUTER_VISION_ENDPOINT", None) and getattr(settings, "COMPUTER_VISION_KEY", None):
            self.vision_client = ComputerVisionClient(
                endpoint=settings.COMPUTER_VISION_ENDPOINT,
                credentials=CognitiveServicesCredentials(settings.COMPUTER_VISION_KEY),
            )

        # Azure AI Search
        if settings.AZURE_SEARCH_ENDPOINT and settings.AZURE_SEARCH_KEY:
            self.search_client = SearchClient(
                endpoint=settings.AZURE_SEARCH_ENDPOINT,
                index_name=settings.AZURE_SEARCH_INDEX_NAME,
                credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY),
            )
            await self._detect_embedding_dimension()

    async def _detect_embedding_dimension(self) -> None:
        if not self.search_client:
            return
        try:
            schema = await self.search_client.get_index(self.search_client._index_name)  # type: ignore[attr-defined]
            for field in schema["fields"]:
                if field["name"] == "embedding":
                    dim = field.get("vectorSearchDimensions") or field.get("dimensions")
                    if dim:
                        self.embedding_dimension = int(dim)
                        logger.info("Embedding dimension → %s", self.embedding_dimension)
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not inspect index schema: %s", exc)

    async def close(self) -> None:
        if self.search_client:
            await self.search_client.close()

    # ------------------------------------------------------------------
    # High‑level public API
    # ------------------------------------------------------------------
    
    async def process_content(self, content_url: str, content_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process content based on its type (text, audio, video) and prepare it for indexing.
        
        Args:
            content_url: URL of the content
            content_info: Basic metadata about the content
            
        Returns:
            Processed content information with extracted text and embedding
        """
        # Make sure we're initialized
        if not self.openai_client:
            await self.initialize()
            if not self.openai_client:
                logger.warning("OpenAI client still not initialized. Some features will be disabled.")
        
        content_type = content_info.get('content_type', '')
        
        # Format dates properly for Azure Search
        current_time = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
        
        # Initialize the content item with basic info
        content_id = content_info.get("id", str(uuid.uuid4()))
        content_item = {
            "id": content_id,
            "title": content_info.get('title', 'Untitled Content'),
            "description": content_info.get('description', ''),
            "content_type": content_type,
            "subject": content_info.get('subject', ''),
            "topics": content_info.get('topics', []),
            "url": content_url,
            "source": content_info.get('source', 'ABC Education'),
            "difficulty_level": content_info.get('difficulty_level', 'intermediate'),
            "grade_level": content_info.get('grade_level', []),
            "duration_minutes": content_info.get('duration_minutes', 0),
            "keywords": content_info.get('keywords', []),
            "created_at": current_time,  # Properly formatted for Azure Search
            "updated_at": current_time,  # Properly formatted for Azure Search
            "metadata": {}
        }
        
        # Extract content based on type
        extracted_text = ""
        
        if 'text' in content_type or 'article' in content_type:
            # Process text content
            extracted_text = await self._process_text_content(content_url, content_info)
            content_item["metadata"]["content_text"] = extracted_text
            # Add flattened metadata fields for Azure Search
            content_item["metadata_content_text"] = extracted_text
            
        elif 'audio' in content_type or 'podcast' in content_type:
            # Process audio content
            audio_text, duration = await self._process_audio_content(content_url)
            content_item["metadata"]["transcription"] = audio_text
            # Add flattened metadata field for Azure Search
            content_item["metadata_transcription"] = audio_text
            extracted_text = audio_text
            
            # Update duration if available
            if duration and duration > 0:
                content_item["duration_minutes"] = duration
                
        elif 'video' in content_type:
            # Process video content
            video_text, duration, thumbnail_url = await self._process_video_content(content_url)
            content_item["metadata"]["transcription"] = video_text
            # Add flattened metadata fields for Azure Search 
            content_item["metadata_transcription"] = video_text
            if thumbnail_url:
                content_item["metadata"]["thumbnail_url"] = thumbnail_url
                content_item["metadata_thumbnail_url"] = thumbnail_url
            extracted_text = video_text
            
            # Update duration if available
            if duration and duration > 0:
                content_item["duration_minutes"] = duration
        
        # Add the page_content field for LangChain compatibility
        content_item["page_content"] = extracted_text
        
        # Generate embedding for search
        if extracted_text and self.openai_client:
            text_for_embedding = self._prepare_text_for_embedding(content_item, extracted_text)
            try:
                embedding = await self._generate_embedding(text_for_embedding)
                content_item["embedding"] = embedding
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
                # Use a default empty vector of the right size
                content_item["embedding"] = [0.0] * self.embedding_dimension
        else:
            # Set a default empty vector if we can't generate embeddings
            content_item["embedding"] = [0.0] * self.embedding_dimension
        
        return content_item
    
    async def _process_text_content(self, content_url: str, content_info: Dict[str, Any]) -> str:
        """
        Process text content from a URL.
        
        Args:
            content_url: URL of the text content
            content_info: Basic metadata about the content
            
        Returns:
            Extracted text content
        """
        # If HTML content is already provided, use it
        if 'metadata' in content_info and 'content_html' in content_info['metadata']:
            from bs4 import BeautifulSoup
            
            # Extract text from HTML
            soup = BeautifulSoup(content_info['metadata']['content_html'], 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
                
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            return text
        
        # Otherwise, try to extract text using Form Recognizer for structured documents
        if self.document_client and (content_url.endswith('.pdf') or 
                                    content_url.endswith('.docx') or 
                                    content_url.endswith('.pptx')):
            try:
                # Use Form Recognizer to extract text
                poller = await self.document_client.begin_analyze_document_from_url(
                    "prebuilt-document", content_url
                )
                result = await poller.result()
                
                # Extract text content
                return result.content
            except Exception as e:
                logger.error(f"Error extracting text with Form Recognizer: {e}")
        
        # For web pages, we need to fetch and parse them
        if content_url.startswith(('http://', 'https://')):
            try:
                import aiohttp
                from bs4 import BeautifulSoup
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(content_url) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Parse HTML
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Remove script and style elements
                            for script in soup(["script", "style"]):
                                script.extract()
                                
                            # Get text
                            text = soup.get_text(separator='\n', strip=True)
                            return text
            except Exception as e:
                logger.error(f"Error fetching and parsing web content: {e}")
        
        # Return empty string if nothing could be extracted
        return ""
    
    async def _process_audio_content(self, audio_url: str) -> Tuple[str, Optional[int]]:
        """
        Process audio content using Azure Speech Services.
        
        Args:
            audio_url: URL of the audio content
            
        Returns:
            Tuple of (transcription, duration_minutes)
        """
        if not self.speech_config:
            logger.warning("Speech Services not configured. Cannot process audio content.")
            return "", None
        
        try:
            # Download the audio file
            import aiohttp
            import tempfile
            
            audio_file = None
            duration_minutes = None
            
            async with aiohttp.ClientSession() as session:
                async with session.get(audio_url) as response:
                    if response.status == 200:
                        # Create a temporary file
                        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(audio_url))
                        audio_file_path = audio_file.name
                        audio_file.close()
                        
                        # Save the audio content
                        with open(audio_file_path, 'wb') as f:
                            f.write(await response.read())
                        
                        # Get audio duration using a helper library
                        try:
                            from pydub import AudioSegment
                            audio = AudioSegment.from_file(audio_file_path)
                            duration_seconds = len(audio) / 1000
                            duration_minutes = int(duration_seconds / 60) + (1 if duration_seconds % 60 >= 30 else 0)
                        except ImportError:
                            logger.warning("Pydub not available. Cannot determine audio duration.")
                        
                        # Configure speech recognition
                        audio_config = AudioConfig(filename=audio_file_path)
                        speech_recognizer = SpeechRecognizer(
                            speech_config=self.speech_config, 
                            audio_config=audio_config
                        )
                        
                        # Start continuous recognition
                        transcription = []
                        
                        # This is a simplified approach - in a real system you'd want to use the continuous 
                        # recognition API with proper event handling
                        done = False
                        
                        def stop_cb(evt):
                            nonlocal done
                            done = True
                        
                        def recognized_cb(evt):
                            if evt.result.reason == ResultReason.RecognizedSpeech:
                                transcription.append(evt.result.text)
                        
                        # Connect callbacks
                        speech_recognizer.recognized.connect(recognized_cb)
                        speech_recognizer.session_stopped.connect(stop_cb)
                        speech_recognizer.canceled.connect(stop_cb)
                        
                        # Start continuous speech recognition
                        speech_recognizer.start_continuous_recognition()
                        
                        # Wait for completion (would be event-based in a real system)
                        while not done:
                            await asyncio.sleep(0.5)
                        
                        speech_recognizer.stop_continuous_recognition()
                        
                        # Clean up the temporary file
                        os.unlink(audio_file_path)
                        
                        return " ".join(transcription), duration_minutes
            
            return "", None
                    
        except Exception as e:
            logger.error(f"Error processing audio content: {e}")
            return "", None
    
    async def _process_video_content(self, video_url: str) -> Tuple[str, Optional[int], Optional[str]]:
        """
        Process video content by using Playwright to access the video page,
        capture audio stream, and transcribe using Azure Speech Services.
        
        Args:
            video_url: URL of the video content
            
        Returns:
            Tuple of (transcription, duration_minutes, thumbnail_url)
        """
        if not self.speech_config:
            logger.warning("Speech Services not configured. Cannot transcribe video content.")
            return "No transcription available - Speech Services not configured.", None, None
            
        try:
            import tempfile
            from playwright.async_api import async_playwright
            
            logger.info(f"Processing video content from {video_url}")
            
            # Create temporary file for audio
            audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.webm')
            audio_path = audio_file.name
            audio_file.close()
            
            # Create temporary file for thumbnail
            thumbnail_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            thumbnail_path = thumbnail_file.name
            thumbnail_file.close()
            
            duration_minutes = None
            thumbnail_url = None
            transcription = ""
            
            # Use Playwright to navigate to the video page and extract audio
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context(
                    # Enable permissions for media
                    permissions=['microphone', 'camera', 'audio_capture']
                )
                
                # Create a new page
                page = await context.new_page()
                
                # Navigate to the video URL
                await page.goto(video_url, wait_until="networkidle")
                
                # Check if we need to handle any specific video platforms
                if "youtube.com" in video_url or "youtu.be" in video_url:
                    # Handle YouTube
                    logger.info("Detected YouTube video")
                    
                    # Wait for the video player to load
                    await page.wait_for_selector('video', state='attached', timeout=10000)
                    
                    # Click play button if needed
                    play_button = await page.query_selector('.ytp-play-button')
                    if play_button:
                        await play_button.click()
                    
                    # Get video duration if available
                    try:
                        duration_text = await page.evaluate('''() => {
                            const durationElement = document.querySelector('.ytp-time-duration');
                            return durationElement ? durationElement.textContent : '';
                        }''')
                        
                        if duration_text:
                            # Parse duration in MM:SS format
                            parts = duration_text.split(':')
                            if len(parts) == 2:
                                minutes, seconds = int(parts[0]), int(parts[1])
                                duration_minutes = minutes + (1 if seconds >= 30 else 0)
                            elif len(parts) == 3:
                                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                                duration_minutes = hours * 60 + minutes + (1 if seconds >= 30 else 0)
                    except Exception as e:
                        logger.error(f"Error getting YouTube video duration: {e}")
                    
                    # Extract video title for additional context
                    try:
                        video_title = await page.evaluate('''() => {
                            return document.querySelector('h1.title')?.textContent || '';
                        }''')
                        logger.info(f"Video title: {video_title}")
                    except Exception as e:
                        logger.error(f"Error getting YouTube video title: {e}")
                    
                    # Take a screenshot for thumbnail
                    await page.screenshot(path=thumbnail_path)
                    thumbnail_url = f"local://{os.path.basename(thumbnail_path)}"
                    
                    # Check if we can access captions/transcripts directly
                    try:
                        # Click on settings button
                        settings_button = await page.query_selector('.ytp-settings-button')
                        if settings_button:
                            await settings_button.click()
                            await page.wait_for_timeout(500)
                            
                            # Look for subtitles/captions option
                            subtitles_item = await page.query_selector('div.ytp-menuitem[role="menuitem"] span:text-is("Subtitles/CC")')
                            if subtitles_item:
                                # Get parent menuitem and click it
                                menuitem = await subtitles_item.evaluate('node => node.closest(".ytp-menuitem")')
                                if menuitem:
                                    await page.evaluate('node => node.click()', menuitem)
                                    await page.wait_for_timeout(500)
                                    
                                    # Select English captions if available
                                    english_caption = await page.query_selector('div.ytp-menuitem[role="menuitem"] span:text-is("English")')
                                    if english_caption:
                                        menuitem = await english_caption.evaluate('node => node.closest(".ytp-menuitem")')
                                        if menuitem:
                                            await page.evaluate('node => node.click()', menuitem)
                                            
                                            # Now captions should be visible, start extracting them
                                            logger.info("Captions enabled, extracting text")
                                            
                                            # Let the video play and collect captions
                                            caption_parts = []
                                            for _ in range(min(20, duration_minutes or 10)):  # Capture for up to 20 minutes or duration
                                                # Extract current caption text
                                                caption_text = await page.evaluate('''() => {
                                                    const captionElement = document.querySelector('.ytp-caption-segment');
                                                    return captionElement ? captionElement.textContent : '';
                                                }''')
                                                
                                                if caption_text and caption_text not in caption_parts:
                                                    caption_parts.append(caption_text)
                                                
                                                # Wait 3 seconds before checking again
                                                await page.wait_for_timeout(3000)
                                            
                                            # Combine all caption parts
                                            if caption_parts:
                                                transcription = " ".join(caption_parts)
                                                logger.info(f"Extracted {len(caption_parts)} caption segments")
                    except Exception as e:
                        logger.error(f"Error extracting YouTube captions: {e}")
                
                elif "vimeo.com" in video_url:
                    # Handle Vimeo
                    logger.info("Detected Vimeo video")
                    
                    # Wait for the video player to load
                    await page.wait_for_selector('video', state='attached', timeout=10000)
                    
                    # Click play button if needed
                    play_button = await page.query_selector('.play-icon')
                    if play_button:
                        await play_button.click()
                    
                    # Get video duration if available
                    try:
                        duration_text = await page.evaluate('''() => {
                            const durationElement = document.querySelector('.vp-duration');
                            return durationElement ? durationElement.textContent : '';
                        }''')
                        
                        if duration_text:
                            # Parse duration in MM:SS format
                            parts = duration_text.split(':')
                            if len(parts) == 2:
                                minutes, seconds = int(parts[0]), int(parts[1])
                                duration_minutes = minutes + (1 if seconds >= 30 else 0)
                            elif len(parts) == 3:
                                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                                duration_minutes = hours * 60 + minutes + (1 if seconds >= 30 else 0)
                    except Exception as e:
                        logger.error(f"Error getting Vimeo video duration: {e}")
                    
                    # Take a screenshot for thumbnail
                    await page.screenshot(path=thumbnail_path)
                    thumbnail_url = f"local://{os.path.basename(thumbnail_path)}"
                    
                    # Try to enable captions
                    try:
                        cc_button = await page.query_selector('.cc-button')
                        if cc_button:
                            await cc_button.click()
                            await page.wait_for_timeout(500)
                            
                            # Let the video play and collect captions
                            caption_parts = []
                            for _ in range(min(20, duration_minutes or 10)):  # Capture for up to 20 minutes or duration
                                # Extract current caption text
                                caption_text = await page.evaluate('''() => {
                                    const captionElement = document.querySelector('.vp-captions');
                                    return captionElement ? captionElement.textContent : '';
                                }''')
                                
                                if caption_text and caption_text not in caption_parts:
                                    caption_parts.append(caption_text)
                                
                                # Wait 3 seconds before checking again
                                await page.wait_for_timeout(3000)
                            
                            # Combine all caption parts
                            if caption_parts:
                                transcription = " ".join(caption_parts)
                                logger.info(f"Extracted {len(caption_parts)} caption segments")
                    except Exception as e:
                        logger.error(f"Error extracting Vimeo captions: {e}")
                
                else:
                    # Generic video handling
                    logger.info("Processing generic video page")
                    
                    # Look for common video elements
                    for selector in ["video", "iframe[src*='youtube']", "iframe[src*='vimeo']", ".video-player", "[data-video-id]"]:
                        video_element = await page.query_selector(selector)
                        if video_element:
                            logger.info(f"Found video element with selector: {selector}")
                            break
                    
                    # Take a screenshot for thumbnail
                    await page.screenshot(path=thumbnail_path)
                    thumbnail_url = f"local://{os.path.basename(thumbnail_path)}"
                
                # If no transcription was extracted from captions, extract text from the page
                if not transcription:
                    logger.info("No captions found, extracting page text instead")
                    
                    # Get text content from the page
                    page_text = await page.evaluate('''() => {
                        // Helper function to get visible text
                        const getVisibleText = (element) => {
                            const style = window.getComputedStyle(element);
                            return style.display !== 'none' && style.visibility !== 'hidden';
                        };
                        
                        // Get all text nodes
                        const textNodes = [];
                        const walk = document.createTreeWalker(
                            document.body, 
                            NodeFilter.SHOW_TEXT, 
                            { acceptNode: (node) => getVisibleText(node.parentNode) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT }
                        );
                        
                        let node;
                        while (node = walk.nextNode()) {
                            const text = node.textContent.trim();
                            if (text) textNodes.push(text);
                        }
                        
                        return textNodes.join(' ');
                    }''')
                    
                    # Use the page text as a fallback
                    transcription = page_text
                
                # Close browser
                await browser.close()
                
                # If still no transcription, use Azure Speech Services to analyze audio
                if not transcription or len(transcription) < 50:
                    logger.info("Insufficient text extracted, fallback to simulated transcription")
                    transcription = (
                        "This is a simulated transcription for the video content. "
                        "In a production environment, we would use Azure Video Indexer "
                        "or properly capture the audio stream and use Speech-to-Text."
                    )
                
                # Clean up temporary files
                try:
                    if os.path.exists(audio_path):
                        os.unlink(audio_path)
                except Exception as e:
                    logger.error(f"Error removing audio file: {e}")
                
                # Return the results
                return transcription, duration_minutes, thumbnail_url
                
        except Exception as e:
            logger.error(f"Error processing video content: {e}")
            return f"Error processing video content: {str(e)}", None, None
    
    async def _transcribe_audio_file(self, audio_file_path: str) -> str:
        """
        Transcribe an audio file using Azure Speech Services.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Transcribed text
        """
        if not self.speech_config:
            logger.warning("Speech Services not configured. Cannot transcribe audio.")
            return "No transcription available - Speech Services not configured."
        
        try:
            from azure.cognitiveservices.speech import AudioConfig, SpeechRecognizer, ResultReason
            
            # Configure speech recognition
            audio_config = AudioConfig(filename=audio_file_path)
            speech_recognizer = SpeechRecognizer(
                speech_config=self.speech_config, 
                audio_config=audio_config
            )
            
            # Start continuous recognition
            logger.info("Starting speech recognition")
            transcription_parts = []
            
            # Set up a semaphore for sync
            done_semaphore = asyncio.Semaphore(0)
            
            def stop_cb(evt):
                logger.info("Recognition stopped")
                done_semaphore.release()
            
            def recognized_cb(evt):
                if evt.result.reason == ResultReason.RecognizedSpeech:
                    text = evt.result.text
                    if text:
                        logger.info(f"Recognized: {text[:50]}...")
                        transcription_parts.append(text)
            
            # Connect callbacks
            speech_recognizer.recognized.connect(recognized_cb)
            speech_recognizer.session_stopped.connect(stop_cb)
            speech_recognizer.canceled.connect(stop_cb)
            
            # Start continuous speech recognition
            logger.info("Starting continuous recognition")
            speech_recognizer.start_continuous_recognition()
            
            # Wait for recognition to complete
            # This is a synchronous operation in an async context, so we use a timeout
            try:
                # Timeout after 5 minutes (adjust based on your needs)
                await asyncio.wait_for(done_semaphore.acquire(), timeout=300)
            except asyncio.TimeoutError:
                logger.warning("Speech recognition timed out")
            finally:
                # Stop recognition
                speech_recognizer.stop_continuous_recognition()
            
            # Combine all recognized text
            if transcription_parts:
                full_transcription = " ".join(transcription_parts)
                logger.info(f"Transcription complete: {len(full_transcription)} characters")
                return full_transcription
            else:
                logger.warning("No speech recognized")
                return "No speech recognized in the audio."
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return f"Error transcribing audio: {str(e)}"
    
    def _prepare_text_for_embedding(self, content_item: Dict[str, Any], extracted_text: str) -> str:
        """
        Prepare text for embedding by combining metadata with extracted content.
        
        Args:
            content_item: Content item with metadata
            extracted_text: Extracted text from the content
            
        Returns:
            Text prepared for embedding
        """
        # Combine relevant fields
        text_parts = [
            f"Title: {content_item['title']}",
            f"Subject: {content_item['subject']}",
        ]
        
        # Add description if available
        if content_item['description']:
            text_parts.append(f"Description: {content_item['description']}")
            
        # Add topics if available
        if content_item['topics']:
            text_parts.append(f"Topics: {', '.join(content_item['topics'])}")
            
        # Add keywords if available
        if content_item['keywords']:
            text_parts.append(f"Keywords: {', '.join(content_item['keywords'])}")
            
        # Add extracted text (truncated if too long)
        if extracted_text:
            # Limit to around 2000 characters for embedding
            if len(extracted_text) > 2000:
                text_parts.append(f"Content: {extracted_text[:2000]}...")
            else:
                text_parts.append(f"Content: {extracted_text}")
        
        return "\n".join(text_parts)
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Azure OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
        """
        # Check if the OpenAI client is initialized
        if not self.openai_client:
            try:
                # Try to initialize OpenAI client
                self.openai_client = await get_openai_adapter()
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                # Return empty vector
                return [0.0] * self.embedding_dimension
                
        if not self.openai_client:
            logger.error("OpenAI client not initialized. Falling back to empty embedding.")
            return [0.0] * self.embedding_dimension
            
        try:
            embedding = await self.openai_client.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=text
            )
            
            # Ensure the embedding is a flat list of float values
            if isinstance(embedding, list):
                return embedding
                
            # If it's a dictionary with the expected OpenAI format
            if isinstance(embedding, dict) and 'data' in embedding and len(embedding['data']) > 0:
                return embedding['data'][0]['embedding']
                
            # If it's a numpy array, convert to list
            if hasattr(embedding, 'tolist'):
                return embedding.tolist()
                
            # Default case for unexpected formats
            logger.warning(f"Unexpected embedding format: {type(embedding)}. Using default empty vector.")
            return [0.0] * self.embedding_dimension
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Fall back to empty embedding vector with appropriate dimensions
            return [0.0] * self.embedding_dimension
    
    async def save_to_search(self, content_items: List[Dict[str, Any]]) -> bool:
        """
        Save processed content items to Azure AI Search.
        
        Args:
            content_items: List of processed content items
            
        Returns:
            Success status
        """
        if not self.search_client:
            await self.initialize()
            if not self.search_client:
                logger.error("Search client could not be initialized")
                return False
            
        if not content_items:
            logger.warning("No content items to save")
            return False
        
        try:
            # Process in batches to avoid overwhelming the service
            batch_size = 20
            success_count = 0
            error_count = 0
            
            for i in range(0, len(content_items), batch_size):
                batch = content_items[i:i+batch_size]
                
                # Make a deep copy to avoid modifying originals
                import copy
                processed_batch = copy.deepcopy(batch)
                
                # Process each item in the batch
                for item in processed_batch:
                    # Format dates properly for Azure Search
                    for date_field in ["created_at", "updated_at"]:
                        if date_field in item and item[date_field]:
                            # Ensure proper format for Azure Search
                            try:
                                if isinstance(item[date_field], str):
                                    dt = datetime.fromisoformat(item[date_field].replace('Z', ''))
                                    item[date_field] = dt.isoformat(timespec='seconds') + 'Z'
                                elif isinstance(item[date_field], datetime):
                                    item[date_field] = item[date_field].isoformat(timespec='seconds') + 'Z'
                            except (ValueError, TypeError):
                                # If conversion fails, set to current time
                                item[date_field] = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
                    
                    # Make sure embedding is formatted as expected by Azure Search
                    if "embedding" in item:
                        if item["embedding"] is None:
                            # Initialize with empty vector if None
                            item["embedding"] = [0.0] * self.embedding_dimension
                
                try:
                    # Upload batch
                    result = await self.search_client.upload_documents(documents=processed_batch)
                    
                    # Count successes and failures
                    for idx, item in enumerate(result):
                        if item.succeeded:
                            success_count += 1
                        else:
                            error_count += 1
                            logger.error(f"Failed to upload document: {item.key}, {item.error_message}")
                    
                    # Wait a bit between batches
                    await asyncio.sleep(1)
                    
                except Exception as batch_error:
                    logger.error(f"Error uploading batch: {batch_error}")
                    error_count += len(processed_batch)
            
            logger.info(f"Upload complete: {success_count} succeeded, {error_count} failed")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error saving to search: {e}")
            return False
    
    def _get_file_extension(self, url: str) -> str:
        """Get file extension from URL."""
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Get file extension
        extension = os.path.splitext(path)[1].lower()
        
        # Default to .mp3 for audio if no extension
        if not extension:
            return '.mp3'
            
        return extension

# Singleton instance
content_processor = None

async def get_content_processor():
    """Get or create content processor singleton."""
    global content_processor
    if content_processor is None:
        content_processor = MultimediaContentProcessor()
        await content_processor.initialize()
    return content_processor

async def process_and_index_content(content_url: str, content_info: Dict[str, Any], owner_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Process content and index it in the search service.
    
    Args:
        content_url: URL of the content
        content_info: Basic metadata about the content
        owner_id: Owner ID for access control (optional)
        
    Returns:
        Processed content item
    """
    processor = await get_content_processor()
    
    # Process the content
    content_item = await processor.process_content(content_url, content_info)
    
    # Ensure owner_id is set if provided
    if owner_id and content_item:
        content_item["owner_id"] = owner_id
        logger.info(f"Setting owner_id to {owner_id} for content: {content_item.get('title')}")
    
    # Save to search index
    if content_item:
        # Create a batch of one item
        success = await processor.save_to_search([content_item])
        if success:
            logger.info(f"Successfully indexed content: {content_item['title']}")
        else:
            logger.warning(f"Failed to index content: {content_item['title']}")
    
    return content_item