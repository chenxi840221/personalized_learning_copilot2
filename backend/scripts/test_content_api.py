"""
Simple script to test the content endpoints directly.
To run: python scripts/test_content_api.py
"""
import asyncio
import logging
from fastapi import Query
from typing import Optional

from api.endpoints import (
    get_content_endpoint,
    get_content_by_id_endpoint,
    get_recommendations_endpoint,
    search_content_endpoint
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_get_content():
    """Test get_content_endpoint with various subjects."""
    # Test without filters
    logger.info("Testing get_content_endpoint with no filters")
    contents = await get_content_endpoint()
    logger.info(f"Found {len(contents)} contents without filters")
    
    if contents:
        logger.info("First few content items:")
        for item in contents[:3]:
            logger.info(f"  - {item.get('id', 'N/A')}: {item.get('title', 'N/A')} ({item.get('subject', 'N/A')})")
        
        # Save an ID for later testing
        first_id = contents[0].get("id")
        logger.info(f"Saving ID for testing: {first_id}")
        return first_id
    else:
        logger.warning("No content found without filters")
        return None

async def test_get_content_by_id(content_id: str):
    """Test get_content_by_id_endpoint."""
    if not content_id:
        logger.error("No content ID provided for testing")
        return
    
    logger.info(f"Testing get_content_by_id_endpoint with ID: {content_id}")
    content = await get_content_by_id_endpoint(content_id=content_id)
    
    if content:
        logger.info("Content details:")
        logger.info(f"  - Title: {content.get('title', 'N/A')}")
        logger.info(f"  - Subject: {content.get('subject', 'N/A')}")
        logger.info(f"  - Content type: {content.get('content_type', 'N/A')}")
    else:
        logger.warning(f"No content found with ID: {content_id}")

async def test_recommendations():
    """Test get_recommendations_endpoint."""
    logger.info("Testing get_recommendations_endpoint with no filters")
    recommendations = await get_recommendations_endpoint()
    logger.info(f"Found {len(recommendations)} recommendations without filters")
    
    if recommendations:
        logger.info("First few recommendations:")
        for item in recommendations[:3]:
            logger.info(f"  - {item.get('id', 'N/A')}: {item.get('title', 'N/A')} ({item.get('subject', 'N/A')})")
    else:
        logger.warning("No recommendations found without filters")

async def test_search():
    """Test search_content_endpoint."""
    search_term = "learning"
    logger.info(f"Testing search_content_endpoint with query: {search_term}")
    search_results = await search_content_endpoint(query=search_term)
    logger.info(f"Found {len(search_results)} results for search term: {search_term}")
    
    if search_results:
        logger.info("First few search results:")
        for item in search_results[:3]:
            logger.info(f"  - {item.get('id', 'N/A')}: {item.get('title', 'N/A')} ({item.get('subject', 'N/A')})")
    else:
        logger.warning(f"No search results found for: {search_term}")

async def main():
    """Run all tests."""
    try:
        # First test get_content to get an ID
        content_id = await test_get_content()
        
        # Then test the other endpoints
        if content_id:
            await test_get_content_by_id(content_id)
        
        await test_recommendations()
        await test_search()
        
    except Exception as e:
        logger.error(f"Error during tests: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting content API tests...")
    asyncio.run(main())
    logger.info("Tests completed.")