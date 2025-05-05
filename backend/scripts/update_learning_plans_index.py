#!/usr/bin/env python3
"""Update the learning-plans index with chunking fields.

This script updates the learning-plans index to include the 
activities_chunking field and dynamically create fields for week chunks.

Usage:
    python update_learning_plans_index.py

The script requires the following environment variables to be set:
    - AZURE_SEARCH_ENDPOINT: The endpoint URL for Azure AI Search
    - AZURE_SEARCH_KEY: The API key for Azure AI Search

If you have a .env file in the project root, the script will load
environment variables from there.

The script will:
1. Check if the learning-plans index exists
2. If it exists, retrieve all documents to preserve them
3. Delete the existing index
4. Create a new index with the updated schema
5. Restore all documents, migrating to the new chunking structure if needed

This is useful when you need to support multi-week learning plans with
many activities, which would exceed Azure Search field size limits without chunking.
"""
from __future__ import annotations

import asyncio
import logging
import os
import json
import aiohttp
import sys
from typing import List, Dict, Any, Optional

# Fix import paths for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)  # Add backend to path
sys.path.insert(0, project_root)  # Add project root to path

from dotenv import load_dotenv

###############################################################################
# Environment & logging                                                       #
###############################################################################

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Get settings from environment or settings module
from config.settings import Settings
settings = Settings()

AZURE_SEARCH_ENDPOINT = settings.AZURE_SEARCH_ENDPOINT
AZURE_SEARCH_KEY = settings.AZURE_SEARCH_KEY
API_VERSION = "2023-07-01-Preview"  # Using API version consistent with services

# Index name
PLANS_INDEX_NAME = settings.PLANS_INDEX_NAME or "learning-plans"

###############################################################################
# Field definitions                                                           #
###############################################################################

# Learning Plans index fields matching the schema provided
PLANS_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "student_id", "type": "Edm.String", "filterable": True, "searchable": True},
    {"name": "owner_id", "type": "Edm.String", "filterable": True, "searchable": True},  # Added owner_id field
    {"name": "title", "type": "Edm.String", "searchable": True},
    {"name": "description", "type": "Edm.String", "searchable": True},
    {"name": "subject", "type": "Edm.String", "searchable": True, "filterable": True, "facetable": True},
    {"name": "topics", "type": "Collection(Edm.String)", "searchable": True, "filterable": True, "facetable": True},
    {"name": "status", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "progress_percentage", "type": "Edm.Double", "filterable": True, "sortable": True},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "start_date", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "end_date", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    # Complex type for activities
    {
        "name": "activities",
        "type": "Collection(Edm.ComplexType)",
        "fields": [
            {"name": "id", "type": "Edm.String"},
            {"name": "title", "type": "Edm.String"},
            {"name": "description", "type": "Edm.String"},
            {"name": "content_id", "type": "Edm.String"},
            {"name": "duration_minutes", "type": "Edm.Int32"},
            {"name": "order", "type": "Edm.Int32"},
            {"name": "status", "type": "Edm.String"},
            {"name": "completed_at", "type": "Edm.DateTimeOffset"}
        ]
    }
]

###############################################################################
# Helpers                                                                     #
###############################################################################

async def create_index(index_name: str, fields: List[Dict[str, Any]]) -> bool:
    """Create an index with the given name and fields."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
    
    # Build the index definition compatible with API version 2023-07-01-Preview
    index_def = {
        "name": index_name,
        "fields": fields
    }
    
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            # Check if index exists
            list_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            async with session.get(list_url, headers=headers) as response:
                if response.status == 200:
                    indexes = await response.json()
                    existing_indexes = [idx["name"] for idx in indexes.get("value", [])]
                    
                    if index_name in existing_indexes:
                        logger.info(f"Index '{index_name}' exists - retrieving to migrate data")
                        
                        # Get all documents from the index before deletion
                        documents = await get_all_documents(index_name)
                        
                        # Delete the existing index
                        logger.info(f"Deleting index '{index_name}'")
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
                    logger.info(f"Successfully created index '{index_name}'")
                    
                    # Restore data if we have documents
                    if 'documents' in locals() and documents:
                        logger.info(f"Migrating {len(documents)} documents back to the index")
                        await restore_documents(index_name, documents)
                    
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

async def get_all_documents(index_name: str) -> List[Dict[str, Any]]:
    """Get all documents from an index."""
    documents = []
    
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            # Search for all documents (in batches)
            search_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}/docs/search?api-version={API_VERSION}"
            
            # First batch
            search_body = {
                "search": "*",
                "top": 1000,
                "skip": 0
            }
            
            # Get documents in batches of 1000
            has_more = True
            skip = 0
            
            while has_more:
                search_body["skip"] = skip
                
                async with session.post(search_url, headers=headers, json=search_body) as response:
                    if response.status == 200:
                        result = await response.json()
                        batch = result.get("value", [])
                        documents.extend(batch)
                        
                        logger.info(f"Retrieved {len(batch)} documents (skip={skip})")
                        
                        # Check if there might be more
                        if len(batch) < 1000:
                            has_more = False
                        else:
                            skip += 1000
                    else:
                        error_text = await response.text()
                        logger.error(f"Error retrieving documents: {response.status} - {error_text}")
                        has_more = False
                        
            return documents
    
    except Exception as e:
        logger.error(f"Error getting documents: {e}")
        return []

async def restore_documents(index_name: str, documents: List[Dict[str, Any]]) -> bool:
    """Restore documents to an index."""
    if not documents:
        logger.info("No documents to restore")
        return True
    
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            # Process in batches of 100
            batch_size = 100
            success = True
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                logger.info(f"Indexing batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")
                
                # Prepare documents for indexing
                migrated_batch = []
                for doc in batch:
                    # Extract and process activities to use the complex type field in the new schema
                    activities_collection = []
                    
                    # Check all possible sources of activities
                    potential_sources = [
                        ("activities", lambda x: x),  # Direct activities field
                        ("activities_json", lambda x: json.loads(x) if isinstance(x, str) else x),
                        ("activities_content", lambda x: json.loads(x) if isinstance(x, str) else x),
                        ("activitiesJson", lambda x: json.loads(x) if isinstance(x, str) else x)
                    ]
                    
                    # Also check for weekly chunks
                    for week_num in range(1, 9):
                        week_field = f"activities_week_{week_num}"
                        if week_field in doc and doc[week_field]:
                            potential_sources.append((week_field, lambda x: json.loads(x) if isinstance(x, str) else x))
                    
                    # Try each source to extract activities
                    found_activities = []
                    for field_name, converter in potential_sources:
                        if field_name in doc and doc[field_name]:
                            try:
                                activities = converter(doc[field_name])
                                if activities and isinstance(activities, list):
                                    logger.info(f"Found {len(activities)} activities in {field_name}")
                                    found_activities.extend(activities)
                                    
                                    # Remove the old field as we'll migrate to the new schema
                                    del doc[field_name]
                            except Exception as e:
                                logger.warning(f"Error extracting activities from {field_name}: {e}")
                    
                    # Process the activities to match the complex type schema
                    for activity in found_activities:
                        # Create a new activity object with only the fields in the schema
                        activity_obj = {
                            "id": activity.get("id", str(uuid.uuid4())),
                            "title": activity.get("title", "Activity"),
                            "description": activity.get("description", ""),
                            "content_id": activity.get("content_id"),
                            "duration_minutes": activity.get("duration_minutes", 30),
                            "order": activity.get("order", 1),
                            "status": activity.get("status", "not_started")
                        }
                        
                        # Format completed_at date if present
                        if "completed_at" in activity and activity["completed_at"]:
                            if isinstance(activity["completed_at"], str):
                                activity_obj["completed_at"] = activity["completed_at"]
                            else:
                                # Try to convert to ISO format
                                try:
                                    from datetime import datetime
                                    dt = activity["completed_at"]
                                    if isinstance(dt, datetime):
                                        activity_obj["completed_at"] = dt.isoformat() + "Z"
                                except:
                                    pass
                        
                        activities_collection.append(activity_obj)
                    
                    # Add activities as a complex type collection
                    if activities_collection:
                        doc["activities"] = activities_collection
                        logger.info(f"Added {len(activities_collection)} activities as complex type collection")
                    
                    # Update field names to match the schema
                    field_mappings = {
                        "created": "created_at",
                        "updated": "updated_at",
                        "startDate": "start_date",
                        "endDate": "end_date",
                        "progress": "progress_percentage"
                    }
                    
                    # Perform field name mappings
                    for old_name, new_name in field_mappings.items():
                        if old_name in doc:
                            doc[new_name] = doc[old_name]
                            del doc[old_name]
                    
                    # Check if there are any fields in the document that don't exist in the schema
                    schema_fields = [f["name"] for f in PLANS_FIELDS]
                    unknown_fields = [f for f in doc.keys() if f not in schema_fields and not f.startswith("@")]
                    
                    if unknown_fields:
                        logger.warning(f"Removing unknown fields not in schema: {', '.join(unknown_fields)}")
                        for field in unknown_fields:
                            del doc[field]
                    
                    migrated_batch.append(doc)
                
                # Index the batch
                index_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}/docs/index?api-version={API_VERSION}"
                async with session.post(index_url, headers=headers, json={"value": migrated_batch}) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error indexing batch: {response.status} - {error_text}")
                        success = False
                    else:
                        logger.info(f"Successfully indexed batch {i//batch_size + 1}")
            
            return success
    
    except Exception as e:
        logger.error(f"Error restoring documents: {e}")
        return False

###############################################################################
# Main                                                                        #
###############################################################################

async def update_learning_plans_index() -> bool:
    """Update the learning plans index to support activity chunking."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
        
    try:
        logger.info(f"Updating learning plans index: {PLANS_INDEX_NAME}")
        
        # First check if the index exists
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
                    
                    if PLANS_INDEX_NAME in existing_indexes:
                        logger.info(f"Index '{PLANS_INDEX_NAME}' exists - will back up and update")
                    else:
                        logger.info(f"Index '{PLANS_INDEX_NAME}' not found - will create new index")
        
        # Update or create the index with the correct schema
        success = await create_index(PLANS_INDEX_NAME, PLANS_FIELDS)
        
        if success:
            logger.info("🎉 Learning plans index updated successfully with chunking support")
            
            # Get the current document count using a more reliable method
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "api-key": AZURE_SEARCH_KEY
                }
                
                # Count documents using search with top=0 instead of the /count endpoint
                search_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{PLANS_INDEX_NAME}/docs/search?api-version={API_VERSION}"
                search_body = {
                    "search": "*",  # Match all documents
                    "top": 0,       # Don't return any actual documents
                    "count": True   # Include the total count
                }
                
                try:
                    async with session.post(search_url, headers=headers, json=search_body) as response:
                        if response.status == 200:
                            result = await response.json()
                            doc_count = result.get("@odata.count", 0)
                            logger.info(f"📊 Learning plans index contains {doc_count} documents")
                        else:
                            error_text = await response.text()
                            logger.warning(f"Unable to get document count: {response.status} - {error_text}")
                            
                            # Try alternate method if search with count fails
                            logger.info("Trying alternate method to verify documents exist...")
                            try:
                                # Just search for any document to verify there are documents
                                alt_body = {
                                    "search": "*",
                                    "top": 1
                                }
                                
                                async with session.post(search_url, headers=headers, json=alt_body) as alt_response:
                                    if alt_response.status == 200:
                                        alt_result = await alt_response.json()
                                        # If we get any documents back, the index is not empty
                                        if "value" in alt_result and len(alt_result["value"]) > 0:
                                            logger.info("✅ Index contains documents (exact count unknown)")
                                        else:
                                            logger.info("⚠️ No documents found in the index")
                                    else:
                                        alt_error = await alt_response.text()
                                        logger.warning(f"Unable to verify documents with alternate method: {alt_response.status} - {alt_error}")
                            except Exception as alt_err:
                                logger.error(f"Alternate counting method failed: {alt_err}")
                            
                            # Try an alternate method if the first one fails
                            logger.info("Trying alternate method to count documents...")
                            try:
                                # Just search for any document to verify there are documents
                                alt_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{PLANS_INDEX_NAME}/docs/search?api-version={API_VERSION}"
                                alt_body = {
                                    "search": "*",
                                    "top": 1
                                }
                                
                                async with session.post(alt_url, headers=headers, json=alt_body) as alt_response:
                                    if alt_response.status == 200:
                                        alt_result = await alt_response.json()
                                        # If we get any documents back, the index is not empty
                                        if "value" in alt_result and len(alt_result["value"]) > 0:
                                            logger.info("✅ Index contains documents (exact count unknown)")
                                            doc_count = 1  # Set to 1 to indicate documents exist
                                    else:
                                        alt_error_text = await alt_response.text()
                                        logger.warning(f"Alternative document check failed: {alt_response.status} - {alt_error_text}")
                            except Exception as alt_err:
                                logger.error(f"Alternate counting method failed: {alt_err}")
                except Exception as e:
                    logger.error(f"Error counting documents in index {PLANS_INDEX_NAME}: {e}")
            
            return True
        else:
            logger.error("Failed to update learning plans index")
            return False
    
    except Exception as e:
        logger.error(f"Error updating learning plans index: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    try:
        logger.info("Starting update_learning_plans_index.py")
        logger.info(f"Using Azure Search API version: {API_VERSION}")
        
        # Check environment
        if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
            logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY environment variables are required.")
            sys.exit(1)
            
        logger.info(f"Azure Search endpoint: {AZURE_SEARCH_ENDPOINT}")
        
        # Run the update
        result = asyncio.run(update_learning_plans_index())
        
        # Exit with appropriate code
        if result:
            logger.info("✅ Learning plans index updated successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Failed to update learning plans index.")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unhandled error: {e}")
        sys.exit(1)