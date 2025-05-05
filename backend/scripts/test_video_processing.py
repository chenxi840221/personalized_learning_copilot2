#!/usr/bin/env python3
"""
Test script for video processing and indexing functionality.
This script will process a video URL, extract audio, transcribe it, and index it with captions.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)

# Now we can properly import from the backend package
from backend.scrapers.video_processor import process_video_content
from backend.utils.vector_store import get_vector_store

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)

async def test_video_processing(url: str, output_file: str = None, args=None):
    """Process a video URL and print the results."""
    logger.info(f"Processing video: {url}")
    
    # Process the video
    result = await process_video_content(url)
    
    # Display transcription information if available
    if "captions" in result:
        captions = result.get("captions", {})
        full_text = captions.get("full_text", "")
        segments = captions.get("segments", [])
        
        # Check if we should show the full transcript
        if full_text:
            show_transcript = False
            if hasattr(args, 'show_transcript') and args.show_transcript:
                show_transcript = True
                
            if show_transcript:
                logger.info("================ FULL TRANSCRIPT ================")
                logger.info(full_text)
                logger.info("================================================")
            else:
                logger.info(f"Transcription extracted (first 200 chars): {full_text[:200]}...")
                logger.info(f"Total transcription length: {len(full_text)} characters")
                logger.info("(Use --show-transcript to view the entire transcript)")
                
        if segments:
            logger.info(f"Extracted {len(segments)} caption segments")
            # Show the first few segments as example
            max_segments_to_show = 10 if hasattr(args, 'show_transcript') and args.show_transcript else 3
            
            for i, segment in enumerate(segments[:max_segments_to_show]):
                start = segment.get("start_time", 0)
                end = segment.get("end_time", 0)
                text = segment.get("text", "")
                logger.info(f"Segment {i+1}: [{start:.2f}s - {end:.2f}s] {text}")
                
            if len(segments) > max_segments_to_show:
                logger.info(f"... and {len(segments) - max_segments_to_show} more segments")
    
    # Save the result to a file if specified
    if output_file:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        # Write results to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Saved processing results to {output_file}")
    
    # Return success status
    return result.get("processed", False)

async def index_video_with_captions(url: str, subject: str = "Testing"):
    """Process a video and index it with captions in Azure Search."""
    logger.info(f"Processing and indexing video: {url}")
    
    # Process the video
    video_result = await process_video_content(url)
    
    if not video_result.get("processed", False):
        logger.error(f"Video processing failed for {url}")
        return False
    
    # Get video properties
    title = video_result.get("title", "Unknown Video")
    description = video_result.get("description", "")
    
    # Get duration and convert to integer (Azure Search expects Int32)
    duration_float = video_result.get("duration_minutes", 0)
    duration = int(round(duration_float))  # Convert to integer
    
    # Extract transcription
    captions = video_result.get("captions", {})
    transcription = captions.get("full_text", "")
    caption_segments = captions.get("segments", [])
    
    # Prepare content item for indexing
    content_item = {
        "id": video_result.get("id", f"video-{int(datetime.now().timestamp())}"),
        "title": title,
        "description": description,
        "content_type": "video",
        "subject": subject,
        "url": url,
        "difficulty_level": "intermediate",
        "grade_level": [7, 8, 9],  # Default grade levels
        "duration_minutes": duration,
        # Format datetime without microseconds for Azure Search compatibility
        "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Add metadata
        "metadata": {
            "video_url": url,
            "video_platform": "test",
            "transcription": transcription[:10000] if transcription else ""  # Limit size
        },
        # Add flattened metadata for Azure Search
        "metadata_transcription": transcription[:10000] if transcription else "",
        # Add captions
        "captions": [
            {
                "text": segment.get("text", ""),
                "start_time": segment.get("start_time", 0),
                "end_time": segment.get("end_time", 0)
            }
            for segment in caption_segments if segment.get("text")
        ]
    }
    
    # Create page content with transcription
    content_item["page_content"] = f"""
    Title: {title}
    Subject: {subject}
    Description: {description}
    Content Type: video
    Video URL: {url}
    
    Transcription:
    {transcription[:5000]}
    """
    
    # Get vector store
    vector_store = await get_vector_store()
    
    # Add to vector store
    success = await vector_store.add_content(content_item)
    
    if success:
        logger.info(f"Successfully indexed video with captions: {title}")
    else:
        logger.error(f"Failed to index video: {title}")
    
    return success

async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test video processing and indexing")
    parser.add_argument("url", nargs="?", help="URL of the video to process")
    parser.add_argument("--url", dest="url_option", help="URL of the video to process")
    parser.add_argument("--subject", default="Testing", help="Subject for the video content")
    parser.add_argument("--output", help="Output file to save processing results (JSON)")
    parser.add_argument("--index", action="store_true", help="Index the video in Azure Search")
    parser.add_argument("--speech-test", action="store_true", help="Use a test file with speech to verify transcription")
    parser.add_argument("--show-transcript", action="store_true", help="Display full transcript in console output")
    parser.add_argument("--extract-all", action="store_true", help="Extract all video information including search for video URLs")
    
    args = parser.parse_args()
    
    # Determine the URL to use
    process_url = None
    
    # For speech test, directly use the sample that worked before
    if args.speech_test:
        logger.info("Using known sample MP4 URL for transcription testing")
        # Hard-coded working video URL that we know works
        process_url = "https://www.learningcontainer.com/wp-content/uploads/2020/05/sample-mp4-file.mp4"
    else:
        # Check positional URL argument first
        if args.url:
            process_url = args.url
        # Then check --url option
        elif args.url_option:
            process_url = args.url_option
        else:
            logger.error("URL is required when not using --speech-test")
            logger.error("Provide a URL either as a positional argument or with --url")
            return False
            
    # Process the video with the determined URL
    logger.info(f"Processing URL: {process_url}")
    success = await test_video_processing(process_url, args.output, args)
    
    if success and args.index:
        # Use the appropriate URL for indexing
        if args.speech_test:
            index_url = "https://www.learningcontainer.com/wp-content/uploads/2020/05/sample-mp4-file.mp4"
        else:
            index_url = process_url
        
        # Index the video with captions
        indexed = await index_video_with_captions(index_url, args.subject)
        if indexed:
            logger.info("Video successfully processed and indexed with captions")
        else:
            logger.error("Video was processed but indexing failed")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())