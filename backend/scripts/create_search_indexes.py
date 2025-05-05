#!/usr/bin/env python3
"""Create Azure AI Search indexes for the Personalized Learning Co‑pilot.

This script creates the necessary search indexes for LangChain integration
with Azure AI Search. It has been updated to work with the 2024-03-01-Preview API.
"""
from __future__ import annotations

import asyncio
import logging
import os
import json
import aiohttp
from typing import List, Dict, Any, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.aio import SearchIndexClient
from dotenv import load_dotenv

###############################################################################
# Environment & logging                                                       #
###############################################################################

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
CONTENT_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "educational-content")
USERS_INDEX_NAME = os.getenv("AZURE_SEARCH_USERS_INDEX", "user-profiles")
PLANS_INDEX_NAME = os.getenv("AZURE_SEARCH_PLANS_INDEX", "learning-plans")
API_VERSION = "2024-03-01-Preview"  # Updated to latest preview API

###############################################################################
# Helpers                                                                     #
###############################################################################

async def _create_index_with_rest(index_name: str, fields: List, vector_config: bool = True):
    """Create an index using direct REST API call."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
    
    # Build the index definition
    index_def = {
        "name": index_name,
        "fields": fields
    }
    
    # Add vector search configuration if requested - SIMPLIFIED FORMAT for 2024-03-01-Preview
    if vector_config:
        index_def["vectorSearch"] = {
            "profiles": [
                {
                    "name": "default-profile",
                    "algorithm": "default-algorithm"
                }
            ],
            "algorithms": [
                {
                    "name": "default-algorithm",
                    "kind": "hnsw"
                }
            ]
        }
    
    # Check if index exists and delete if it does
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            # Check if index exists
            list_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            async with session.get(list_url, headers=headers) as response:
                if response.status == 200:
                    indexes = await response.json()
                    existing_indexes = [idx["name"] for idx in indexes.get("value", [])]
                    
                    if index_name in existing_indexes:
                        logger.info(f"Index '{index_name}' exists – deleting")
                        delete_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}?api-version={API_VERSION}"
                        async with session.delete(delete_url, headers=headers) as delete_response:
                            if delete_response.status == 204:
                                logger.info(f"Successfully deleted index '{index_name}'")
                            else:
                                error_text = await delete_response.text()
                                logger.error(f"Failed to delete index: {delete_response.status} - {error_text}")
                                return False
            
            # Create the index
            create_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            async with session.post(create_url, headers=headers, json=index_def) as response:
                if response.status == 201:
                    logger.info(f"✅ Created index: {index_name}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to create index: {response.status} - {error_text}")
                    # Log the full request for debugging
                    logger.info(f"Request payload: {json.dumps(index_def)}")
                    return False
    
    except Exception as e:
        logger.error(f"Error in REST API call: {e}")
        return False

###############################################################################
# Field definitions                                                           #
###############################################################################

CONTENT_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "title", "type": "Edm.String", "searchable": True, "filterable": True},
    {"name": "description", "type": "Edm.String", "searchable": True},
    {"name": "content_type", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "subject", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "topics", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    {"name": "url", "type": "Edm.String"},
    {"name": "source", "type": "Edm.String", "filterable": True},
    {"name": "difficulty_level", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "grade_level", "type": "Collection(Edm.Int32)", "filterable": True, "facetable": True},
    {"name": "duration_minutes", "type": "Edm.Int32", "filterable": True, "facetable": True},
    {"name": "keywords", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    # Flattened metadata
    {"name": "metadata_content_text", "type": "Edm.String", "searchable": True},
    {"name": "metadata_transcription", "type": "Edm.String", "searchable": True},
    {"name": "metadata_thumbnail_url", "type": "Edm.String"},
    # This is the main field that will be used for text content
    {"name": "page_content", "type": "Edm.String", "searchable": True},
    # Vector field for embeddings - UPDATED FIELD CONFIGURATION
    {"name": "embedding", "type": "Collection(Edm.Single)", "searchable": True, "dimensions": 1536, "vectorSearchProfile": "default-profile"}
]

USER_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "username", "type": "Edm.String", "filterable": True},
    {"name": "full_name", "type": "Edm.String", "searchable": True},
    {"name": "email", "type": "Edm.String", "filterable": True},
    {"name": "grade_level", "type": "Edm.Int32", "filterable": True, "facetable": True},
    {"name": "learning_style", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "subjects_of_interest", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    # Vector field for embeddings - UPDATED FIELD CONFIGURATION
    {"name": "embedding", "type": "Collection(Edm.Single)", "searchable": True, "dimensions": 1536, "vectorSearchProfile": "default-profile"}
]

PLAN_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "student_id", "type": "Edm.String", "filterable": True},
    {"name": "owner_id", "type": "Edm.String", "filterable": True},  # Added owner_id field
    {"name": "title", "type": "Edm.String", "searchable": True},
    {"name": "description", "type": "Edm.String", "searchable": True},
    {"name": "subject", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "topics", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    # Activities complex collection
    {"name": "status", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "progress_percentage", "type": "Edm.Double", "filterable": True, "sortable": True},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "start_date", "type": "Edm.DateTimeOffset", "filterable": True},
    {"name": "end_date", "type": "Edm.DateTimeOffset", "filterable": True},
    # LangChain can work with page_content field 
    {"name": "page_content", "type": "Edm.String", "searchable": True},
    # Vector field for embeddings - UPDATED FIELD CONFIGURATION
    {"name": "embedding", "type": "Collection(Edm.Single)", "searchable": True, "dimensions": 1536, "vectorSearchProfile": "default-profile"}
]

###############################################################################
# Main                                                                        #
###############################################################################

async def populate_sample_content(index_name: str) -> bool:
    """
    Populate the educational-content index with sample content from fallback content.
    This ensures that we always have some content to search.
    """
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
        
    try:
        # Import the fallback content
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        sys.path.insert(0, backend_dir)
        
        # Import directly from the add_fallback_content module's FALLBACK_CONTENT
        from scripts.add_fallback_content import FALLBACK_CONTENT
        
        # Import necessary types for adding content
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        
        # Prepare sample documents for indexing
        sample_docs = []
        for subject, content_list in FALLBACK_CONTENT.items():
            for content_item in content_list:
                # Create a document with all required fields for search index
                doc = {}
                doc["id"] = content_item["id"]
                doc["title"] = content_item["title"]
                doc["description"] = content_item["description"]
                doc["content_type"] = content_item["content_type"]
                doc["subject"] = subject
                doc["difficulty_level"] = content_item["difficulty_level"]
                doc["url"] = content_item["url"]
                doc["grade_level"] = content_item["grade_level"]
                doc["topics"] = content_item.get("topics", [subject])
                doc["duration_minutes"] = content_item.get("duration_minutes", 30)
                doc["keywords"] = content_item.get("keywords", [])
                doc["source"] = "Fallback Content"
                doc["page_content"] = content_item["description"]
                
                # Add to documents to index
                sample_docs.append(doc)
        
        # Create search client
        search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=index_name,
            credential=AzureKeyCredential(AZURE_SEARCH_KEY)
        )
        
        # Upload in batches to avoid hitting limits
        batch_size = 10
        upload_count = 0
        
        for i in range(0, len(sample_docs), batch_size):
            batch = sample_docs[i:i+batch_size]
            try:
                result = search_client.upload_documents(documents=batch)
                successful = sum(1 for r in result if r.succeeded)
                upload_count += successful
                logger.info(f"Uploaded batch {i//batch_size + 1}: {successful}/{len(batch)} succeeded")
            except Exception as e:
                logger.error(f"Error uploading batch {i//batch_size + 1}: {e}")
        
        logger.info(f"Successfully uploaded {upload_count}/{len(sample_docs)} fallback content items")
        return upload_count > 0
    except Exception as e:
        logger.error(f"Error populating sample content: {e}")
        return False

async def main() -> bool:
    """Create all search indexes."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False

    try:
        # Create the indexes using direct REST API
        success1 = await _create_index_with_rest(CONTENT_INDEX_NAME, CONTENT_FIELDS)
        success2 = await _create_index_with_rest(USERS_INDEX_NAME, USER_FIELDS)
        success3 = await _create_index_with_rest(PLANS_INDEX_NAME, PLAN_FIELDS)
        
        # Populate educational-content index with sample content if successful
        if success1:
            logger.info(f"Populating {CONTENT_INDEX_NAME} with sample content...")
            success_content = await populate_sample_content(CONTENT_INDEX_NAME)
            if success_content:
                logger.info("✅ Successfully added sample content to index")
            else:
                logger.warning("⚠️ Failed to add sample content, but index was created")
        
        if success1 and success2 and success3:
            logger.info("🎉 All indexes created successfully")
            return True
        else:
            logger.error("Failed to create all indexes")
            return False
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(main())