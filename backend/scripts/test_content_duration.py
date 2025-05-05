#!/usr/bin/env python3
"""
Script to check duration_minutes in Azure AI Search educational-content index
Counts how many documents have NULL duration_minutes
"""

import asyncio
import sys
import os
import logging
from collections import Counter

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.search_service import get_search_service
from config.settings import Settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_content_durations():
    # Get settings
    settings = Settings()
    
    # Get search service
    search_service = await get_search_service()
    if not search_service:
        logger.error("Unable to initialize search service")
        return
    
    # Get content index name from settings
    content_index_name = settings.CONTENT_INDEX_NAME
    logger.info(f"Checking duration_minutes in index: {content_index_name}")
    
    # Attempt to search all documents to analyze duration_minutes
    try:
        # Get all documents (paginate through results as needed)
        results = []
        page_size = 100
        skip = 0
        total_documents = 0
        
        while True:
            # Query for a page of results
            page_results = await search_service.search_documents(
                index_name=content_index_name,
                query="*",
                select="id,title,duration_minutes,content_type,subject",
                top=page_size,
                skip=skip
            )
            
            if not page_results:
                break
                
            page_count = len(page_results)
            total_documents += page_count
            results.extend(page_results)
            
            logger.info(f"Retrieved {page_count} documents, total so far: {total_documents}")
            
            if page_count < page_size:
                break
                
            skip += page_size
        
        # Analyze the results
        null_durations = 0
        zero_durations = 0
        negative_durations = 0
        valid_durations = 0
        duration_stats = {"min": None, "max": None, "avg": 0}
        duration_values = []
        content_type_stats = Counter()
        subject_stats = Counter()
        content_type_duration_stats = {}
        
        for doc in results:
            # Count by content type
            content_type = doc.get("content_type", "unknown")
            content_type_stats[content_type] += 1
            
            # Count by subject
            subject = doc.get("subject", "unknown")
            subject_stats[subject] += 1
            
            # Check duration_minutes
            duration = doc.get("duration_minutes")
            
            if duration is None:
                null_durations += 1
                # Track content types with null durations
                if content_type not in content_type_duration_stats:
                    content_type_duration_stats[content_type] = {"null": 0, "valid": 0}
                content_type_duration_stats[content_type]["null"] += 1
            else:
                # Try to convert to integer
                try:
                    duration_value = int(duration)
                    if duration_value == 0:
                        zero_durations += 1
                    elif duration_value < 0:
                        negative_durations += 1
                    else:
                        valid_durations += 1
                        duration_values.append(duration_value)
                        
                        # Track stats for valid durations
                        if duration_stats["min"] is None or duration_value < duration_stats["min"]:
                            duration_stats["min"] = duration_value
                        if duration_stats["max"] is None or duration_value > duration_stats["max"]:
                            duration_stats["max"] = duration_value
                            
                        # Track content types with valid durations
                        if content_type not in content_type_duration_stats:
                            content_type_duration_stats[content_type] = {"null": 0, "valid": 0}
                        content_type_duration_stats[content_type]["valid"] += 1
                except (ValueError, TypeError):
                    null_durations += 1
        
        # Calculate average for valid durations
        if duration_values:
            duration_stats["avg"] = sum(duration_values) / len(duration_values)
            
        # Print the results
        logger.info(f"\n===== DURATION ANALYSIS RESULTS =====")
        logger.info(f"Total documents analyzed: {total_documents}")
        logger.info(f"Documents with NULL duration_minutes: {null_durations} ({null_durations / total_documents * 100:.2f}%)")
        logger.info(f"Documents with ZERO duration_minutes: {zero_durations} ({zero_durations / total_documents * 100:.2f}%)")
        logger.info(f"Documents with NEGATIVE duration_minutes: {negative_durations} ({negative_durations / total_documents * 100:.2f}%)")
        logger.info(f"Documents with VALID duration_minutes: {valid_durations} ({valid_durations / total_documents * 100:.2f}%)")
        
        if valid_durations > 0:
            logger.info(f"\nValid duration_minutes statistics:")
            logger.info(f"  Min duration: {duration_stats['min']} minutes")
            logger.info(f"  Max duration: {duration_stats['max']} minutes")
            logger.info(f"  Avg duration: {duration_stats['avg']:.2f} minutes")
        
        # Content type breakdown
        logger.info(f"\nContent type breakdown:")
        for content_type, count in content_type_stats.most_common():
            stats = content_type_duration_stats.get(content_type, {"null": 0, "valid": 0})
            null_percent = stats["null"] / count * 100 if count > 0 else 0
            valid_percent = stats["valid"] / count * 100 if count > 0 else 0
            logger.info(f"  {content_type}: {count} documents, {stats['null']} NULL ({null_percent:.2f}%), {stats['valid']} valid ({valid_percent:.2f}%)")
        
        # Subject breakdown
        logger.info(f"\nTop 5 subjects:")
        for subject, count in subject_stats.most_common(5):
            logger.info(f"  {subject}: {count} documents")
        
        # Return the null duration count for use elsewhere
        return null_durations, total_documents
            
    except Exception as e:
        logger.error(f"Error checking content durations: {e}")
        return None, 0

if __name__ == "__main__":
    results = asyncio.run(check_content_durations())
    if results:
        null_count, total_count = results
        print(f"\nSUMMARY: {null_count} out of {total_count} documents have NULL duration_minutes")