#!/usr/bin/env python3
"""List all Azure AI Search indexes."""
from __future__ import annotations

import asyncio
import logging
import os
import json
import aiohttp
import sys

# Fix import paths for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)  # Add backend to path
sys.path.insert(0, project_root)  # Add project root to path

from dotenv import load_dotenv

# Environment & logging
load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Get settings from environment or settings module
from config.settings import Settings
settings = Settings()

AZURE_SEARCH_ENDPOINT = settings.AZURE_SEARCH_ENDPOINT
AZURE_SEARCH_KEY = settings.AZURE_SEARCH_KEY
API_VERSION = "2024-03-01-Preview"  # Using latest preview API

async def list_indexes():
    """List all Azure AI Search indexes."""
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
            
            # Get index definition
            list_url = f"{AZURE_SEARCH_ENDPOINT}/indexes?api-version={API_VERSION}"
            async with session.get(list_url, headers=headers) as response:
                if response.status == 200:
                    indexes = await response.json()
                    logger.info(f"Available indexes:")
                    for idx in indexes.get("value", []):
                        logger.info(f"  - {idx['name']}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to list indexes: {response.status} - {error_text}")
                    return False
                
    except Exception as e:
        logger.error(f"Error listing indexes: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(list_indexes())