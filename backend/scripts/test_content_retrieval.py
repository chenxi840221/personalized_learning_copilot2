#!/usr/bin/env python
# backend/scripts/test_content_retrieval.py

"""
Test script to verify the retrieval of content from Azure AI Search 'educational-content' index.
This script tests specifically the retrieval of all content without subject filters
to confirm if the content limit per subject is high enough.

Usage:
    python test_content_retrieval.py
"""

import asyncio
import sys
import os
import time
import json
from collections import Counter, defaultdict

# Fix import paths for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)  # Add backend to path

try:
    from config.settings import Settings
    from services.search_service import get_search_service
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this script from the backend directory")
    sys.exit(1)

async def test_recommendations_endpoint_simulation(search_service, index_name):
    """
    Simulate the behavior of the recommendations endpoint with the same logic 
    that's in the API to verify content retrieval capacity.
    
    Args:
        search_service: The initialized search service
        index_name: The name of the index to query
    """
    print("\n=== Testing All Content Retrieval (Recommendations Endpoint Simulation) ===\n")
    
    try:
        start_time = time.time()
        
        # First, get all available subjects (same as in the endpoint implementation)
        print("Step 1: Getting all available subjects...")
        all_subjects = await search_service.search_documents(
            index_name=index_name,
            query="*",
            top=100,
            select="subject"
        )
        
        # Extract unique subjects
        unique_subjects = set()
        for item in all_subjects:
            if "subject" in item and item["subject"]:
                unique_subjects.add(item["subject"])
        
        print(f"Found {len(unique_subjects)} unique subjects: {unique_subjects}")
        
        # Define the items per subject (matching the endpoint setting)
        items_per_subject = 1000  # This is the value we increased
        all_recommendations = []
        
        # Retrieve content for each subject (same as the endpoint logic)
        print(f"\nStep 2: Retrieving up to {items_per_subject} items per subject...")
        
        for subj in unique_subjects:
            subj_filter = f"subject eq '{subj}'"
            print(f"  - Retrieving items for subject: {subj}")
            
            subject_content = await search_service.search_documents(
                index_name=index_name,
                query="*",
                filter=subj_filter,
                top=items_per_subject,
                select="id,title,description,subject,content_type,difficulty_level,grade_level"
            )
            
            if subject_content:
                print(f"    Found {len(subject_content)} items for subject '{subj}'")
                all_recommendations.extend(subject_content)
            else:
                print(f"    No content found for subject '{subj}'")
        
        # Calculate total retrieval time
        elapsed_time = time.time() - start_time
        
        # Display results
        print(f"\nRetrieved a total of {len(all_recommendations)} content items across all subjects")
        print(f"Retrieval time: {elapsed_time:.2f} seconds")
        
        # Analyze content by subject
        subject_counts = Counter()
        for item in all_recommendations:
            if "subject" in item and item["subject"]:
                subject_counts[item["subject"]] += 1
        
        print("\nContent distribution by subject:")
        for subject, count in subject_counts.items():
            print(f"  - {subject}: {count} items")
            
        # Verify uniqueness of items
        unique_ids = set()
        duplicate_count = 0
        
        for item in all_recommendations:
            if item["id"] in unique_ids:
                duplicate_count += 1
            else:
                unique_ids.add(item["id"])
        
        print(f"\nUnique items: {len(unique_ids)}")
        print(f"Duplicate items: {duplicate_count}")
        
        # Additional analysis - content types
        content_types = Counter()
        for item in all_recommendations:
            if "content_type" in item and item["content_type"]:
                content_types[item["content_type"]] += 1
        
        print("\nContent types distribution:")
        for content_type, count in content_types.most_common():
            print(f"  - {content_type}: {count} items")
        
    except Exception as e:
        print(f"Error during test: {e}")

async def test_direct_retrieval(search_service, index_name):
    """
    Test direct retrieval of all content without filters to see maximum capacity.
    
    Args:
        search_service: The initialized search service
        index_name: The name of the index to query
    """
    print("\n=== Testing Direct Content Retrieval ===\n")
    
    try:
        start_time = time.time()
        
        print("Retrieving all content directly without filters...")
        all_content = await search_service.search_documents(
            index_name=index_name,
            query="*",
            filter=None,
            top=1000,  # Try to get a large number of items
            select="id,title,subject,content_type"
        )
        
        # Calculate total retrieval time
        elapsed_time = time.time() - start_time
        
        # Display results
        print(f"\nDirectly retrieved {len(all_content)} content items")
        print(f"Retrieval time: {elapsed_time:.2f} seconds")
        
        # Analyze subject distribution
        subject_counts = Counter()
        for item in all_content:
            if "subject" in item and item["subject"]:
                subject_counts[item["subject"]] += 1
        
        print("\nContent distribution by subject:")
        for subject, count in subject_counts.most_common():
            print(f"  - {subject}: {count} items")
        
    except Exception as e:
        print(f"Error during direct retrieval test: {e}")

async def test_pagination(search_service, index_name):
    """
    Test the pagination capability to see how many items we can retrieve in total.
    
    Args:
        search_service: The initialized search service
        index_name: The name of the index to query
    """
    print("\n=== Testing Content Pagination ===\n")
    
    try:
        start_time = time.time()
        
        total_items = []
        page = 1
        limit = 100  # Items per page
        
        print("Retrieving content using pagination...")
        
        while True:
            skip_value = (page - 1) * limit
            print(f"  - Fetching page {page} (skip={skip_value}, limit={limit})...")
            
            page_items = await search_service.search_documents(
                index_name=index_name,
                query="*",
                filter=None,
                top=limit,
                skip=skip_value,
                select="id,title,subject"
            )
            
            if not page_items or len(page_items) == 0:
                print(f"    No more items found after page {page-1}")
                break
            
            total_items.extend(page_items)
            print(f"    Retrieved {len(page_items)} items")
            
            page += 1
            
            # Safety limit to prevent infinite loops
            if page > 10:
                print("    Reached maximum page limit (10), stopping")
                break
        
        # Calculate total retrieval time
        elapsed_time = time.time() - start_time
        
        # Display results
        print(f"\nRetrieved {len(total_items)} items through pagination")
        print(f"Retrieval time: {elapsed_time:.2f} seconds")
        
        # Verify uniqueness of items
        unique_ids = set(item["id"] for item in total_items)
        print(f"Unique items: {len(unique_ids)}")
        print(f"Duplicate items: {len(total_items) - len(unique_ids)}")
        
    except Exception as e:
        print(f"Error during pagination test: {e}")

async def main():
    try:
        # Load settings
        settings = Settings()
        
        # Check if Azure Search is configured
        if not settings.AZURE_SEARCH_ENDPOINT or not settings.AZURE_SEARCH_KEY:
            print("Error: Azure AI Search settings not configured")
            return
        
        # Get search service
        search_service = await get_search_service()
        
        if not search_service:
            print("Error: Failed to initialize search service")
            return
        
        # Define the index name
        index_name = settings.CONTENT_INDEX_NAME or "educational-content"
        
        # First, get an approximation of total items by retrieving with a high limit
        print("Getting approximation of total items...")
        total_result = await search_service.search_documents(
            index_name=index_name,
            query="*",
            top=1000,
            select="id"  # Only get IDs to minimize data transfer
        )
        
        total_count = len(total_result) if total_result else 0
        print(f"\n=== Azure AI Search Index: '{index_name}' ===")
        print(f"Total content items in index: {total_count}")
        
        # Run the tests
        await test_recommendations_endpoint_simulation(search_service, index_name)
        await test_direct_retrieval(search_service, index_name)
        await test_pagination(search_service, index_name)
        
        print("\n=== Test Summary ===")
        print("Tests completed successfully!")
        print(f"The index contains {total_count} total items.")
        print("Check the individual test results above for details on content retrieval capacity.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up any resources
        if 'search_service' in locals() and hasattr(search_service, 'close'):
            await search_service.close()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())