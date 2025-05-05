"""
Simple script to list all unique subjects in the educational-content index.
To run: python scripts/list_subjects.py
"""
import asyncio
import logging
import os
import sys
from typing import List, Set

# Add the project root to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)

sys.path.insert(0, backend_dir)  # Also add backend dir to path

from config.settings import Settings
from services.search_service import get_search_service

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def get_unique_subjects() -> Set[str]:
    """
    Get a list of all unique subjects in the educational-content index.
    
    Returns:
        Set of unique subject names
    """
    settings = Settings()
    content_index_name = settings.CONTENT_INDEX_NAME or "educational-content"
    
    try:
        # Get search service
        search_service = await get_search_service()
        
        logger.info(f"Using content index: {content_index_name}")
        
        # Search for all documents, but only retrieve the subject field
        all_content = await search_service.search_documents(
            index_name=content_index_name,
            query="*",
            top=1000,  # Increase if you have more than 1000 documents
            select="subject"
        )
        
        # Extract unique subjects
        subjects = set()
        for item in all_content:
            if "subject" in item and item["subject"]:
                subjects.add(item["subject"])
        
        return subjects
        
    except Exception as e:
        logger.error(f"Error getting subjects: {e}")
        return set()

async def main():
    """Main function."""
    logger.info("Getting list of unique subjects in educational-content index...")
    
    subjects = await get_unique_subjects()
    
    if subjects:
        logger.info(f"Found {len(subjects)} unique subjects:")
        for subject in sorted(subjects):
            logger.info(f"  - {subject}")
    else:
        logger.warning("No subjects found or an error occurred.")

if __name__ == "__main__":
    asyncio.run(main())