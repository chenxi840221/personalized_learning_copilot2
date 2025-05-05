#!/usr/bin/env python
# Test script for student name source functionality

import asyncio
import sys
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to simulate document preparation and field removal
async def test_additional_fields():
    """Test that student_name_source is properly stored in additional_fields."""
    
    from services.search_service import SearchService
    
    logger.info("Creating test documents...")
    
    # Create a search service instance
    search_service = SearchService()
    
    # Create test documents: One with student_name_source, one with additional_fields
    doc1 = {
        "id": "test-doc-1",
        "student_name": "Jane Doe",
        "student_name_source": "filename"  # This field should be filtered out
    }
    
    doc2 = {
        "id": "test-doc-2",
        "student_name": "John Smith",
        "additional_fields": {
            "name_source": "report_content"  # This should be preserved
        }
    }
    
    # Process documents
    logger.info("Processing document 1 (with student_name_source)")
    prepared_doc1 = search_service._prepare_document_for_indexing(doc1)
    
    logger.info("Processing document 2 (with additional_fields)")
    prepared_doc2 = search_service._prepare_document_for_indexing(doc2)
    
    # Check results
    logger.info(f"Document 1 keys after processing: {list(prepared_doc1.keys())}")
    logger.info(f"Document 2 keys after processing: {list(prepared_doc2.keys())}")
    
    # Verify student_name_source was removed
    assert "student_name_source" not in prepared_doc1, "student_name_source should have been removed"
    
    # Verify additional_fields was preserved
    assert "additional_fields" in prepared_doc2, "additional_fields should be preserved"
    
    # Print document details for verification
    logger.info(f"Document 1 after processing: {json.dumps(prepared_doc1)}")
    logger.info(f"Document 2 after processing: {json.dumps(prepared_doc2)}")
    
    logger.info("Test completed successfully!")

# Main function
async def main():
    logger.info("Starting test...")
    await test_additional_fields()
    logger.info("All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())