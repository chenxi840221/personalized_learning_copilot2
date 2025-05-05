#!/usr/bin/env python3
"""Update Azure AI Search indexes to add owner_id field for user isolation.

This script adds the owner_id field to student-reports, student-profiles, and
learning-plans indexes to enable user-based access control.
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
API_VERSION = "2024-03-01-Preview"  # Using latest preview API

# Index names
REPORTS_INDEX_NAME = settings.REPORTS_INDEX_NAME
PROFILES_INDEX_NAME = "student-profiles"
PLANS_INDEX_NAME = "learning-plans"

###############################################################################
# Helpers                                                                     #
###############################################################################

async def get_index_definition(index_name: str) -> Optional[Dict[str, Any]]:
    """Get the definition of an existing index."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return None
    
    try:
        # Set up aiohttp session
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            # Get index definition
            index_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}?api-version={API_VERSION}"
            async with session.get(index_url, headers=headers) as response:
                if response.status == 200:
                    index_def = await response.json()
                    logger.info(f"Successfully retrieved index definition for '{index_name}'")
                    return index_def
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to get index definition: {response.status} - {error_text}")
                    return None
                
    except Exception as e:
        logger.error(f"Error getting index definition: {e}")
        return None

async def update_index_with_owner_id(index_name: str) -> bool:
    """Update an index definition to add the owner_id field."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
    
    try:
        # Get current index definition
        index_def = await get_index_definition(index_name)
        if not index_def:
            logger.error(f"Could not retrieve index definition for '{index_name}'")
            return False
        
        # Check if owner_id field already exists
        fields = index_def.get("fields", [])
        field_names = [field.get("name") for field in fields]
        
        if "owner_id" in field_names:
            logger.info(f"Index '{index_name}' already has owner_id field")
            return True
        
        # Add owner_id field to fields
        owner_id_field = {
            "name": "owner_id",
            "type": "Edm.String",
            "filterable": True
        }
        
        # Fix vector search configuration
        vector_search = index_def.get("vectorSearch", {})
        
        # Check if we need to update embedding field configuration
        for field in fields:
            if field.get("name") == "embedding" and field.get("dimensions"):
                # Check if we need to add vectorSearchProfile
                if not field.get("vectorSearchProfile") and vector_search:
                    # Create necessary configuration in vectorSearch if needed
                    if not vector_search.get("profiles"):
                        # Add default profile
                        vector_search["profiles"] = [
                            {
                                "name": "default-profile",
                                "algorithm": "default"
                            }
                        ]
                    
                    # Set vectorSearchProfile on the embedding field
                    field["vectorSearchProfile"] = "default-profile"
                    logger.info(f"Updated embedding field with vectorSearchProfile")
                
        # Rebuild index definition with new field
        fields.append(owner_id_field)
        index_def["fields"] = fields
        
        if vector_search:
            index_def["vectorSearch"] = vector_search
            
        # Make sure vectorSearch.profiles exists if algorithms exist
        if "vectorSearch" in index_def and "algorithms" in index_def["vectorSearch"]:
            if not index_def["vectorSearch"].get("profiles"):
                # Add a default profile if algorithms are defined
                default_algo = index_def["vectorSearch"]["algorithms"][0]["name"]
                index_def["vectorSearch"]["profiles"] = [
                    {
                        "name": "default-profile",
                        "algorithm": default_algo
                    }
                ]
                logger.info(f"Added default profile to vectorSearch using algorithm {default_algo}")
        
        # Update the index
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "api-key": AZURE_SEARCH_KEY
            }
            
            # Delete the existing index
            delete_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}?api-version={API_VERSION}"
            async with session.delete(delete_url, headers=headers) as response:
                if response.status == 204:
                    logger.info(f"Successfully deleted index '{index_name}'")
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to delete index: {response.status} - {error_text}")
                    return False
            
            # Create the index with updated definition
            create_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            async with session.post(create_url, headers=headers, json=index_def) as response:
                if response.status == 201:
                    logger.info(f"Successfully updated index '{index_name}' with owner_id field")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to update index: {response.status} - {error_text}")
                    # Log the full request for debugging
                    logger.info(f"Request payload: {json.dumps(index_def)}")
                    return False
                
    except Exception as e:
        logger.error(f"Error updating index: {e}")
        return False

###############################################################################
# Main                                                                        #
###############################################################################

async def main() -> bool:
    """Update all indexes with owner_id field."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False

    try:
        # Update each index
        success1 = await update_index_with_owner_id(REPORTS_INDEX_NAME)
        success2 = await update_index_with_owner_id(PROFILES_INDEX_NAME)
        success3 = await update_index_with_owner_id(PLANS_INDEX_NAME)
        
        if success1 and success2 and success3:
            logger.info("🎉 All indexes updated successfully with owner_id field")
            return True
        else:
            logger.error("Failed to update all indexes")
            return False
        
    except Exception as e:
        logger.error(f"Error updating indexes: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(main())