#!/usr/bin/env python3
import os
import sys
import json
import logging
import argparse
import asyncio
from datetime import datetime

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from config.settings import settings

# Initialize logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def search_content(query=None, filter_string=None, limit=10, show_captions=False, content_id=None):
    """
    Search for content in the Azure Search index.
    
    Args:
        query: Search query
        filter_string: Filter string
        limit: Maximum number of results to return
        show_captions: Whether to include captions field in results
        content_id: Specific content ID to retrieve
        
    Returns:
        Search results
    """
    try:
        import aiohttp
        
        # Get Azure Search settings
        endpoint = settings.AZURE_SEARCH_ENDPOINT
        key = settings.AZURE_SEARCH_KEY
        index_name = settings.CONTENT_INDEX_NAME
        
        if not endpoint or not key or not index_name:
            logger.error("Azure Search settings not configured")
            return None
            
        # If retrieving by ID, use a different approach
        if content_id:
            # Document lookup URL
            url = f"{endpoint}/indexes/{index_name}/docs/{content_id}?api-version=2023-11-01"
            
            headers = {
                "Content-Type": "application/json",
                "api-key": key
            }
            
            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Found document with ID: {content_id}")
                        return {"value": [result]}
                    else:
                        logger.error(f"Error retrieving document: {response.status}")
                        error_text = await response.text()
                        logger.error(f"Error response: {error_text}")
                        return None
        
        # Otherwise do a search    
        # Prepare search request
        url = f"{endpoint}/indexes/{index_name}/docs/search?api-version=2023-11-01"
        
        headers = {
            "Content-Type": "application/json",
            "api-key": key
        }
        
        # Determine fields to select - it seems captions is not in the schema, so we need to select all fields
        select_fields = "*"
        
        # Create search body
        search_body = {
            "search": query if query else "*",
            "top": limit,
            "select": select_fields,
        }
        
        # Add filter if provided
        if filter_string:
            search_body["filter"] = filter_string
        
        # Make request
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=search_body) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Found {len(result.get('value', []))} results")
                    return result
                else:
                    logger.error(f"Error searching Azure Search: {response.status}")
                    error_text = await response.text()
                    logger.error(f"Error response: {error_text}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error searching Azure Search: {e}")
        return None
        
def display_document(doc):
    """Display document details in a structured format."""
    print("\n" + "="*50)
    print(f"ID: {doc.get('id')}")
    print(f"Title: {doc.get('title')}")
    print(f"Content Type: {doc.get('content_type')}")
    print(f"Subject: {doc.get('subject')}")
    print(f"URL: {doc.get('url')}")
    
    # Show transcription if available
    if "metadata_transcription" in doc and doc.get("metadata_transcription"):
        trans = doc.get("metadata_transcription")
        print("\nTRANSCRIPTION:")
        print("-" * 50)
        if len(trans) > 500:
            print(f"{trans[:500]}...[truncated]")
        else:
            print(trans)
            
    # Show captions if available
    if "captions" in doc and doc.get("captions"):
        captions = doc.get("captions")
        print("\nCAPTION SEGMENTS:")
        print("-" * 50)
        
        for i, cap in enumerate(captions[:5]):
            start = cap.get("start_time", 0)
            end = cap.get("end_time", 0)
            text = cap.get("text", "")
            print(f"[{start:.1f}s - {end:.1f}s] {text}")
            
        if len(captions) > 5:
            print(f"...and {len(captions) - 5} more segments")
        
    print("="*50)
        
async def main():
    parser = argparse.ArgumentParser(description="Search for video content with captions in Azure Search")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--filter", help="Filter string")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of results")
    parser.add_argument("--content-type", help="Filter by content type (e.g., video)")
    parser.add_argument("--id", help="Get document by ID")
    parser.add_argument("--full", action="store_true", help="Show full document details including captions")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    
    args = parser.parse_args()
    
    # Build filter string if content type is specified
    filter_string = args.filter
    if args.content_type:
        content_type_filter = f"content_type eq '{args.content_type}'"
        if filter_string:
            filter_string = f"{filter_string} and {content_type_filter}"
        else:
            filter_string = content_type_filter
    
    # Search for content
    results = await search_content(
        args.query, 
        filter_string, 
        args.limit, 
        show_captions=args.full,
        content_id=args.id
    )
    
    if results:
        if args.json:
            # Print raw JSON
            print(json.dumps(results, indent=2))
        else:
            # Print formatted results
            print(f"\nFound {len(results.get('value', []))} results:")
            
            for i, doc in enumerate(results.get("value", [])):
                display_document(doc)
                
                if i < len(results.get("value", [])) - 1:
                    print("\n")  # Add space between results
        
if __name__ == "__main__":
    asyncio.run(main())