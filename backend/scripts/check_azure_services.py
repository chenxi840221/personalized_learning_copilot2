#!/usr/bin/env python3
"""
Script to check Azure services configuration.
Verifies connection to Azure AI Search, Azure OpenAI, Azure Form Recognizer, etc.
"""

import os
import sys
import logging
import json
import asyncio
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Add backend directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)
sys.path.insert(0, project_root)

# Import settings
from config.settings import Settings
settings = Settings()

# Import services
from services.search_service import get_search_service
from rag.openai_adapter import get_openai_adapter

async def check_ai_search():
    """Check Azure AI Search configuration and connectivity."""
    logger.info("=== Checking Azure AI Search ===")
    
    if not settings.AZURE_SEARCH_ENDPOINT or not settings.AZURE_SEARCH_KEY:
        logger.error("❌ Missing Azure AI Search configuration")
        logger.info(f"AZURE_SEARCH_ENDPOINT: {'Set' if settings.AZURE_SEARCH_ENDPOINT else 'Missing'}")
        logger.info(f"AZURE_SEARCH_KEY: {'Set' if settings.AZURE_SEARCH_KEY else 'Missing'}")
        return False
    
    try:
        # Initialize search service
        logger.info("Initializing search service...")
        search_service = await get_search_service()
        
        if not search_service:
            logger.error("❌ Failed to initialize search service")
            return False
        
        # Check indexes
        logger.info("Checking indexes...")
        indexes_to_check = [
            "student-reports",
            "student-profiles",
            "educational-content",
            "user-profiles",
            "learning-plans"
        ]
        
        for index_name in indexes_to_check:
            exists = await search_service.check_index_exists(index_name)
            status = "✅ Exists" if exists else "❌ Missing"
            logger.info(f"Index '{index_name}': {status}")
        
        logger.info("✅ Azure AI Search checks completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking Azure AI Search: {e}")
        return False

async def check_openai():
    """Check Azure OpenAI configuration and connectivity."""
    logger.info("=== Checking Azure OpenAI ===")
    
    if not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_KEY:
        logger.error("❌ Missing Azure OpenAI configuration")
        logger.info(f"AZURE_OPENAI_ENDPOINT: {'Set' if settings.AZURE_OPENAI_ENDPOINT else 'Missing'}")
        logger.info(f"AZURE_OPENAI_KEY: {'Set' if settings.AZURE_OPENAI_KEY else 'Missing'}")
        return False
    
    try:
        # Initialize OpenAI adapter
        logger.info("Initializing OpenAI adapter...")
        openai_adapter = await get_openai_adapter()
        
        if not openai_adapter:
            logger.error("❌ Failed to initialize OpenAI adapter")
            return False
        
        # Test completions
        logger.info("Testing text completions...")
        prompt = "Hello, how are you?"
        
        try:
            response = await openai_adapter.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=settings.AZURE_OPENAI_DEPLOYMENT
            )
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"✅ Completion test successful. First 50 chars: {content[:50]}...")
        except Exception as comp_err:
            logger.error(f"❌ Completion test failed: {comp_err}")
        
        # Test embeddings
        logger.info("Testing embeddings...")
        try:
            embedding = await openai_adapter.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text="Test embedding"
            )
            if embedding and len(embedding) > 0:
                logger.info(f"✅ Embedding test successful. Vector length: {len(embedding)}")
            else:
                logger.error("❌ Embedding test failed: Empty embedding")
        except Exception as emb_err:
            logger.error(f"❌ Embedding test failed: {emb_err}")
        
        logger.info("✅ Azure OpenAI checks completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking Azure OpenAI: {e}")
        return False

async def check_services():
    """Check all Azure services."""
    logger.info("Checking Azure services configuration...")
    
    # Print environment information
    logger.info("Environment:")
    logger.info(f"AZURE_SEARCH_ENDPOINT: {settings.AZURE_SEARCH_ENDPOINT}")
    logger.info(f"AZURE_SEARCH_KEY: {'Set' if settings.AZURE_SEARCH_KEY else 'Missing'}")
    logger.info(f"AZURE_SEARCH_REPORTS_INDEX: {settings.REPORTS_INDEX_NAME}")
    logger.info(f"AZURE_OPENAI_ENDPOINT: {settings.AZURE_OPENAI_ENDPOINT}")
    logger.info(f"AZURE_OPENAI_KEY: {'Set' if settings.AZURE_OPENAI_KEY else 'Missing'}")
    logger.info(f"AZURE_OPENAI_DEPLOYMENT: {settings.AZURE_OPENAI_DEPLOYMENT}")
    logger.info(f"AZURE_OPENAI_EMBEDDING_DEPLOYMENT: {settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT}")
    logger.info(f"FORM_RECOGNIZER_ENDPOINT: {settings.FORM_RECOGNIZER_ENDPOINT}")
    logger.info(f"FORM_RECOGNIZER_KEY: {'Set' if settings.FORM_RECOGNIZER_KEY else 'Missing'}")
    logger.info(f"ENCRYPTION_KEY: {'Set' if settings.ENCRYPTION_KEY else 'Missing'}")
    
    # Check services
    await check_ai_search()
    await check_openai()
    
    logger.info("All service checks completed")

if __name__ == "__main__":
    asyncio.run(check_services())