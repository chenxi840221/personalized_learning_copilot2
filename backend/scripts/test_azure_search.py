#!/usr/bin/env python3
# backend/scripts/test_azure_search.py

"""
Simple test script for Azure Search connection.
This script:
1. Tests the connection to Azure Search
2. Creates a minimal index with vector search support using direct REST API calls
3. Adds a test document with embedding
"""

import asyncio
import logging
import os
import sys
import uuid
import json
import aiohttp
from typing import List, Dict, Any
import numpy as np

# Add the project root to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Constants
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
TEST_INDEX_NAME = "test-vector-index"
API_VERSION = "2024-03-01-Preview"  # Updated to use the preview API that supports vector search

async def test_connection():
    """Test the connection to Azure Search using direct REST API."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
    
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            # List existing indexes
            list_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            async with session.get(list_url, headers=headers) as response:
                if response.status == 200:
                    indexes = await response.json()
                    existing_indexes = indexes.get("value", [])
                    logger.info(f"Found {len(existing_indexes)} indexes:")
                    for index in existing_indexes:
                        logger.info(f"- {index.get('name')}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Error checking indexes: {response.status} - {error_text}")
                    return False
    
    except Exception as e:
        logger.error(f"Error connecting to Azure Search: {e}")
        return False

async def create_test_index():
    """Create a test index with vector search support."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
    
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            # Check if index exists and delete if needed
            list_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            async with session.get(list_url, headers=headers) as response:
                if response.status == 200:
                    indexes = await response.json()
                    existing_indexes = [idx["name"] for idx in indexes.get("value", [])]
                    
                    if TEST_INDEX_NAME in existing_indexes:
                        logger.info(f"Index '{TEST_INDEX_NAME}' exists – deleting")
                        delete_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{TEST_INDEX_NAME}?api-version={API_VERSION}"
                        async with session.delete(delete_url, headers=headers) as delete_response:
                            if delete_response.status == 204:
                                logger.info(f"Successfully deleted index '{TEST_INDEX_NAME}'")
                            else:
                                error_text = await delete_response.text()
                                logger.error(f"Failed to delete index: {delete_response.status} - {error_text}")
                                return False
            
            # Define the index with vector search capability
            index_def = {
                "name": TEST_INDEX_NAME,
                "fields": [
                    {
                        "name": "id",
                        "type": "Edm.String",
                        "key": True,
                        "filterable": True
                    },
                    {
                        "name": "title",
                        "type": "Edm.String",
                        "filterable": True,
                        "searchable": True
                    },
                    {
                        "name": "content",
                        "type": "Edm.String",
                        "searchable": True
                    },
                    {
                        "name": "embedding",
                        "type": "Collection(Edm.Single)",
                        "searchable": True,
                        "dimensions": 4,
                        "vectorSearchProfile": "default-profile"
                    }
                ],
                "vectorSearch": {
                    "profiles": [
                        {
                            "name": "default-profile",
                            "algorithm": "my-hnsw"
                        }
                    ],
                    "algorithms": [
                        {
                            "name": "my-hnsw",
                            "kind": "hnsw"
                        }
                    ]
                }
            }




              
            
            # Create the index
            create_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            async with session.post(create_url, headers=headers, json=index_def) as response:
                if response.status == 201:
                    logger.info(f"Created test index: {TEST_INDEX_NAME}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create index: {response.status} - {error_text}")
                    return False
        
    except Exception as e:
        logger.error(f"Error creating test index: {e}")
        return False

async def add_test_document():
    """Add a test document with embedding to the test index."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
    
    try:
        # Wait a moment for the index to be ready
        await asyncio.sleep(5)
        
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            test_doc = {
                "@search.action": "upload",
                "id": str(uuid.uuid4()),
                "title": "Test Document",
                "content": "This is a test document for vector search.",
                "embedding": [float(x) for x in [0.1, 0.2, 0.3, 0.4]]
            }

            
            # Upload the document
            docs_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{TEST_INDEX_NAME}/docs/index?api-version={API_VERSION}"
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }

            payload = {
                "value": [test_doc]
            }

            async with session.post(docs_url, headers=headers, json=payload) as response:
                response_text = await response.text()
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError:
                    result = {}

                if response.status == 200 and "value" in result:
                    doc_result = result["value"][0]
                    if doc_result.get("status", False):

                        logger.info(f"✅ Successfully added test document with ID: {test_doc['id']}")
                        return True
                    else:
                        logger.error(f"❌ Failed to add test document – full result: {json.dumps(doc_result, indent=2)}")
                        return False

                else:
                    logger.error(f"❌ Upload failed - Status {response.status} - Body: {response_text}")
                    return False

        
    except Exception as e:
        logger.error(f"Error adding test document: {e}")
        return False

async def run_tests():
    """Run all tests."""
    # Test connection
    connection_ok = await test_connection()
    if not connection_ok:
        logger.error("Connection test failed. Exiting.")
        return False
    
    # Create test index
    index_ok = await create_test_index()
    if not index_ok:
        logger.error("Index creation failed. Exiting.")
        return False
    
    # Add test document
    doc_ok = await add_test_document()
    if not doc_ok:
        logger.error("Document addition failed. Exiting.")
        return False
    
    logger.info("All tests passed successfully!")
    return True

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    if success:
        print("✅ Azure Search test completed successfully")
        sys.exit(0)
    else:
        print("❌ Azure Search test failed")
        sys.exit(1)