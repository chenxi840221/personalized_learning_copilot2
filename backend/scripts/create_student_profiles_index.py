#!/usr/bin/env python3
"""Create or update Azure AI Search student-profiles index.

This script creates or updates the student-profiles index for
the Personalized Learning Co-pilot, replacing the user-profiles index.
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
OLD_USERS_INDEX_NAME = os.getenv("AZURE_SEARCH_USERS_INDEX", "user-profiles")
STUDENT_PROFILES_INDEX_NAME = "student-profiles"  # The new index name
API_VERSION = "2024-03-01-Preview"  # Using latest preview API

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

async def _migrate_data(source_index: str, target_index: str) -> bool:
    """Migrate data from source index to target index."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
    
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            # Check if source index exists
            list_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            async with session.get(list_url, headers=headers) as response:
                if response.status == 200:
                    indexes = await response.json()
                    existing_indexes = [idx["name"] for idx in indexes.get("value", [])]
                    
                    if source_index not in existing_indexes:
                        logger.warning(f"Source index '{source_index}' does not exist.")
                        return False
                    
                    if target_index not in existing_indexes:
                        logger.warning(f"Target index '{target_index}' does not exist.")
                        return False
            
            # Query all documents from source index
            search_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{source_index}/docs/search?api-version={API_VERSION}"
            search_payload = {
                "search": "*",
                "top": 1000  # Adjust as needed
            }
            
            async with session.post(search_url, headers=headers, json=search_payload) as response:
                if response.status == 200:
                    result = await response.json()
                    documents = result.get("value", [])
                    
                    if not documents:
                        logger.info(f"No documents found in source index '{source_index}'")
                        return True
                    
                    logger.info(f"Found {len(documents)} documents in source index")
                    
                    # Prepare documents for target index - map fields as needed
                    target_documents = []
                    for doc in documents:
                        # Map or transform fields as needed
                        # For example, rename fields or add new fields
                        # Adapt this mapping based on your source and target schemas
                        target_doc = {
                            "id": doc.get("id"),
                            "full_name": doc.get("full_name"),
                            "email": doc.get("email"),
                            "grade_level": doc.get("grade_level"),
                            "learning_style": doc.get("learning_style"),
                            "interests": doc.get("subjects_of_interest"),
                            "created_at": doc.get("created_at"),
                            "updated_at": doc.get("updated_at"),
                            "embedding": doc.get("embedding")
                        }
                        target_documents.append(target_doc)
                    
                    # Index documents in target index in batches
                    batch_size = 50
                    for i in range(0, len(target_documents), batch_size):
                        batch = target_documents[i:i+batch_size]
                        
                        index_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{target_index}/docs/index?api-version={API_VERSION}"
                        index_payload = {
                            "value": batch
                        }
                        
                        async with session.post(index_url, headers=headers, json=index_payload) as index_response:
                            if index_response.status == 200:
                                logger.info(f"Indexed batch {i//batch_size + 1}/{(len(target_documents) + batch_size - 1)//batch_size}")
                            else:
                                error_text = await index_response.text()
                                logger.error(f"Failed to index batch: {index_response.status} - {error_text}")
                                return False
                    
                    logger.info(f"✅ Successfully migrated {len(target_documents)} documents from '{source_index}' to '{target_index}'")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to query source index: {response.status} - {error_text}")
                    return False
    
    except Exception as e:
        logger.error(f"Error migrating data: {e}")
        return False

###############################################################################
# Field definitions                                                           #
###############################################################################

# Define fields for student-profiles index
STUDENT_PROFILE_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "full_name", "type": "Edm.String", "searchable": True, "filterable": True},
    {"name": "email", "type": "Edm.String", "filterable": True},
    {"name": "gender", "type": "Edm.String", "filterable": True},
    {"name": "grade_level", "type": "Edm.Int32", "filterable": True, "facetable": True},
    {"name": "learning_style", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "strengths", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    {"name": "interests", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    {"name": "areas_for_improvement", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    {"name": "school_name", "type": "Edm.String", "filterable": True},
    {"name": "teacher_name", "type": "Edm.String", "filterable": True},
    {"name": "report_ids", "type": "Collection(Edm.String)", "filterable": True},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "last_report_date", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    # Vector field for embeddings
    {"name": "embedding", "type": "Collection(Edm.Single)", "searchable": True, "dimensions": 1536, "vectorSearchProfile": "default-profile"}
]

###############################################################################
# Main                                                                        #
###############################################################################

async def create_student_profiles_index() -> bool:
    """Create student-profiles index and migrate data from user-profiles."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False

    try:
        # Create the student-profiles index
        logger.info(f"Creating student-profiles index: {STUDENT_PROFILES_INDEX_NAME}")
        success = await _create_index_with_rest(STUDENT_PROFILES_INDEX_NAME, STUDENT_PROFILE_FIELDS)
        
        if not success:
            logger.error("Failed to create student-profiles index")
            return False
        
        # Check if the old user-profiles index exists
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            list_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            async with session.get(list_url, headers=headers) as response:
                if response.status == 200:
                    indexes = await response.json()
                    existing_indexes = [idx["name"] for idx in indexes.get("value", [])]
                    
                    if OLD_USERS_INDEX_NAME in existing_indexes:
                        # Migrate data from old user-profiles index
                        logger.info(f"Migrating data from '{OLD_USERS_INDEX_NAME}' to '{STUDENT_PROFILES_INDEX_NAME}'")
                        migration_success = await _migrate_data(OLD_USERS_INDEX_NAME, STUDENT_PROFILES_INDEX_NAME)
                        
                        if not migration_success:
                            logger.warning(f"Data migration from '{OLD_USERS_INDEX_NAME}' failed")
                    else:
                        logger.info(f"Old index '{OLD_USERS_INDEX_NAME}' does not exist, skipping migration.")
        
        logger.info(f"✅ Student-profiles index '{STUDENT_PROFILES_INDEX_NAME}' created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating student-profiles index: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(create_student_profiles_index())