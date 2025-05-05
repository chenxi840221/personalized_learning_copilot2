#!/usr/bin/env python
# backend/scripts/test_vector_store.py
import logging
import asyncio
import sys
import os
import json
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fix import paths for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)  # Add backend to path
sys.path.insert(0, project_root)  # Add project root to path

# Import the vector store
from utils.vector_store import get_vector_store

async def check_index_schema():
    """Check the schema of the Azure Search index."""
    from config.settings import Settings
    import aiohttp
    import json
    
    settings = Settings()
    
    # Define API version
    api_version = "2023-07-01-Preview"
    
    # Define headers
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_SEARCH_KEY
    }
    
    # Use aiohttp for the HTTP request
    async with aiohttp.ClientSession() as session:
        url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{settings.AZURE_SEARCH_INDEX_NAME}?api-version={api_version}"
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                logger.info(f"Index exists")
                schema = await response.json()
                fields = schema.get('fields', [])
                logger.info("Index fields:")
                for field in fields:
                    logger.info(f"  {field.get('name')}: {field.get('type')}")
                
                # Check for vector search configuration
                vector_search = schema.get('vectorSearch', {})
                logger.info(f"Vector search configuration: {json.dumps(vector_search, indent=2)}")
                
                # Look for embedding field
                embedding_field = next((f for f in fields if f.get('name') == 'embedding'), None)
                if embedding_field:
                    logger.info(f"Embedding field: {json.dumps(embedding_field, indent=2)}")
                else:
                    logger.error("No embedding field found")
                    
                return schema
            elif response.status == 404:
                logger.warning(f"Index does not exist")
                return None
            else:
                logger.error(f"Error checking index: {response.status}")
                text = await response.text()
                logger.error(f"Response: {text}")
                return None

async def direct_azure_search_test():
    """Test directly with Azure Search API."""
    from config.settings import Settings
    import aiohttp
    import json
    import random
    import numpy as np
    
    settings = Settings()
    
    # Define API version
    api_version = "2023-11-01"
    
    # Define headers
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_SEARCH_KEY
    }
    
    # Create test embedding - 1536 dimensions
    embedding = [random.uniform(-1, 1) for _ in range(1536)]
    
    # Create test document matching the exact schema
    document = {
        "@search.action": "upload",
        "id": f"test-{str(uuid.uuid4())}",
        "title": "Test Document",
        "description": "Test document created for API verification",
        "content_type": "test",
        "subject": "testing",
        "page_content": "This is a test document for the vector store with Azure Search integration.",
        "embedding": embedding
    }
    
    # Create payload
    payload = {
        "value": [document]
    }
    
    # Use aiohttp for the HTTP request
    async with aiohttp.ClientSession() as session:
        url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{settings.AZURE_SEARCH_INDEX_NAME}/docs/index?api-version={api_version}"
        logger.info(f"Sending request to URL: {url}")
        
        # First try just with minimal fields
        minimal_doc = {
            "@search.action": "upload",
            "id": f"test-minimal-{str(uuid.uuid4())}",
            "title": "Minimal Test",
            "page_content": "Minimal test document",
            "embedding": embedding
        }
        
        minimal_payload = {
            "value": [minimal_doc]
        }
        
        logger.info("Trying with minimal document...")
        try:
            async with session.post(url, headers=headers, json=minimal_payload) as response:
                status = response.status
                response_text = await response.text()
                logger.info(f"Response status: {status}")
                logger.info(f"Response: {response_text}")
                
                if status in [200, 201, 202, 204]:
                    logger.info("Minimal document added successfully!")
                    return True
                else:
                    logger.warning(f"Failed to add minimal document: {status} - {response_text}")
        except Exception as e:
            logger.error(f"Error adding minimal document: {e}")
            
        return False

async def test_vector_store():
    """Test the vector store with a sample document."""
    logger.info("Testing vector store...")
    
    # Check the index schema first
    schema = await check_index_schema()
    
    # Try direct Azure Search test
    logger.info("Trying direct Azure Search test...")
    direct_success = await direct_azure_search_test()
    
    if not direct_success:
        logger.error("Direct Azure Search test failed, skipping vector store test")
        return
    
    # Get vector store
    vector_store = await get_vector_store()
    
    # Create a test document - use page_content instead of content to match the schema
    test_doc = {
        "id": str(uuid.uuid4()),
        "title": "Test Document",
        "content_type": "Test",
        "page_content": "This is a test document for the vector store with Azure Search integration.",
        "description": "Test document for verification of Azure Search integration",
        "subject": "Testing",
        "difficulty_level": "Beginner",
        "keywords": ["test", "azure", "search", "vector"],
        "topics": ["Azure Search", "Vector Store", "Testing"]
    }
    
    logger.info(f"Adding test document with ID: {test_doc['id']}")
    
    # Add the document to the vector store
    success = await vector_store.add_content(test_doc)
    
    if success:
        logger.info("Test document added successfully!")
    else:
        logger.error("Failed to add test document")
        return
    
    # Search for the document using direct API approach
    logger.info("Searching for the document using direct API...")
    from config.settings import Settings
    import aiohttp
    import json
    import random
    
    settings = Settings()
    
    # Create test embedding - 1536 dimensions
    embedding = [random.uniform(-1, 1) for _ in range(1536)]
    
    # Define API version
    api_version = "2023-11-01"
    
    # Define headers
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_SEARCH_KEY
    }
    
    # Use aiohttp for the HTTP request
    async with aiohttp.ClientSession() as session:
        # Try standard text search
        search_payload = {
            "search": "test document",
            "top": 10
        }
        
        url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{settings.AZURE_SEARCH_INDEX_NAME}/docs/search?api-version={api_version}"
        logger.info(f"Sending text search request to URL: {url}")
        
        try:
            async with session.post(url, headers=headers, json=search_payload) as response:
                status = response.status
                response_text = await response.text()
                logger.info(f"Response status: {status}")
                
                if status == 200:
                    result = json.loads(response_text)
                    if "value" in result and len(result["value"]) > 0:
                        logger.info(f"Found {len(result['value'])} documents")
                        for doc in result["value"]:
                            logger.info(f"Document ID: {doc.get('id')}, Title: {doc.get('title')}")
                    else:
                        logger.warning("No documents found in response")
                else:
                    logger.warning(f"Search failed: {response_text}")
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
    
    # Now try with the LangChain vector_store
    logger.info("Trying vector_store.vector_search...")
    search_results = await vector_store.vector_search("test document")
    
    if not search_results:
        logger.error("No results found")
        return
        
    logger.info(f"Found {len(search_results)} results")
    
    # Get the document by ID
    logger.info(f"Getting document by ID: {test_doc['id']}")
    retrieved_doc = await vector_store.get_content(test_doc['id'])
    
    if retrieved_doc:
        logger.info("Successfully retrieved document by ID")
        logger.info(f"Document fields: {list(retrieved_doc.keys())}")
        if "content" in retrieved_doc:
            logger.info("Document has 'content' field - CORRECT")
        elif "page_content" in retrieved_doc:
            logger.info("Document has 'page_content' field - CORRECT")
        else:
            logger.error("Document does not have 'content' or 'page_content' field")
    else:
        logger.error("Failed to retrieve document by ID")

if __name__ == "__main__":
    # Run the test function
    asyncio.run(test_vector_store())