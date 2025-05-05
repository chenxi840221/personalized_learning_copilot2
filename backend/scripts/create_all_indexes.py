#!/usr/bin/env python3
"""Create all required indexes for Personalized Learning Co-pilot.

This script creates or updates all of the indexes needed for the application,
including student-reports, student-profiles, and learning-plans with the owner_id field.
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
# Field definitions                                                           #
###############################################################################

# Student Reports index fields
REPORTS_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "student_id", "type": "Edm.String", "filterable": True},
    {"name": "student_name", "type": "Edm.String", "searchable": True, "filterable": True},
    {"name": "report_type", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "school_name", "type": "Edm.String", "searchable": True, "filterable": True, "facetable": True},
    {"name": "school_year", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "term", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "grade_level", "type": "Edm.Int32", "filterable": True, "facetable": True},
    {"name": "teacher_name", "type": "Edm.String", "searchable": True, "filterable": True},
    {"name": "report_date", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "general_comments", "type": "Edm.String", "searchable": True},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "raw_extracted_text", "type": "Edm.String", "searchable": True},
    {"name": "document_url", "type": "Edm.String"},
    {"name": "owner_id", "type": "Edm.String", "filterable": True},
    {"name": "additional_fields", "type": "Edm.String"},
    
    # Subjects as a complex collection
    {
        "name": "subjects", 
        "type": "Collection(Edm.ComplexType)",
        "fields": [
            {"name": "name", "type": "Edm.String", "searchable": True, "filterable": True, "facetable": True},
            {"name": "grade", "type": "Edm.String", "filterable": True},
            {"name": "comments", "type": "Edm.String", "searchable": True},
            {"name": "achievement_level", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "areas_for_improvement", "type": "Collection(Edm.String)", "searchable": True},
            {"name": "strengths", "type": "Collection(Edm.String)", "searchable": True}
        ]
    },
    
    # Attendance as a complex field
    {
        "name": "attendance",
        "type": "Edm.ComplexType",
        "fields": [
            {"name": "days_present", "type": "Edm.Int32"},
            {"name": "days_absent", "type": "Edm.Int32"},
            {"name": "days_late", "type": "Edm.Int32"}
        ]
    },
    
    # Vector field for embeddings
    {
        "name": "embedding",
        "type": "Collection(Edm.Single)",
        "searchable": True,
        "dimensions": 1536,
        "vectorSearchProfile": "default-profile"
    }
]

# Student Profiles index fields
PROFILES_FIELDS = [
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
    {"name": "current_school_year", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "current_term", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "historical_data", "type": "Edm.String", "searchable": True},
    {"name": "years_and_terms", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    {"name": "owner_id", "type": "Edm.String", "filterable": True},
    
    # Vector field for embeddings
    {
        "name": "embedding", 
        "type": "Collection(Edm.Single)", 
        "searchable": True, 
        "dimensions": 1536, 
        "vectorSearchProfile": "default-profile"
    }
]

# Learning Plans index fields
PLANS_FIELDS = [
    {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
    {"name": "student_id", "type": "Edm.String", "filterable": True},
    {"name": "title", "type": "Edm.String", "searchable": True},
    {"name": "description", "type": "Edm.String", "searchable": True},
    {"name": "subject", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "topics", "type": "Collection(Edm.String)", "filterable": True, "facetable": True},
    # Store activities as JSON string instead of complex collection
    {"name": "activities_json", "type": "Edm.String"},
    {"name": "status", "type": "Edm.String", "filterable": True, "facetable": True},
    {"name": "progress_percentage", "type": "Edm.Double", "filterable": True, "sortable": True},
    {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
    {"name": "start_date", "type": "Edm.DateTimeOffset", "filterable": True},
    {"name": "end_date", "type": "Edm.DateTimeOffset", "filterable": True},
    {"name": "metadata", "type": "Edm.String"},
    {"name": "page_content", "type": "Edm.String", "searchable": True},
    {"name": "owner_id", "type": "Edm.String", "filterable": True},
    
    # Vector field for embeddings
    {
        "name": "embedding", 
        "type": "Collection(Edm.Single)", 
        "searchable": True, 
        "dimensions": 1536, 
        "vectorSearchProfile": "default-profile"
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
    
    # Build the index definition
    index_def = {
        "name": index_name,
        "fields": fields,
        "vectorSearch": {
            "profiles": [
                {
                    "name": "default-profile",
                    "algorithm": "default-algorithm"
                }
            ],
            "algorithms": [
                {
                    "name": "default-algorithm",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "metric": "cosine",
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500
                    }
                }
            ]
        }
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
                        logger.info(f"Index '{index_name}' exists - deleting")
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
# Main                                                                        #
###############################################################################

async def main() -> bool:
    """Create all required indexes."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False

    try:
        # Create each index
        logger.info(f"Creating student reports index: {REPORTS_INDEX_NAME}")
        success1 = await create_index(REPORTS_INDEX_NAME, REPORTS_FIELDS)
        
        logger.info(f"Creating student profiles index: {PROFILES_INDEX_NAME}")
        success2 = await create_index(PROFILES_INDEX_NAME, PROFILES_FIELDS)
        
        logger.info(f"Creating learning plans index: {PLANS_INDEX_NAME}")
        success3 = await create_index(PLANS_INDEX_NAME, PLANS_FIELDS)
        
        if success1 and success2 and success3:
            logger.info("🎉 All indexes created successfully with owner_id field")
            return True
        else:
            logger.error("Failed to create all indexes")
            return False
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(main())