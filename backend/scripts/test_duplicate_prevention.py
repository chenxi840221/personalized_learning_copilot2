#!/usr/bin/env python3
"""
Test script to verify that the duplicate prevention logic works correctly.
This script will add the same content twice to the vector store and verify
that it doesn't create duplicates.
"""

import os
import sys
import asyncio
import logging
import json
import uuid
from datetime import datetime

# Add the project root to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)  # Add project root first

# Now we can properly import from the backend package
from backend.utils.vector_store import get_vector_store
from backend.config.settings import Settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)

async def test_duplicate_prevention():
    """
    Tests that the same content doesn't get added twice to Azure Search.
    """
    logger.info("Starting duplicate prevention test")
    
    # Get the vector store
    vector_store = await get_vector_store()
    
    # Create a test content item with URL for consistent ID generation
    url = "https://example.com/test-duplicate-prevention"
    content_item = {
        "url": url,
        "title": "Test Duplicate Prevention",
        "description": "This is a test to verify that the same content doesn't get added twice.",
        "subject": "Programming",
        "content_type": "article",
        "page_content": "This is the content of the test document.",
        "difficulty_level": "intermediate",
        "grade_level": [9, 10, 11],
        "topics": ["Testing", "Vector Search", "Duplicate Prevention"],
        "keywords": ["test", "duplicate", "prevention", "vector"],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # First attempt to add the content
    logger.info("First attempt to add content")
    success1 = await vector_store.add_content(content_item)
    logger.info(f"First attempt result: {success1}")
    
    # Wait a bit to ensure the first add completes
    await asyncio.sleep(2)
    
    # Second attempt to add the same content
    logger.info("Second attempt to add the same content")
    success2 = await vector_store.add_content(content_item)
    logger.info(f"Second attempt result: {success2}")
    
    # Wait a bit to ensure the second add completes
    await asyncio.sleep(2)
    
    # Try to filter search to find any documents with this URL
    filter_expr = f"url eq '{url}'"
    results = await vector_store.filter_search(filter_expr)
    
    if len(results) == 1:
        logger.info("SUCCESS: Only one document found with the test URL. Duplicate prevention is working!")
    else:
        logger.error(f"FAILURE: Found {len(results)} documents with the test URL. Duplicate prevention is NOT working.")
    
    logger.info(f"Found {len(results)} documents with filter: {filter_expr}")
    for idx, doc in enumerate(results):
        logger.info(f"Document {idx+1}: ID = {doc.get('id')}, Title = {doc.get('title')}")
    
    return len(results) == 1

async def test_update_content():
    """
    Tests that content gets properly updated when it already exists.
    """
    logger.info("Starting update content test")
    
    # Get the vector store
    vector_store = await get_vector_store()
    
    # Create a test content item with URL for consistent ID generation
    url = "https://example.com/test-update-content"
    content_item = {
        "url": url,
        "title": "Test Update Content - Original",
        "description": "This is a test to verify that content gets properly updated.",
        "subject": "Programming",
        "content_type": "article",
        "page_content": "This is the original content.",
        "difficulty_level": "intermediate",
        "grade_level": [9, 10, 11],
        "topics": ["Testing", "Vector Search", "Updates"],
        "keywords": ["test", "update", "vector"],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # First add the content
    logger.info("Adding initial content")
    success1 = await vector_store.add_content(content_item)
    logger.info(f"Initial add result: {success1}")
    
    # Wait a bit to ensure the first add completes
    await asyncio.sleep(2)
    
    # Search for the content to get its ID
    filter_expr = f"url eq '{url}'"
    results = await vector_store.filter_search(filter_expr)
    
    if not results:
        logger.error("FAILURE: Could not find the content we just added.")
        return False
    
    doc_id = results[0].get('id')
    logger.info(f"Found document with ID: {doc_id}")
    
    # Create updated content
    updated_content = content_item.copy()
    updated_content["title"] = "Test Update Content - Updated"
    updated_content["page_content"] = "This is the updated content."
    updated_content["updated_at"] = datetime.utcnow().isoformat()
    
    # Update the content using update_content method
    logger.info("Updating content")
    success2 = await vector_store.update_content(doc_id, updated_content)
    logger.info(f"Update result: {success2}")
    
    # Wait a bit to ensure the update completes
    await asyncio.sleep(2)
    
    # Check if the content was updated
    updated_results = await vector_store.filter_search(filter_expr)
    
    if not updated_results:
        logger.error("FAILURE: Could not find the content after update.")
        return False
    
    if len(updated_results) > 1:
        logger.error(f"FAILURE: Found {len(updated_results)} documents with the test URL after update.")
        return False
    
    updated_doc = updated_results[0]
    
    if updated_doc.get("title") == "Test Update Content - Updated" and "updated content" in updated_doc.get("page_content", ""):
        logger.info("SUCCESS: Content was properly updated!")
    else:
        logger.error(f"FAILURE: Content was not updated correctly. Title: {updated_doc.get('title')}, Content: {updated_doc.get('content')}")
        return False
    
    return True

async def main():
    """Main function to run tests."""
    logger.info("Starting tests")
    
    # Run duplicate prevention test
    duplicate_result = await test_duplicate_prevention()
    
    # Run update content test
    update_result = await test_update_content()
    
    # Print final results
    logger.info("\n===== Test Results =====")
    logger.info(f"Duplicate Prevention Test: {'SUCCESS' if duplicate_result else 'FAILURE'}")
    logger.info(f"Update Content Test: {'SUCCESS' if update_result else 'FAILURE'}")
    
    return duplicate_result and update_result

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)