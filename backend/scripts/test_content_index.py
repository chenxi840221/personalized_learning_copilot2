#!/usr/bin/env python
# backend/scripts/test_content_index.py

"""
Test script to retrieve and display information from Azure AI Search index 'educational-content'.
This script can be used to verify the content index functionality and display statistics.

Usage:
    python test_content_index.py [--subject SUBJECT] [--count COUNT] [--show-samples]
"""

import asyncio
import argparse
import os
import sys
import json
from tabulate import tabulate
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

async def get_content_stats(search_service, index_name, subject=None, count=100, show_samples=False):
    """
    Get statistics and information about the content in Azure AI Search index.
    
    Args:
        search_service: The initialized search service
        index_name: The name of the index to query
        subject: Optional subject filter
        count: Number of items to retrieve for analysis
        show_samples: Whether to display sample items
        
    Returns:
        Statistics about the content in the index
    """
    print(f"\n=== Testing connection to Azure AI Search index: '{index_name}' ===\n")
    
    try:
        # Build filter if subject is provided
        filter_expression = None
        if subject:
            if subject.lower() in ['math', 'mathematics']:
                filter_expression = "(subject eq 'Math' or subject eq 'Mathematics' or subject eq 'Maths')"
            else:
                filter_expression = f"subject eq '{subject}'"
            
            print(f"Filtering by subject: {subject} (Filter: {filter_expression})")
        
        # Get total count of documents in the index by retrieving all IDs
        try:
            total_result = await search_service.search_documents(
                index_name=index_name,
                query="*",
                filter=filter_expression,
                top=1000,
                select="id"  # Only retrieve IDs to minimize data transfer
            )
            
            total_count = len(total_result) if total_result else 0
            print(f"Found {total_count} content items{' for subject ' + subject if subject else ''}")
            
            # If we get exactly 1000 items, there might be more
            if total_count == 1000:
                print("Note: Retrieved maximum of 1000 items, total count may be higher")
        except Exception as count_error:
            print(f"Error getting total count: {count_error}")
            total_count = 0
        
        # Retrieve content items for detailed analysis
        results = await search_service.search_documents(
            index_name=index_name,
            query="*",
            filter=filter_expression,
            top=count,
            select="id,title,subject,content_type,difficulty_level,grade_level,topics,url,duration_minutes,keywords,source"
        )
        
        if not results:
            print("No content items found in the index.")
            return
        
        # Analyze content items
        content_types = Counter()
        subjects = Counter()
        difficulty_levels = Counter()
        grade_levels = defaultdict(int)
        sources = Counter()
        has_url_count = 0
        has_topics_count = 0
        has_keywords_count = 0
        
        # Process each item
        for item in results:
            # Count content types
            if "content_type" in item and item["content_type"]:
                content_types[item["content_type"]] += 1
                
            # Count subjects
            if "subject" in item and item["subject"]:
                subjects[item["subject"]] += 1
                
            # Count difficulty levels
            if "difficulty_level" in item and item["difficulty_level"]:
                difficulty_levels[item["difficulty_level"]] += 1
                
            # Count grade levels
            if "grade_level" in item and item["grade_level"]:
                if isinstance(item["grade_level"], list):
                    for grade in item["grade_level"]:
                        grade_levels[grade] += 1
                else:
                    grade_levels[item["grade_level"]] += 1
                    
            # Count sources
            if "source" in item and item["source"]:
                sources[item["source"]] += 1
                
            # Count items with URL, topics, keywords
            if "url" in item and item["url"]:
                has_url_count += 1
                
            if "topics" in item and item["topics"]:
                has_topics_count += 1
                
            if "keywords" in item and item["keywords"]:
                has_keywords_count += 1
        
        # Display statistics
        print("\n=== Content Statistics ===\n")
        print(f"Analyzed {len(results)} of {total_count} items")
        
        # Content Types
        print("\nContent Types:")
        content_type_table = [[ctype, count, f"{count/len(results):.1%}"] 
                             for ctype, count in content_types.most_common()]
        print(tabulate(content_type_table, headers=["Content Type", "Count", "Percentage"]))
        
        # Subjects
        print("\nSubjects:")
        subject_table = [[subj, count, f"{count/len(results):.1%}"] 
                        for subj, count in subjects.most_common()]
        print(tabulate(subject_table, headers=["Subject", "Count", "Percentage"]))
        
        # Difficulty Levels
        print("\nDifficulty Levels:")
        difficulty_table = [[level, count, f"{count/len(results):.1%}"] 
                           for level, count in difficulty_levels.most_common()]
        print(tabulate(difficulty_table, headers=["Difficulty Level", "Count", "Percentage"]))
        
        # Grade Levels
        print("\nGrade Levels:")
        grade_table = [[grade, count, f"{count/len(results):.1%}"] 
                      for grade, count in sorted(grade_levels.items())]
        print(tabulate(grade_table, headers=["Grade Level", "Count", "Percentage"]))
        
        # Sources
        print("\nTop 10 Sources:")
        source_table = [[source, count, f"{count/len(results):.1%}"] 
                       for source, count in sources.most_common(10)]
        print(tabulate(source_table, headers=["Source", "Count", "Percentage"]))
        
        # Completeness statistics
        print("\nCompleteness Statistics:")
        completeness_table = [
            ["Has URL", has_url_count, f"{has_url_count/len(results):.1%}"],
            ["Has Topics", has_topics_count, f"{has_topics_count/len(results):.1%}"],
            ["Has Keywords", has_keywords_count, f"{has_keywords_count/len(results):.1%}"]
        ]
        print(tabulate(completeness_table, headers=["Field", "Count", "Percentage"]))
        
        # Display sample items if requested
        if show_samples:
            print("\n=== Sample Content Items ===\n")
            for i, item in enumerate(results[:5]):  # Show up to 5 samples
                print(f"Item {i+1}:")
                # Format the item for display
                formatted_item = json.dumps(item, indent=2)
                print(formatted_item)
                print("-" * 80)
        
    except Exception as e:
        print(f"Error retrieving content: {e}")

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test Azure AI Search educational-content index")
    parser.add_argument("--subject", help="Filter by subject")
    parser.add_argument("--count", type=int, default=100, help="Number of items to analyze")
    parser.add_argument("--show-samples", action="store_true", help="Show sample content items")
    args = parser.parse_args()
    
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
        
        # Get and display content statistics
        await get_content_stats(
            search_service, 
            index_name, 
            subject=args.subject, 
            count=args.count,
            show_samples=args.show_samples
        )
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up any resources
        if 'search_service' in locals() and hasattr(search_service, 'close'):
            await search_service.close()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())