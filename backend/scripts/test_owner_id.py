#!/usr/bin/env python
# backend/scripts/test_owner_id.py
import asyncio
import logging
import sys
import os
import json
import uuid
from datetime import datetime

# Add backend directory to Python path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
sys.path.insert(0, backend_dir)

from config.settings import Settings
from services.search_service import get_search_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_report_with_owner_id():
    """Test creating a student report with owner_id in the Azure Search index."""
    # Load settings
    settings = Settings()
    
    # Get search service
    search_service = await get_search_service()
    
    # Check if search service is available
    if not search_service:
        logger.error("Search service not available")
        return False
        
    # Generate test data
    report_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())
    
    # Create a sample report document
    report = {
        "id": report_id,
        "student_id": str(uuid.uuid4()),
        "student_name": "Test Student",
        "report_type": "PRIMARY",
        "school_name": "Test School",
        "school_year": "2024",
        "term": "S1",
        "grade_level": 5,
        "teacher_name": "Test Teacher",
        "general_comments": "This is a test report",
        "subjects": [
            {
                "name": "Math",
                "grade": "A",
                "comments": "Excellent work",
                "achievement_level": "Above average",
                "areas_for_improvement": ["Word problems"],
                "strengths": ["Calculation"]
            }
        ],
        "raw_extracted_text": "Sample text for report",
        "document_url": "http://example.com/test.pdf",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "owner_id": owner_id,
        "additional_fields": {
            "teacher_name": "Test Teacher",
            "general_comments": "This is a test report"
        }
    }
    
    # Try to index the document
    logger.info(f"Attempting to index report with ID {report_id} and owner_id {owner_id}")
    success = await search_service.index_document(
        index_name=settings.REPORTS_INDEX_NAME,
        document=report
    )
    
    if success:
        logger.info(f"Successfully indexed report with owner_id")
        
        # Wait a bit for Azure Search to process the document
        import time
        logger.info("Waiting 5 seconds for Azure Search to process the document...")
        time.sleep(5)
        
        # First try to retrieve all documents to check what's in the index
        logger.info("Retrieving all documents from the index")
        all_results = await search_service.search_documents(
            index_name=settings.REPORTS_INDEX_NAME,
            query="*"
        )
        
        logger.info(f"Found {len(all_results)} total documents in the index")
        for i, doc in enumerate(all_results):
            logger.info(f"Document {i+1}: ID={doc.get('id')}, owner_id={doc.get('owner_id')}")
        
        # Try to retrieve the document by owner_id
        logger.info(f"Attempting to retrieve report by owner_id {owner_id}")
        results = await search_service.search_documents(
            index_name=settings.REPORTS_INDEX_NAME,
            query="*",
            filter=f"owner_id eq '{owner_id}'"
        )
        
        if results and len(results) > 0:
            logger.info(f"Successfully retrieved {len(results)} reports with owner_id {owner_id}")
            
            # Verify the document contains the expected owner_id
            retrieved_owner_id = results[0].get("owner_id")
            if retrieved_owner_id == owner_id:
                logger.info(f"Retrieved document has correct owner_id: {retrieved_owner_id}")
                
                # Now try to clean up
                logger.info(f"Cleaning up test document with ID {report_id}")
                deleted = await search_service.delete_document(
                    index_name=settings.REPORTS_INDEX_NAME,
                    document_id=report_id
                )
                
                if deleted:
                    logger.info("Successfully deleted test document")
                else:
                    logger.warning("Failed to delete test document")
                
                return True
            else:
                logger.error(f"Retrieved document has unexpected owner_id: {retrieved_owner_id}")
                return False
        else:
            logger.error(f"Failed to retrieve report by owner_id {owner_id}")
            return False
    else:
        logger.error("Failed to index report with owner_id")
        return False

async def main():
    """Main function to run the test."""
    result = await test_report_with_owner_id()
    
    if result:
        logger.info("TEST PASSED: Successfully created and retrieved a report with owner_id")
    else:
        logger.error("TEST FAILED: Could not create or retrieve a report with owner_id")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())