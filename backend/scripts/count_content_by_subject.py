#!/usr/bin/env python
# backend/scripts/count_content_by_subject.py

"""
Utility script to count content items by subject in the Azure AI Search index.
This script provides a quick overview of content distribution across subjects.

Usage:
    python count_content_by_subject.py
"""

import asyncio
import sys
import os
from collections import Counter
from tabulate import tabulate

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

async def count_content_by_subject(search_service, index_name):
    """
    Count the number of content items per subject in the Azure AI Search index.
    
    Args:
        search_service: The initialized search service
        index_name: The name of the index to query
        
    Returns:
        A dictionary of subject counts
    """
    try:
        print(f"\n=== Counting Content by Subject in '{index_name}' ===\n")
        
        # First get all the available subjects
        all_subjects_result = await search_service.search_documents(
            index_name=index_name,
            query="*",
            top=100,
            select="subject"
        )
        
        # Extract unique subjects
        unique_subjects = set()
        for item in all_subjects_result:
            if "subject" in item and item["subject"]:
                unique_subjects.add(item["subject"])
        
        print(f"Found {len(unique_subjects)} unique subjects")
        
        # Count items for each subject
        subject_counts = {}
        for subject in unique_subjects:
            filter_expression = f"subject eq '{subject}'"
            
            try:
                # Query with select=id to minimize data transfer
                result = await search_service.search_documents(
                    index_name=index_name,
                    query="*",
                    filter=filter_expression,
                    top=1000,  # Get up to 1000 items
                    select="id"
                )
                
                count = len(result) if result else 0
                
                # If we got exactly 1000 items, there might be more
                if count == 1000:
                    print(f"Note: Subject '{subject}' may have more than 1000 items")
                subject_counts[subject] = count
                
            except Exception as count_error:
                print(f"Error getting count for subject '{subject}': {count_error}")
                print("Falling back to retrieving all items...")
                
                # Fallback: retrieve all items and count them
                try:
                    items = await search_service.search_documents(
                        index_name=index_name,
                        query="*",
                        filter=filter_expression,
                        top=1000,  # Retrieve a large number to approximate count
                        select="id"
                    )
                    subject_counts[subject] = len(items) if items else 0
                except Exception as fallback_error:
                    print(f"Error in fallback method for subject '{subject}': {fallback_error}")
                    subject_counts[subject] = -1  # Indicate error
        
        # Get total item count by summing individual subject counts
        # This is an approximation if there are items with no subject or multiple subjects
        total_count = sum(count for count in subject_counts.values() if count >= 0)
        
        print(f"Total count (sum of subjects): {total_count}")
        
        # Sort subjects by count and prepare table data
        table_data = []
        for subject, count in sorted(subject_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_count * 100) if total_count > 0 else 0
            table_data.append([subject, count, f"{percentage:.1f}%"])
        
        # Add total row
        table_data.append(["TOTAL", total_count, "100.0%"])
        
        # Print table
        print(tabulate(table_data, headers=["Subject", "Count", "Percentage"], tablefmt="grid"))
        
        # Check if sum of subject counts matches total count
        sum_subject_counts = sum(count for count in subject_counts.values() if count >= 0)
        if sum_subject_counts != total_count:
            print(f"\nNote: Sum of subject counts ({sum_subject_counts}) differs from total count ({total_count}).")
            print("This may indicate some items have multiple subjects or no subject assigned.")
        
        return subject_counts
        
    except Exception as e:
        print(f"Error counting content by subject: {e}")
        return {}

async def main():
    try:
        # Load settings
        settings = Settings()
        
        # Check if Azure Search is configured
        if not settings.AZURE_SEARCH_ENDPOINT or not settings.AZURE_SEARCH_KEY:
            print("Error: Azure AI Search settings not configured")
            print("Make sure AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY are set in your environment")
            return
        
        # Get search service
        search_service = await get_search_service()
        
        if not search_service:
            print("Error: Failed to initialize search service")
            return
        
        # Define the index name
        index_name = settings.CONTENT_INDEX_NAME or "educational-content"
        
        # Count content by subject
        await count_content_by_subject(search_service, index_name)
        
        print("\nTo view detailed statistics about a specific subject, use:")
        print(f"python scripts/test_content_index.py --subject \"SUBJECT_NAME\" --show-samples")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up any resources
        if 'search_service' in locals() and hasattr(search_service, 'close'):
            await search_service.close()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())