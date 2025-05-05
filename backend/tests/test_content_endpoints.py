"""
Test script for content endpoints.
To run: python -m tests.test_content_endpoints
"""
import sys
import os
import asyncio
import logging
from fastapi.testclient import TestClient

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from config.settings import Settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize test client
client = TestClient(app)

async def test_get_content():
    """Test the /content endpoint."""
    settings = Settings()
    content_index_name = settings.CONTENT_INDEX_NAME or "educational-content"
    
    logger.info(f"Using content index: {content_index_name}")
    
    # Test with no filters
    response = client.get("/content")
    logger.info(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        content_items = response.json()
        logger.info(f"Found {len(content_items)} content items without filters")
    else:
        logger.error(f"Error: {response.text}")
    
    # Test with Mathematics filter
    response = client.get("/content?subject=Mathematics")
    logger.info(f"Response status for Mathematics: {response.status_code}")
    
    if response.status_code == 200:
        content_items = response.json()
        logger.info(f"Found {len(content_items)} Mathematics content items")
        for item in content_items[:3]:  # Show first 3 items
            logger.info(f"  - {item.get('id', 'N/A')}: {item.get('title', 'N/A')} ({item.get('subject', 'N/A')})")
    else:
        logger.error(f"Error for Mathematics: {response.text}")
    
    # Test with History filter
    response = client.get("/content?subject=History")
    logger.info(f"Response status for History: {response.status_code}")
    
    if response.status_code == 200:
        content_items = response.json()
        logger.info(f"Found {len(content_items)} History content items")
        for item in content_items[:3]:  # Show first 3 items
            logger.info(f"  - {item.get('id', 'N/A')}: {item.get('title', 'N/A')} ({item.get('subject', 'N/A')})")
    else:
        logger.error(f"Error for History: {response.text}")

async def test_get_content_by_id():
    """Test the /content/{content_id} endpoint."""
    # First get some content IDs from the main endpoint
    response = client.get("/content")
    
    if response.status_code != 200 or not response.json():
        logger.error("Could not get content items to test content_by_id endpoint")
        return
    
    # Get the first content item's ID
    content_items = response.json()
    test_id = content_items[0].get("id", None)
    
    if not test_id:
        logger.error("Content item has no ID")
        return
    
    # Test the content_by_id endpoint
    logger.info(f"Testing content_by_id with ID: {test_id}")
    response = client.get(f"/content/{test_id}")
    
    if response.status_code == 200:
        content_item = response.json()
        logger.info(f"Successfully retrieved item:")
        logger.info(f"  - Title: {content_item.get('title', 'N/A')}")
        logger.info(f"  - Subject: {content_item.get('subject', 'N/A')}")
        logger.info(f"  - Content type: {content_item.get('content_type', 'N/A')}")
    else:
        logger.error(f"Error retrieving content by ID: {response.text}")
    
    # Test with an invalid ID
    invalid_id = "non-existent-id-12345"
    logger.info(f"Testing content_by_id with invalid ID: {invalid_id}")
    response = client.get(f"/content/{invalid_id}")
    
    logger.info(f"Response status for invalid ID: {response.status_code}")
    logger.info(f"Response text: {response.text}")

async def test_get_recommendations():
    """Test the /content/recommendations endpoint."""
    # Test with no subject filter
    response = client.get("/content/recommendations")
    logger.info(f"Recommendations response status: {response.status_code}")
    
    if response.status_code == 200:
        recommendations = response.json()
        logger.info(f"Found {len(recommendations)} recommendations without subject filter")
    else:
        logger.error(f"Error getting recommendations: {response.text}")
    
    # Test with Mathematics subject
    response = client.get("/content/recommendations?subject=Mathematics")
    logger.info(f"Mathematics recommendations response status: {response.status_code}")
    
    if response.status_code == 200:
        recommendations = response.json()
        logger.info(f"Found {len(recommendations)} Mathematics recommendations")
        for item in recommendations[:3]:  # Show first 3 items
            logger.info(f"  - {item.get('id', 'N/A')}: {item.get('title', 'N/A')} ({item.get('subject', 'N/A')})")
    else:
        logger.error(f"Error getting Mathematics recommendations: {response.text}")

async def test_search_content():
    """Test the /content/search endpoint."""
    # Test search with a general term
    search_term = "learning"
    response = client.get(f"/content/search?query={search_term}")
    logger.info(f"Search response status for '{search_term}': {response.status_code}")
    
    if response.status_code == 200:
        search_results = response.json()
        logger.info(f"Found {len(search_results)} results for search term '{search_term}'")
        for item in search_results[:3]:  # Show first 3 items
            logger.info(f"  - {item.get('id', 'N/A')}: {item.get('title', 'N/A')} ({item.get('subject', 'N/A')})")
    else:
        logger.error(f"Error searching for '{search_term}': {response.text}")
    
    # Test search with subject filter
    search_term = "algebra"
    subject = "Mathematics"
    response = client.get(f"/content/search?query={search_term}&subject={subject}")
    logger.info(f"Search response for '{search_term}' in {subject}: {response.status_code}")
    
    if response.status_code == 200:
        search_results = response.json()
        logger.info(f"Found {len(search_results)} results for '{search_term}' in {subject}")
        for item in search_results[:3]:  # Show first 3 items
            logger.info(f"  - {item.get('id', 'N/A')}: {item.get('title', 'N/A')} ({item.get('subject', 'N/A')})")
    else:
        logger.error(f"Error searching for '{search_term}' in {subject}: {response.text}")

async def run_tests():
    """Run all tests."""
    logger.info("Testing /content endpoint")
    await test_get_content()
    
    logger.info("\nTesting /content/{content_id} endpoint")
    await test_get_content_by_id()
    
    logger.info("\nTesting /content/recommendations endpoint")
    await test_get_recommendations()
    
    logger.info("\nTesting /content/search endpoint")
    await test_search_content()

if __name__ == "__main__":
    logger.info("Starting content endpoint tests...")
    asyncio.run(run_tests())
    logger.info("Tests completed.")