#!/usr/bin/env python
# backend/scripts/update_report_index.py
import logging
import argparse
import sys
import os
import json
import requests

# Fix import paths for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)  # Add backend to path
sys.path.insert(0, project_root)  # Add project root to path

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_student_reports_index():
    """Update the student reports index in Azure AI Search using REST API."""
    # Import settings
    from config.settings import Settings
    settings = Settings()
    
    if not settings.AZURE_SEARCH_ENDPOINT or not settings.AZURE_SEARCH_KEY:
        logger.error("Azure AI Search settings not configured")
        return False
    
    # Define API version
    api_version = "2023-07-01-Preview"
    
    # Define the index name
    index_name = settings.REPORTS_INDEX_NAME
    
    # Define headers
    headers = {
        "Content-Type": "application/json",
        "api-key": settings.AZURE_SEARCH_KEY
    }
    
    # Define the index schema with vector search capability
    index_schema = {
        "name": index_name,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "student_id", "type": "Edm.String", "filterable": True},
            {"name": "report_type", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "school_name", "type": "Edm.String", "searchable": True, "filterable": True, "facetable": True},
            {"name": "school_year", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "term", "type": "Edm.String", "filterable": True, "facetable": True},
            {"name": "grade_level", "type": "Edm.Int32", "filterable": True, "facetable": True},
            {"name": "report_date", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
            {"name": "created_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
            {"name": "updated_at", "type": "Edm.DateTimeOffset", "filterable": True, "sortable": True},
            {"name": "raw_extracted_text", "type": "Edm.String", "searchable": True},
            {"name": "document_url", "type": "Edm.String"},
            {"name": "teacher_name", "type": "Edm.String", "searchable": True},
            {"name": "general_comments", "type": "Edm.String", "searchable": True},
            
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
            
            # Store encrypted fields as a string dictionary
            {"name": "encrypted_fields", "type": "Edm.String"},  # Store as JSON string
            
            # Vector field for embeddings - no metadata for simplicity
            {
                "name": "embedding",
                "type": "Collection(Edm.Single)",
                "dimensions": 1536,
                "vectorSearchConfiguration": "default"
            },
            
            # Add indexing status field
            {"name": "indexing_status", "type": "Edm.String"}
        ],
        "vectorSearch": {
            "algorithmConfigurations": [
                {
                    "name": "default",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                }
            ]
        }
    }
    
    try:
        # Check if index exists
        index_url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{index_name}?api-version={api_version}"
        
        response = requests.get(index_url, headers=headers)
        
        if response.status_code == 200:
            logger.info(f"Index {index_name} already exists, deleting it first...")
            delete_url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{index_name}?api-version={api_version}"
            delete_response = requests.delete(delete_url, headers=headers)
            
            if delete_response.status_code in (200, 204):
                logger.info(f"Successfully deleted existing index {index_name}")
            else:
                logger.warning(f"Failed to delete index, status: {delete_response.status_code}")
            
            # Use create API - always create a new index
            logger.info(f"Creating index {index_name}...")
            index_url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes?api-version={api_version}"
            method = requests.post
            action = "created"
        elif response.status_code == 404:
            logger.info(f"Creating index {index_name}...")
            index_url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes?api-version={api_version}"
            method = requests.post
            action = "created"
        else:
            response.raise_for_status()
        
        # Create or update the index
        response = method(index_url, headers=headers, json=index_schema)
        
        if response.status_code in (200, 201):
            logger.info(f"Index {index_name} {action} successfully")
            return True
        else:
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Unknown error")
            except json.JSONDecodeError:
                error_message = f"HTTP {response.status_code}: {response.text}"
                
            logger.error(f"Error {action} index: {error_message}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating/updating index: {e}")
        return False

# Make the function publicly accessible
def create_reports_index():
    """Wrapper function that creates the student reports index."""
    return update_student_reports_index()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update student reports index in Azure AI Search")
    args = parser.parse_args()
    
    result = update_student_reports_index()
    
    if result:
        logger.info("Student reports index updated successfully")
    else:
        logger.error("Failed to update student reports index")
        sys.exit(1)