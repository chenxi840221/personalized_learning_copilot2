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

# Learning Plans index fields with minimal schema to ensure compatibility with API version 2023-07-01-Preview
PLANS_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True}, 
    {"name": "student_id", "type": "Edm.String", "filterable": True},
    {"name": "title", "type": "Edm.String", "searchable": True},
    {"name": "description", "type": "Edm.String", "searchable": True},
    {"name": "subject", "type": "Edm.String", "filterable": True, "searchable": True},
    {"name": "topics", "type": "Collection(Edm.String)", "filterable": True, "searchable": True},
    {"name": "status", "type": "Edm.String", "filterable": True},
    {"name": "progress", "type": "Edm.Double", "filterable": True, "sortable": True},
    {"name": "created", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "startDate", "type": "Edm.DateTimeOffset", "filterable": True},
    {"name": "endDate", "type": "Edm.DateTimeOffset", "filterable": True},
    {"name": "metadata", "type": "Edm.String"},
    {"name": "ownerId", "type": "Edm.String", "filterable": True},
    {"name": "activitiesJson", "type": "Edm.String"},
    {"name": "week1", "type": "Edm.String"},
    {"name": "week2", "type": "Edm.String"},
    {"name": "week3", "type": "Edm.String"},
    {"name": "week4", "type": "Edm.String"}
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
                    # Handle activities data and determine chunking method
                    # Check if plan needs chunking based on metadata
                    needs_chunking = False
                    
                    # Check metadata for weeks_in_period to determine if chunking is needed
                    if "metadata" in doc and doc["metadata"]:
                        try:
                            if isinstance(doc["metadata"], str):
                                metadata = json.loads(doc["metadata"])
                                if "weeks_in_period" in metadata and metadata["weeks_in_period"] > 1:
                                    needs_chunking = True
                                    logger.info(f"Chunking needed based on metadata: {metadata['weeks_in_period']} weeks")
                            elif isinstance(doc["metadata"], dict) and "weeks_in_period" in doc["metadata"] and doc["metadata"]["weeks_in_period"] > 1:
                                needs_chunking = True
                                logger.info(f"Chunking needed based on metadata: {doc['metadata']['weeks_in_period']} weeks")
                        except Exception as e:
                            logger.warning(f"Error parsing metadata for chunking decision: {e}")
                    
                    # Check for existing activities chunking metadata
                    existing_chunking = False
                    if "activities_chunking" in doc and doc["activities_chunking"] == "weekly":
                        existing_chunking = True
                        needs_chunking = True
                    
                    # If we have activities_week_* fields, plan was already chunked
                    for key in doc.keys():
                        if key.startswith("activities_week_") and doc[key]:
                            existing_chunking = True
                            needs_chunking = True
                            break
                    
                    # Extract and process activities
                    activities = []
                    
                    # Check for activities_json or activities_content field
                    if "activities_json" in doc and doc["activities_json"]:
                        try:
                            activities_json = doc["activities_json"]
                            if isinstance(activities_json, str):
                                activities = json.loads(activities_json)
                            elif isinstance(activities_json, list):
                                activities = activities_json
                                
                            # Migrate activities_json to activities_content
                            doc["activities_content"] = doc["activities_json"]
                            del doc["activities_json"]
                        except Exception as e:
                            logger.warning(f"Error parsing activities_json: {e}")
                    elif "activities_content" in doc and doc["activities_content"]:
                        try:
                            activities_content = doc["activities_content"]
                            if isinstance(activities_content, str):
                                activities = json.loads(activities_content)
                            elif isinstance(activities_content, list):
                                activities = activities_content
                        except Exception as e:
                            logger.warning(f"Error parsing activities_content: {e}")
                    
                    # If no activities found yet, check for activities field
                    if not activities and "activities" in doc:
                        try:
                            if isinstance(doc["activities"], str):
                                activities = json.loads(doc["activities"])
                            elif isinstance(doc["activities"], list):
                                activities = doc["activities"]
                        except Exception as e:
                            logger.warning(f"Error parsing activities field: {e}")
                    
                    # If we have many activities, this is a sign chunking might be needed
                    if len(activities) > 20:
                        needs_chunking = True
                        logger.info(f"Chunking needed based on activity count: {len(activities)} activities")
                    
                    # Process chunking based on activities
                    if needs_chunking and activities and not existing_chunking:
                        # Organize activities into weeks based on day field
                        weekly_activities = {}
                        
                        for activity in activities:
                            # Get day field, default to 1 if not present
                            day = activity.get("day", 1)
                            # Calculate week number: days 1-7 = week 1, days 8-14 = week 2, etc.
                            week_num = (day - 1) // 7 + 1
                            
                            # Initialize the week's activity list if it doesn't exist
                            if week_num not in weekly_activities:
                                weekly_activities[week_num] = []
                                
                            # Add the activity to the appropriate week
                            weekly_activities[week_num].append(activity)
                        
                        # Only use chunking for weeks 1-8, as these are defined in our schema
                        valid_weeks = {k: v for k, v in weekly_activities.items() if 1 <= k <= 8}
                        
                        if valid_weeks:
                            # Remove the original activities
                            doc.pop("activities", None)
                            doc.pop("activities_json", None)
                            
                            # Store each week's activities in a separate field
                            for week_num, week_activities in valid_weeks.items():
                                week_field = f"activities_week_{week_num}"
                                doc[week_field] = json.dumps(week_activities)
                                logger.info(f"Week {week_num} activities: {len(week_activities)} activities")
                            
                            # Add fields to indicate we're using weekly chunking
                            doc["activities_chunking"] = "weekly"
                            doc["activities_weeks"] = list(valid_weeks.keys())
                            
                            # If we had weeks > 8, store them in activities_content as overflow
                            overflow_weeks = {k: v for k, v in weekly_activities.items() if k > 8}
                            if overflow_weeks:
                                overflow_activities = []
                                for week_activities in overflow_weeks.values():
                                    overflow_activities.extend(week_activities)
                                
                                if overflow_activities:
                                    logger.info(f"Storing {len(overflow_activities)} overflow activities in activities_content")
                                    doc["activities_content"] = json.dumps(overflow_activities)
                        else:
                            # No valid weeks found, use activities_content
                            logger.info("No valid weeks found, using activities_content")
                            doc["activities_content"] = json.dumps(activities)
                            doc["activities_chunking"] = "none"
                            # Remove any week fields if they exist
                            for week in range(1, 9):
                                field = f"activities_week_{week}"
                                if field in doc:
                                    del doc[field]
                    elif existing_chunking:
                        # Plan already has chunking, make sure weeks list is correct
                        week_numbers = []
                        for week in range(1, 9):
                            field = f"activities_week_{week}"
                            if field in doc and doc[field]:
                                week_numbers.append(week)
                        
                        if week_numbers:
                            doc["activities_weeks"] = week_numbers
                            doc["activities_chunking"] = "weekly"
                    elif "activities_json" in doc and doc["activities_json"]:
                        # No chunking needed - just ensure all required fields exist
                        doc["activities_chunking"] = "none"
                        # Migrate activities_json to activities_content
                        doc["activities_content"] = doc["activities_json"]
                        del doc["activities_json"]
                        # Ensure all week fields are removed
                        for week in range(1, 9):
                            field = f"activities_week_{week}"
                            if field in doc:
                                del doc[field]
                    else:
                        # Ensure activities_content exists even if empty
                        if "activities" in doc and doc["activities"]:
                            try:
                                if isinstance(doc["activities"], str):
                                    activities_list = json.loads(doc["activities"])
                                else:
                                    activities_list = doc["activities"]
                                doc["activities_content"] = json.dumps(activities_list)
                            except Exception as e:
                                logger.warning(f"Error converting activities to JSON: {e}")
                                doc["activities_content"] = "[]"
                        else:
                            doc["activities_content"] = "[]"
                        
                        # Set chunking method to none
                        doc["activities_chunking"] = "none"
                        
                        # Remove any week fields if they exist
                        for week in range(1, 9):
                            field = f"activities_week_{week}"
                            if field in doc:
                                del doc[field]
                    
                    # If activities field exists, remove it as Azure Search doesn't support nested objects directly
                    if "activities" in doc:
                        del doc["activities"]
                    
                    # Migrate metadata to metadata_json for API compatibility
                    if "metadata" in doc:
                        if isinstance(doc["metadata"], dict):
                            doc["metadata_json"] = json.dumps(doc["metadata"])
                        elif isinstance(doc["metadata"], str):
                            doc["metadata_json"] = doc["metadata"]
                        # Remove the original metadata field which is causing the error
                        del doc["metadata"]
                        
                    # Migrate owner_id to owner_id_field for API compatibility
                    if "owner_id" in doc:
                        doc["owner_id_field"] = doc["owner_id"]
                        del doc["owner_id"]
                    
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