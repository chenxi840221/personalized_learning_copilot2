#!/usr/bin/env python3
"""Script to clear the student-reports index in Azure AI Search."""
import asyncio
import logging
import sys
import os
import json
import aiohttp

# Fix import paths for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)  # Add backend to path
sys.path.insert(0, project_root)  # Add project root to path

# Import settings
from config.settings import Settings
settings = Settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define API version
API_VERSION = "2023-07-01-Preview"

async def clear_index():
    """Delete the student-reports index and recreate it."""
    if not settings.AZURE_SEARCH_ENDPOINT or not settings.AZURE_SEARCH_KEY:
        logger.error("Azure AI Search settings not configured")
        return False
    
    # Check if index name is configured
    index_name = settings.REPORTS_INDEX_NAME
    if not index_name:
        logger.error("Reports index name not configured")
        return False

    try:
        # Delete the index
        logger.info(f"Deleting index: {index_name}")
        
        # Define headers
        headers = {
            "Content-Type": "application/json",
            "api-key": settings.AZURE_SEARCH_KEY
        }
        
        # Delete the index
        delete_url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{index_name}?api-version={API_VERSION}"
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(delete_url, headers=headers) as response:
                if response.status in (200, 204):
                    logger.info(f"Successfully deleted index: {index_name}")
                elif response.status == 404:
                    logger.info(f"Index {index_name} does not exist")
                else:
                    text = await response.text()
                    logger.error(f"Failed to delete index: {response.status} - {text}")
                    return False
        
        # Recreate the index
        logger.info(f"Recreating index: {index_name}")
        try:
            # Import the index creation script
            try:
                from update_report_index import update_student_reports_index
                success = update_student_reports_index()
            except ImportError:
                # Try alternative import path
                from scripts.update_report_index import update_student_reports_index
                success = update_student_reports_index()
                
            if success:
                logger.info(f"Successfully recreated index: {index_name}")
                return True
            else:
                logger.error(f"Failed to recreate index: {index_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error recreating index: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Error clearing index: {e}")
        return False

if __name__ == "__main__":
    if asyncio.run(clear_index()):
        logger.info("Index cleared and recreated successfully")
    else:
        logger.error("Failed to clear and recreate index")
        sys.exit(1)