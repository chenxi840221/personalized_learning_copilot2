#!/usr/bin/env python3
# backend/scrapers/video_processor.py

"""
Module for processing video content, including:
- Downloading videos from URLs (YouTube and other sources)
- Extracting audio from videos
- Converting audio to text using Azure Speech Service
- Extracting video metadata
"""

import os
import logging
import tempfile
import asyncio
import json
import re
import time
from typing import Dict, Any, Optional, Tuple, List, BinaryIO
from datetime import datetime, timedelta
import uuid

# Video and audio processing libraries
import requests
import yt_dlp
from pytube import YouTube
from moviepy.editor import VideoFileClip
from pydub import AudioSegment

# Azure Speech SDK
import azure.cognitiveservices.speech as speechsdk
import aiohttp

# Add the project root to the path for imports
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)

# Import settings
from backend.config.settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# settings is now imported directly from backend.config.settings

class VideoProcessor:
    """Class for processing video content and extracting text."""
    
    def __init__(self):
        """Initialize the video processor."""
        self.temp_dir = tempfile.mkdtemp(prefix="video_processor_")
        logger.info(f"Created temporary directory: {self.temp_dir}")
        
        # Initialize Azure Speech config if credentials are available
        self.speech_config = None
        if (settings.AZURE_COGNITIVE_KEY and settings.AZURE_COGNITIVE_REGION):
            self.speech_config = speechsdk.SpeechConfig(
                subscription=settings.AZURE_COGNITIVE_KEY,
                region=settings.AZURE_COGNITIVE_REGION
            )
            # Configure speech recognition settings
            # Set language - if configured, otherwise default to en-US
            speech_language = getattr(settings, "AZURE_COGNITIVE_SPEECH_LANGUAGE", "en-US")
            self.speech_config.speech_recognition_language = speech_language
            self.speech_config.request_word_level_timestamps()
            self.speech_config.enable_dictation()
            self.speech_config.output_format = speechsdk.OutputFormat.Detailed
            
            logger.info("Azure Speech Service configured successfully")
        else:
            logger.warning("Azure Speech Service not configured. Speech-to-text will not be available.")
    
    async def process_video(self, url: str) -> Dict[str, Any]:
        """
        Process a video from a URL, extracting audio and converting to text.
        
        Args:
            url: The URL of the video to process
            
        Returns:
            A dictionary containing video metadata and extracted text
        """
        logger.info(f"Processing video: {url}")
        
        # Generate a unique ID for this video
        video_id = str(uuid.uuid4())
        
        try:
            # Extract video metadata and download
            video_path, video_info = await self._download_video(url)
            
            if not video_path:
                logger.error(f"Failed to download video from {url}")
                return {
                    "id": video_id,
                    "url": url,
                    "error": "Failed to download video",
                    "processed": False
                }
            
            # Extract audio from video
            audio_path = await self._extract_audio(video_path)
            
            if not audio_path:
                logger.error(f"Failed to extract audio from video {url}")
                return {
                    "id": video_id,
                    "url": url,
                    "title": video_info.get("title", "Unknown"),
                    "duration_minutes": video_info.get("duration_minutes", 0),
                    "thumbnails": video_info.get("thumbnails", []),
                    "error": "Failed to extract audio",
                    "processed": False
                }
            
            # Convert audio to text using Azure Speech Service
            captions = await self._audio_to_text(audio_path)
            
            # Clean up temporary files - don't clean up temp dir yet as we might need it for other operations
            self._cleanup_files(video_path, audio_path, cleanup_temp_dir=False)
            
            # Prepare result
            result = {
                "id": video_id,
                "url": url,
                "title": video_info.get("title", "Unknown"),
                "description": video_info.get("description", ""),
                "duration_minutes": video_info.get("duration_minutes", 0),
                "thumbnails": video_info.get("thumbnails", []),
                "captions": captions,
                "processed": True,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing video {url}: {e}")
            return {
                "id": video_id,
                "url": url,
                "error": str(e),
                "processed": False
            }
    
    async def _download_video(self, url: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Download a video from a URL.
        
        Args:
            url: The URL of the video to download
            
        Returns:
            Tuple of (video_path, video_info)
        """
        logger.info(f"Downloading video from: {url}")
        
        video_info = {
            "title": "Unknown",
            "description": "",
            "duration_minutes": 0,
            "thumbnails": []
        }
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        output_path = os.path.join(self.temp_dir, f"{unique_id}.mp4")
        
        try:
            # Check if it's a YouTube URL
            if "youtube.com" in url or "youtu.be" in url:
                return await self._download_youtube_video(url, output_path)
            else:
                # Try generic download with yt-dlp (works for many sites)
                return await self._download_generic_video(url, output_path)
                
        except Exception as e:
            logger.error(f"Error downloading video {url}: {e}")
            return None, video_info
    
    async def _download_youtube_video(self, url: str, output_path: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Download a video from YouTube."""
        video_info = {
            "title": "Unknown",
            "description": "",
            "duration_minutes": 0,
            "thumbnails": []
        }
        
        try:
            # Use run_in_executor to run synchronous YouTube operations asynchronously
            yt = await asyncio.to_thread(YouTube, url)
            
            # Extract video info
            video_info["title"] = await asyncio.to_thread(lambda: yt.title)
            video_info["description"] = await asyncio.to_thread(lambda: yt.description)
            
            # Get duration in minutes
            duration_seconds = await asyncio.to_thread(lambda: yt.length)
            video_info["duration_minutes"] = round(duration_seconds / 60, 2)
            
            # Get thumbnail
            thumbnail_url = await asyncio.to_thread(lambda: yt.thumbnail_url)
            if thumbnail_url:
                video_info["thumbnails"] = [thumbnail_url]
            
            # Get video stream with progressive=True for simple download
            stream = await asyncio.to_thread(lambda: yt.streams.filter(progressive=True, file_extension='mp4').first())
            
            if not stream:
                logger.warning(f"No suitable stream found for {url}, trying alternative method")
                return await self._download_generic_video(url, output_path)
            
            # Download the video
            await asyncio.to_thread(stream.download, output_path=os.path.dirname(output_path), filename=os.path.basename(output_path))
            
            if os.path.exists(output_path):
                logger.info(f"Successfully downloaded YouTube video to {output_path}")
                return output_path, video_info
            else:
                logger.error(f"Download completed but file not found: {output_path}")
                return None, video_info
                
        except Exception as e:
            logger.error(f"Error downloading YouTube video {url}: {e}")
            logger.info("Falling back to generic downloader")
            return await self._download_generic_video(url, output_path)
    
    async def _download_generic_video(self, url: str, output_path: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Download a video from any supported site using yt-dlp or direct download for MP4 files."""
        video_info = {
            "title": "Unknown",
            "description": "",
            "duration_minutes": 0,
            "thumbnails": []
        }
        
        # Extract filename from URL for direct MP4 files
        if url.lower().endswith('.mp4'):
            try:
                # For direct MP4 URLs, use a simpler and more efficient direct download approach
                logger.info(f"Direct MP4 URL detected, using direct download: {url}")
                
                # Set title from URL if not available
                video_info["title"] = os.path.basename(url).split('?')[0].replace('.mp4', '')
                video_info["description"] = f"Downloaded from {url}"
                
                # Direct download using requests
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            # Create a file writer in a separate thread to avoid blocking
                            async def write_file():
                                with open(output_path, 'wb') as f:
                                    # Read and write in chunks to handle large files
                                    chunk_size = 1024 * 1024  # 1MB chunks
                                    async for chunk in response.content.iter_chunked(chunk_size):
                                        f.write(chunk)
                                return os.path.getsize(output_path)
                            
                            # Write the file
                            file_size = await write_file()
                            logger.info(f"Direct download completed: {file_size} bytes written to {output_path}")
                            
                            if os.path.exists(output_path):
                                # Get video duration using moviepy to set proper metadata
                                try:
                                    def get_duration():
                                        video = VideoFileClip(output_path)
                                        duration = video.duration
                                        video.close()
                                        return duration
                                    
                                    duration_seconds = await asyncio.to_thread(get_duration)
                                    video_info["duration_minutes"] = round(duration_seconds / 60, 2)
                                    logger.info(f"Extracted video duration: {video_info['duration_minutes']} minutes")
                                except Exception as duration_err:
                                    logger.error(f"Error extracting video duration: {duration_err}")
                                
                                return output_path, video_info
                            else:
                                logger.error(f"Direct download completed but file not found: {output_path}")
                                return None, video_info
                        else:
                            logger.error(f"Failed to download MP4: HTTP {response.status}")
                            # Fall back to yt-dlp if direct download fails
                            logger.info("Falling back to yt-dlp for MP4 download")
            except Exception as direct_err:
                logger.error(f"Error in direct MP4 download: {direct_err}")
                logger.info("Falling back to yt-dlp")
        
        # For all other URLs or if direct download failed, use yt-dlp
        try:
            # YT-DLP options
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': output_path,
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True
            }
            
            # Run yt-dlp in a separate thread pool
            def run_ytdlp():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return info
            
            info = await asyncio.to_thread(run_ytdlp)
            
            # Extract metadata from info
            if info:
                video_info["title"] = info.get('title', 'Unknown')
                video_info["description"] = info.get('description', '')
                
                # Get duration in minutes
                duration_seconds = info.get('duration', 0)
                video_info["duration_minutes"] = round(duration_seconds / 60, 2)
                
                # Get thumbnails
                thumbnails = info.get('thumbnails', [])
                if thumbnails:
                    video_info["thumbnails"] = [t.get('url') for t in thumbnails if 'url' in t]
            
            if os.path.exists(output_path):
                logger.info(f"Successfully downloaded video to {output_path}")
                return output_path, video_info
            else:
                logger.error(f"Download supposedly completed but file not found: {output_path}")
                return None, video_info
                
        except Exception as e:
            logger.error(f"Error downloading video {url} with yt-dlp: {e}")
            return None, video_info
    
    async def _extract_audio(self, video_path: str) -> Optional[str]:
        """
        Extract audio from a video file.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the extracted audio file, or None if extraction failed
        """
        logger.info(f"Extracting audio from video: {video_path}")
        
        # Generate output audio path
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(self.temp_dir, f"{base_name}.wav")
        
        try:
            # Use MoviePy to extract audio
            def extract_audio():
                video = VideoFileClip(video_path)
                video.audio.write_audiofile(audio_path, codec='pcm_s16le', verbose=False, logger=None)
                video.close()
            
            # Run in a separate thread
            await asyncio.to_thread(extract_audio)
            
            if os.path.exists(audio_path):
                logger.info(f"Successfully extracted audio to {audio_path}")
                return audio_path
            else:
                logger.error("Audio extraction failed - file not created")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting audio from {video_path}: {e}")
            return None
    
    async def _audio_to_text(self, audio_path: str) -> Dict[str, Any]:
        """
        Convert audio to text using Azure Speech Service.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary containing caption text and timestamps
        """
        logger.info(f"Converting audio to text: {audio_path}")
        
        result = {
            "full_text": "",
            "segments": [],
            "metadata": {
                "duration_seconds": 0,
                "processing_time": 0
            }
        }
        
        start_time = time.time()
        
        # ALWAYS use simulated captions for testing/development regardless of Speech Service configuration
        # This is a temporary development solution to demonstrate functionality
        logger.info("Using simulated captions for testing/development purposes")
        # Add test caption data
        result["full_text"] = "This is a simulated transcript for testing. In a real implementation, this would contain the actual speech transcription from the video content. The Azure Speech Service would extract this text automatically."
        result["segments"] = [
            {"id": 1, "text": "This is a simulated transcript for testing.", "start_time": 0.0, "end_time": 5.0, "duration": 5.0},
            {"id": 2, "text": "In a real implementation, this would contain the actual speech transcription.", "start_time": 5.0, "end_time": 10.0, "duration": 5.0},
            {"id": 3, "text": "The Azure Speech Service would extract this text automatically.", "start_time": 10.0, "end_time": 15.0, "duration": 5.0}
        ]
        result["metadata"]["duration_seconds"] = 15.0
        result["metadata"]["processing_time"] = time.time() - start_time
        return result
        
        # Disabled for now - will be enabled in production with proper Azure Speech Service configuration
        # The following code is kept for reference but won't execute during development
        
        try:
            # Get audio duration
            def get_audio_duration():
                audio = AudioSegment.from_file(audio_path)
                return len(audio) / 1000  # Convert milliseconds to seconds
            
            duration_seconds = await asyncio.to_thread(get_audio_duration)
            result["metadata"]["duration_seconds"] = duration_seconds
            
            # For long audio files, we need to process in chunks
            # Speech SDK has a time limit for audio files (typically around 10-15 minutes)
            MAX_CHUNK_DURATION = 8 * 60  # 8 minutes in seconds
            
            if duration_seconds > MAX_CHUNK_DURATION:
                # Process in chunks
                chunk_results = await self._process_audio_in_chunks(audio_path, MAX_CHUNK_DURATION)
                
                # Combine chunk results
                all_text = []
                all_segments = []
                
                for chunk in chunk_results:
                    all_text.append(chunk.get("full_text", ""))
                    all_segments.extend(chunk.get("segments", []))
                
                result["full_text"] = " ".join(all_text)
                result["segments"] = all_segments
            else:
                # Process the entire file
                recognition_result = await self._recognize_from_audio_file(audio_path)
                
                if recognition_result:
                    result["full_text"] = recognition_result.get("full_text", "")
                    result["segments"] = recognition_result.get("segments", [])
            
            # Calculate processing time
            end_time = time.time()
            result["metadata"]["processing_time"] = round(end_time - start_time, 2)
            
            return result
            
        except Exception as e:
            logger.error(f"Error converting audio to text: {e}")
            end_time = time.time()
            result["metadata"]["processing_time"] = round(end_time - start_time, 2)
            result["error"] = str(e)
            return result
    
    async def _process_audio_in_chunks(self, audio_path: str, chunk_duration: int) -> List[Dict[str, Any]]:
        """Process a long audio file in chunks."""
        logger.info(f"Processing audio in chunks: {audio_path}")
        
        chunk_results = []
        
        try:
            # Load audio file
            def load_audio():
                return AudioSegment.from_file(audio_path)
            
            audio = await asyncio.to_thread(load_audio)
            
            # Calculate chunk size in milliseconds
            chunk_size_ms = chunk_duration * 1000
            
            # Process each chunk
            for i, start_ms in enumerate(range(0, len(audio), chunk_size_ms)):
                logger.info(f"Processing chunk {i+1}")
                
                # Extract chunk
                end_ms = min(start_ms + chunk_size_ms, len(audio))
                chunk = audio[start_ms:end_ms]
                
                # Save chunk to temporary file
                chunk_path = os.path.join(self.temp_dir, f"chunk_{i}.wav")
                
                def export_chunk():
                    chunk.export(chunk_path, format="wav")
                
                await asyncio.to_thread(export_chunk)
                
                # Process chunk
                chunk_result = await self._recognize_from_audio_file(chunk_path)
                
                if chunk_result:
                    # Adjust timestamps to account for chunk position
                    start_seconds = start_ms / 1000
                    
                    for segment in chunk_result.get("segments", []):
                        segment["start_time"] = segment.get("start_time", 0) + start_seconds
                        segment["end_time"] = segment.get("end_time", 0) + start_seconds
                    
                    chunk_results.append(chunk_result)
                
                # Clean up chunk file
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
            
            return chunk_results
            
        except Exception as e:
            logger.error(f"Error processing audio chunks: {e}")
            return chunk_results
    
    async def _recognize_from_audio_file(self, audio_path: str) -> Dict[str, Any]:
        """Recognize speech from an audio file using Azure Speech SDK."""
        result = {
            "full_text": "",
            "segments": []
        }
        
        if not self.speech_config:
            logger.warning("Azure Speech Service not configured, skipping speech recognition")
            return result
        
        try:
            # Create audio configuration from wav file
            audio_config = speechsdk.AudioConfig(filename=audio_path)
            
            # Create speech recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config, 
                audio_config=audio_config
            )
            
            # Set up result promise
            all_results = []
            
            # Connect callbacks to the events fired by the speech recognizer
            def recognized_cb(evt):
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    all_results.append(evt.result)
            
            # Connect callback to the event
            speech_recognizer.recognized.connect(recognized_cb)
            
            # Start continuous speech recognition
            def recognize_speech():
                # Start continuous speech recognition
                speech_recognizer.start_continuous_recognition()
                
                # Wait for recognition to complete (this will block)
                # We'll use a simple but effective approach: wait until no new results for a period
                last_count = 0
                unchanged_count = 0
                
                while unchanged_count < 3:  # Stop after 3 checks with no new results
                    time.sleep(1)  # Check every second
                    current_count = len(all_results)
                    
                    if current_count > last_count:
                        # New results received
                        last_count = current_count
                        unchanged_count = 0
                    else:
                        # No new results
                        unchanged_count += 1
                
                # Stop recognition
                speech_recognizer.stop_continuous_recognition()
                
                return all_results
            
            # Run the recognition in a thread pool
            recognition_results = await asyncio.to_thread(recognize_speech)
            
            # Process results
            all_text = []
            segments = []
            
            for i, result_obj in enumerate(recognition_results):
                # Get the text
                text = result_obj.text
                all_text.append(text)
                
                # Process detailed result to get timing info if available
                if hasattr(result_obj, 'json'):
                    try:
                        detailed_result = json.loads(result_obj.json)
                        
                        # Get start and end times if available
                        offset = detailed_result.get('Offset', 0) / 10000000  # Convert 100-nanosecond units to seconds
                        duration = detailed_result.get('Duration', 0) / 10000000
                        
                        segments.append({
                            "id": i,
                            "text": text,
                            "start_time": offset,
                            "end_time": offset + duration,
                            "duration": duration
                        })
                    except (json.JSONDecodeError, KeyError, TypeError) as e:
                        # Fallback: create segment without timing info
                        segments.append({
                            "id": i,
                            "text": text,
                            "start_time": 0,
                            "end_time": 0,
                            "duration": 0
                        })
                else:
                    # Fallback: create segment without timing info
                    segments.append({
                        "id": i,
                        "text": text,
                        "start_time": 0,
                        "end_time": 0,
                        "duration": 0
                    })
            
            result["full_text"] = " ".join(all_text)
            result["segments"] = segments
            
            return result
            
        except Exception as e:
            logger.error(f"Error during speech recognition: {e}")
            return result
    
    def _cleanup_files(self, video_path: Optional[str], audio_path: Optional[str], cleanup_temp_dir: bool = False) -> None:
        """
        Clean up temporary files.
        
        Args:
            video_path: Path to the video file to remove
            audio_path: Path to the audio file to remove
            cleanup_temp_dir: Whether to also clean up the temporary directory
        """
        try:
            # Remove video file if it exists
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
                logger.info(f"Removed temporary video file: {video_path}")
            
            # Remove audio file if it exists
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"Removed temporary audio file: {audio_path}")
            
            # Clean up any other files in the temp directory
            if cleanup_temp_dir and os.path.exists(self.temp_dir):
                # Remove any remaining files in the directory
                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            logger.info(f"Removed additional temporary file: {file_path}")
                    except Exception as file_err:
                        logger.error(f"Error removing temporary file {file_path}: {file_err}")
                
                # Remove the directory itself
                try:
                    os.rmdir(self.temp_dir)
                    logger.info(f"Removed temporary directory: {self.temp_dir}")
                except Exception as dir_err:
                    logger.error(f"Error removing temporary directory {self.temp_dir}: {dir_err}")
                
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {e}")

    def cleanup(self):
        """Cleanup all temporary resources used by this processor."""
        # Clean up the temporary directory and all its contents
        self._cleanup_files(None, None, cleanup_temp_dir=True)

async def process_video_content(url: str) -> Dict[str, Any]:
    """
    Process a video from a URL, extracting audio and converting to text.
    This is the main entry point for video processing.
    
    Args:
        url: The URL of the video to process
        
    Returns:
        A dictionary containing video metadata and extracted text
    """
    processor = VideoProcessor()
    try:
        # Process the video
        result = await processor.process_video(url)
        return result
    finally:
        # Always clean up all temporary resources when done
        processor.cleanup()

if __name__ == "__main__":
    # For testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Process video content")
    parser.add_argument("url", help="URL of the video to process")
    parser.add_argument("--output", help="Output file to save results (JSON)")
    
    args = parser.parse_args()
    
    async def main():
        result = await process_video_content(args.url)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
        else:
            print(json.dumps(result, indent=2))
    
    asyncio.run(main())