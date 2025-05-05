#!/usr/bin/env python3
"""Check the schema of the learning-plans index in Azure Search.

This script checks the schema of the learning-plans index and prints
the field names and types to help debug field mapping issues.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import json
import aiohttp
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
API_VERSION = "2023-07-01-Preview"  # Using the same API version as in service

# Index name
PLANS_INDEX_NAME = settings.PLANS_INDEX_NAME or "learning-plans"

###############################################################################
# Main function                                                               #
###############################################################################

async def get_index_schema(index_name: str) -> Dict[str, Any]:
    """Get the schema of an Azure Search index."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return {}
        
    try:
        # Use the REST API to get the index schema
        headers = {
            "api-key": AZURE_SEARCH_KEY,
            "Content-Type": "application/json"
        }
        
        # Use aiohttp for the HTTP request
        async with aiohttp.ClientSession() as session:
            url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}?api-version={API_VERSION}"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Successfully retrieved schema for index {index_name}")
                    return result
                else:
                    logger.error(f"Error getting schema for index {index_name}: {response.status}")
                    text = await response.text()
                    logger.error(f"Response: {text}")
                    return {}
    except Exception as e:
        logger.error(f"Error getting schema for index {index_name}: {e}")
        return {}

async def main():
    """Check the schema of the learning-plans index."""
    logger.info(f"Checking schema for index {PLANS_INDEX_NAME}")
    
    # Get the index schema
    schema = await get_index_schema(PLANS_INDEX_NAME)
    
    if not schema:
        logger.error(f"Failed to retrieve schema for index {PLANS_INDEX_NAME}")
        return
    
    # Print the schema fields
    print("\n" + "=" * 80)
    print(f"📊 SCHEMA FOR INDEX: {PLANS_INDEX_NAME}")
    print("=" * 80)
    
    if "fields" in schema:
        print(f"Number of fields: {len(schema['fields'])}")
        print("-" * 60)
        
        # Print field information
        for field in schema["fields"]:
            field_name = field.get("name", "Unknown")
            field_type = field.get("type", "Unknown")
            is_key = field.get("key", False)
            is_filterable = field.get("filterable", False)
            is_searchable = field.get("searchable", False)
            
            # Format field info
            key_str = "🔑 " if is_key else "  "
            filter_str = "🔍 " if is_filterable else "  "
            search_str = "🔎 " if is_searchable else "  "
            
            print(f"{key_str}{filter_str}{search_str} {field_name}: {field_type}")
    else:
        print("No fields found in the schema")
    
    print("=" * 80)
    print("\nLegend:")
    print("🔑 = Key field")
    print("🔍 = Filterable field")
    print("🔎 = Searchable field")
    print("=" * 80)
    
    # Summarize for debugging
    print("\nField names for debugging/reference:")
    if "fields" in schema:
        # Extract just the field names for easy copy-paste
        field_names = [field.get("name") for field in schema["fields"]]
        print(", ".join(field_names))
    print("\n")

if __name__ == "__main__":
    asyncio.run(main())