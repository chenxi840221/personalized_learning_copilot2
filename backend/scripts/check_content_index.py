#!/usr/bin/env python3
"""Check the educational-content index in Azure Search.

This script checks if the educational-content index exists in Azure Search,
counts how many documents are in the index, and shows sample content for each subject.
If the index is empty or doesn't exist, it provides instructions for running
the create_search_indexes.py script to create and populate the index.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import json
import aiohttp
from typing import List, Dict, Any, Optional
from collections import defaultdict

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

# Get environment variables
AZURE_SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY")
CONTENT_INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX_NAME", "educational-content")
API_VERSION = "2024-03-01-Preview"  # Using latest preview API

###############################################################################
# Helpers                                                                     #
###############################################################################

async def check_index_exists(index_name: str) -> bool:
    """Check if an index exists in Azure Search."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return False
        
    try:
        # Use the REST API to check if the index exists
        headers = {
            "api-key": AZURE_SEARCH_KEY,
            "Content-Type": "application/json"
        }
        
        # Use aiohttp for the HTTP request
        async with aiohttp.ClientSession() as session:
            url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}?api-version={API_VERSION}"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"✅ Index {index_name} exists")
                    return True
                elif response.status == 404:
                    logger.warning(f"❌ Index {index_name} does not exist")
                    return False
                else:
                    logger.error(f"Error checking if index {index_name} exists: {response.status}")
                    text = await response.text()
                    logger.error(f"Response: {text}")
                    return False
    except Exception as e:
        logger.error(f"Error checking if index {index_name} exists: {e}")
        return False

async def count_documents(index_name: str) -> int:
    """Count the number of documents in an index."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return 0
        
    try:
        # Use the search API with top=0 to get the count
        # This is more reliable than the /count endpoint
        headers = {
            "api-key": AZURE_SEARCH_KEY,
            "Content-Type": "application/json"
        }
        
        # Use aiohttp for the HTTP request
        async with aiohttp.ClientSession() as session:
            # Search with top=0 to just get the count
            url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}/docs/search?api-version={API_VERSION}"
            body = {
                "search": "*",  # Match all documents
                "top": 0,       # Don't return any actual documents
                "count": True   # Include the total count
            }
            
            async with session.post(url, headers=headers, json=body) as response:
                if response.status == 200:
                    result = await response.json()
                    count = result.get("@odata.count", 0)
                    logger.info(f"📊 Index {index_name} contains {count} documents")
                    return count
                else:
                    logger.error(f"Error counting documents in index {index_name}: {response.status}")
                    text = await response.text()
                    logger.error(f"Response: {text}")
                    
                    # Try an alternate method if the first one fails
                    logger.info("Trying alternate method to count documents...")
                    try:
                        # Just search for any document to verify there are documents
                        alt_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}/docs/search?api-version={API_VERSION}"
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
                                    return 1  # Return 1 to indicate documents exist
                            return 0
                    except Exception as alt_err:
                        logger.error(f"Alternate counting method failed: {alt_err}")
                        return 0
    except Exception as e:
        logger.error(f"Error counting documents in index {index_name}: {e}")
        return 0

async def get_sample_content(index_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get sample content for each subject in the index."""
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        return {}
        
    try:
        # Use the REST API to search for all subjects
        headers = {
            "api-key": AZURE_SEARCH_KEY,
            "Content-Type": "application/json"
        }
        
        # First try to get unique subjects using facets
        subjects = []
        async with aiohttp.ClientSession() as session:
            # First query to get facets for subject field
            url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}/docs/search?api-version={API_VERSION}"
            body = {
                "search": "*",
                "facets": ["subject"],
                "top": 0
            }
            
            try:
                async with session.post(url, headers=headers, json=body) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Extract subjects from facets
                        if "@search.facets" in result and "subject" in result["@search.facets"]:
                            for facet in result["@search.facets"]["subject"]:
                                subjects.append(facet["value"])
                            logger.info(f"📚 Found subjects: {', '.join(subjects)}")
                    else:
                        logger.error(f"Error getting subjects with facets: {response.status}")
                        text = await response.text()
                        logger.error(f"Response: {text}")
            except Exception as e:
                logger.error(f"Error with facet query: {e}")
        
        # If facets failed, try to get subjects by just searching all documents
        if not subjects:
            logger.info("Trying alternate method to get subjects...")
            async with aiohttp.ClientSession() as session:
                # Just search for docs and extract unique subjects
                url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}/docs/search?api-version={API_VERSION}"
                body = {
                    "search": "*",
                    "select": "subject",
                    "top": 100  # Get up to 100 documents
                }
                
                try:
                    async with session.post(url, headers=headers, json=body) as response:
                        if response.status == 200:
                            result = await response.json()
                            # Extract unique subjects from results
                            subject_set = set()
                            for doc in result.get("value", []):
                                if "subject" in doc and doc["subject"]:
                                    subject_set.add(doc["subject"])
                            subjects = list(subject_set)
                            if subjects:
                                logger.info(f"📚 Found subjects using alternate method: {', '.join(subjects)}")
                        else:
                            logger.error(f"Error getting subjects with alternate method: {response.status}")
                            text = await response.text()
                            logger.error(f"Response: {text}")
                except Exception as e:
                    logger.error(f"Error with alternate query: {e}")
        
        # If we still have no subjects, use the predefined list of main subjects
        if not subjects:
            logger.warning("Could not retrieve subjects from index. Using predefined list.")
            subjects = ["Mathematics", "Science", "English", "History", "Art", "Geography"]
        
        # Now get sample content for each subject
        samples_by_subject = {}
        async with aiohttp.ClientSession() as session:
            for subject in subjects:
                url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{index_name}/docs/search?api-version={API_VERSION}"
                body = {
                    "search": "*",
                    "filter": f"subject eq '{subject}'",
                    "top": 2,  # Get 2 samples per subject
                    "select": "id,title,subject,content_type,difficulty_level,url"
                }
                
                try:
                    async with session.post(url, headers=headers, json=body) as response:
                        if response.status == 200:
                            result = await response.json()
                            samples = result.get("value", [])
                            if samples:
                                samples_by_subject[subject] = samples
                        else:
                            logger.error(f"Error getting sample content for subject {subject}: {response.status}")
                            text = await response.text()
                            logger.error(f"Response: {text}")
                except Exception as e:
                    logger.error(f"Error getting samples for {subject}: {e}")
        
        return samples_by_subject
    except Exception as e:
        logger.error(f"Error getting sample content: {e}")
        return {}

###############################################################################
# Main                                                                        #
###############################################################################

async def main():
    """Check the educational-content index in Azure Search."""
    # Check environment variables
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_KEY:
        logger.error("❌ AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY must be set.")
        logger.error("Please set these environment variables and try again.")
        return False
    
    # Check if index exists
    index_exists = await check_index_exists(CONTENT_INDEX_NAME)
    if not index_exists:
        logger.warning(f"❌ Index {CONTENT_INDEX_NAME} does not exist.")
        logger.info("To create and populate the index, run:")
        logger.info(f"cd {backend_dir} && python3 scripts/create_search_indexes.py")
        return False
    
    # Try to get sample content directly without counting first
    # This is more reliable since we'll know the index has content if we get results
    logger.info("Retrieving sample content by subject...")
    samples = await get_sample_content(CONTENT_INDEX_NAME)
    
    # Count documents - but don't make this a blocker
    doc_count = await count_documents(CONTENT_INDEX_NAME)
    
    # We've found content, so the index is not empty
    has_content = len(samples) > 0
    
    if not has_content and doc_count == 0:
        logger.warning(f"❌ Index {CONTENT_INDEX_NAME} appears to be empty (no content found).")
        logger.info("To populate the index, run:")
        logger.info(f"cd {backend_dir} && python3 scripts/create_search_indexes.py")
        return False
    
    # Show sample content
    if samples:
        # Some sample content was found, show it
        print("\n" + "=" * 80)
        print(f"📊 CONTENT INDEX SUMMARY: {CONTENT_INDEX_NAME}")
        print("=" * 80)
        if doc_count > 0:
            print(f"Total documents: {doc_count}")
        else:
            print("Total documents: Unknown (count API failed, but documents exist)")
        print(f"Subjects found with content: {len(samples)}")
        print("=" * 80 + "\n")
        
        # Display sample content
        for subject, content_items in samples.items():
            print(f"📚 SUBJECT: {subject}")
            print("-" * 60)
            for item in content_items:
                print(f"  📄 {item.get('title', 'Untitled')}")
                print(f"     ID: {item.get('id', 'Unknown')}")
                print(f"     Type: {item.get('content_type', 'Unknown')}")
                print(f"     Difficulty: {item.get('difficulty_level', 'Unknown')}")
                print(f"     URL: {item.get('url', 'No URL')}")
                print()
            print()
    else:
        # No sample content was found - this is a problem
        # But we'll check again with the direct API call
        logger.warning("❌ Could not retrieve sample content with standard API call.")
        
        # Try one more direct approach to get any content
        try:
            logger.info("Making one last attempt to verify content...")
            headers = {
                "api-key": AZURE_SEARCH_KEY,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{CONTENT_INDEX_NAME}/docs/search?api-version={API_VERSION}"
                body = {
                    "search": "*",
                    "top": 2
                }
                
                async with session.post(url, headers=headers, json=body) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "value" in result and result["value"]:
                            logger.info("✅ Content found using direct API call")
                            print("\n" + "=" * 80)
                            print(f"📊 CONTENT INDEX SUMMARY: {CONTENT_INDEX_NAME}")
                            print("=" * 80)
                            print("Total documents: Unknown (count API failed, but documents exist)")
                            print("Subjects: Unknown (facet API failed)")
                            print("=" * 80 + "\n")
                            
                            # Show the documents we found
                            for item in result["value"]:
                                print(f"  📄 {item.get('title', 'Untitled')}")
                                print(f"     ID: {item.get('id', 'Unknown')}")
                                if "subject" in item:
                                    print(f"     Subject: {item.get('subject', 'Unknown')}")
                                if "content_type" in item:
                                    print(f"     Type: {item.get('content_type', 'Unknown')}")
                                if "difficulty_level" in item:
                                    print(f"     Difficulty: {item.get('difficulty_level', 'Unknown')}")
                                if "url" in item:
                                    print(f"     URL: {item.get('url', 'No URL')}")
                                print()
                            
                            has_content = True
                        else:
                            logger.warning("No documents found in the index with direct API call")
                    else:
                        logger.error(f"Direct API call failed: {response.status}")
        except Exception as e:
            logger.error(f"Error in direct API call: {e}")
    
    # Check if we have all the main subjects
    main_subjects = ["Mathematics", "Science", "English", "History", "Art", "Geography"]
    missing_subjects = [subject for subject in main_subjects if subject not in samples]
    
    if missing_subjects and has_content:
        logger.warning(f"⚠️ Missing content for subjects: {', '.join(missing_subjects)}")
        logger.info("To ensure all subjects have content, recreate the index:")
        logger.info(f"cd {backend_dir} && python3 scripts/create_search_indexes.py")
    elif has_content:
        logger.info("✅ Content found for all main subjects")
    
    # Final recommendations
    if has_content:
        logger.info("✅ Educational content index appears to have content")
        logger.info("If you're still experiencing search issues in the application, check:")
        logger.info("1. API version compatibility in search requests")
        logger.info("2. Filter expressions in search queries")
        logger.info("3. Permissions and network access to Azure Search")
        logger.info(f"4. Run the application with LOGGING_LEVEL=DEBUG for more detailed logs")
    else:
        logger.warning("❌ Could not confirm content in the index")
        logger.info("Please recreate and populate the index with:")
        logger.info(f"cd {backend_dir} && python3 scripts/create_search_indexes.py")
    
    return has_content

if __name__ == "__main__":
    asyncio.run(main())