# backend/utils/vector_store.py
"""
This module provides a simplified API for interacting with vector stores
by directly using Azure Search API.
"""

import logging
from typing import List, Dict, Any, Optional
import asyncio
import os
import sys
import uuid
import json
import traceback
import requests

# Fix import paths for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)  # Add project root to path

# Now import using absolute imports
from backend.config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class AzureSearchVectorStore:
    """
    Vector store implementation that directly uses Azure Search API.
    Provides methods for adding, querying, and managing content.
    """
    def __init__(self):
        """Initialize the vector store wrapper."""
        pass
    
    async def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific content item by ID.
        
        Args:
            content_id: ID of the content to retrieve
            
        Returns:
            Content item or None if not found
        """
        try:
            # Use direct Azure Search API approach
            # Get Azure Search settings
            from backend.config.settings import Settings
            settings = Settings()
            
            if (settings.AZURE_SEARCH_ENDPOINT and 
                settings.AZURE_SEARCH_KEY and 
                settings.AZURE_SEARCH_INDEX_NAME):
                
                import requests
                
                # Azure Search endpoint for lookup by ID
                url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{settings.AZURE_SEARCH_INDEX_NAME}/docs('{content_id}')?api-version=2023-11-01"
                
                # Headers
                headers = {
                    "Content-Type": "application/json",
                    "api-key": settings.AZURE_SEARCH_KEY
                }
                
                # Make the request
                response = requests.get(url, headers=headers)
                
                # Check response
                if response.status_code == 200:
                    document = response.json()
                    
                    # Create result with consistent field naming
                    result = {
                        "id": content_id,
                    }
                    
                    # Copy all fields except for special handling of page_content
                    for key, value in document.items():
                        if key not in ["@odata.context"]:
                            if key == "page_content":
                                result["content"] = value
                            else:
                                result[key] = value
                    
                    logger.info(f"Successfully retrieved document by ID using direct API: {content_id}")
                    return result
                else:
                    logger.warning(f"Direct document lookup failed: {response.status_code}, {response.text}")
                    return None
            else:
                logger.error("Azure Search settings not available")
                return None
                
        except Exception as e:
            logger.error(f"Error getting content: {e}")
            return None
    
    async def vector_search(
        self, 
        query_text: str, 
        filter_expression: Optional[str] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for content using vector similarity.
        
        Args:
            query_text: Text to search for
            filter_expression: Optional filter expression
            limit: Maximum number of results to return
            
        Returns:
            List of matching content items
        """
        try:
            # Use direct Azure Search API approach
            # Get Azure Search settings
            from backend.config.settings import Settings
            settings = Settings()
            
            if (settings.AZURE_SEARCH_ENDPOINT and 
                settings.AZURE_SEARCH_KEY and 
                settings.AZURE_SEARCH_INDEX_NAME):
                
                # First get embedding for the query
                from backend.rag.openai_adapter import get_openai_adapter
                openai_client = await get_openai_adapter()
                embedding = await openai_client.create_embedding(
                    model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                    text=query_text
                )
                
                # Ensure embedding is a list of floats
                if isinstance(embedding, list):
                    vector = embedding
                elif hasattr(embedding, 'vector'):
                    vector = embedding.vector
                elif isinstance(embedding, dict) and 'vector' in embedding:
                    vector = embedding['vector']
                else:
                    logger.error(f"Couldn't parse embedding result type: {type(embedding)}")
                    # Create a placeholder embedding of right dimension (fallback)
                    vector = [0.0] * 1536
                
                import aiohttp
                import json
                
                # Azure Search endpoint for vector search
                url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{settings.AZURE_SEARCH_INDEX_NAME}/docs/search?api-version=2023-11-01"
                
                # Headers
                headers = {
                    "Content-Type": "application/json",
                    "api-key": settings.AZURE_SEARCH_KEY
                }
                
                # Prepare search payload
                search_payload = {
                    "search": "*",  # Use * to match all documents
                    "vectorQueries": [
                        {
                            "vector": vector,
                            "fields": "embedding",
                            "k": limit,
                            "kind": "vector"
                        }
                    ],
                    "top": limit
                }
                
                # Add filter if provided
                if filter_expression:
                    search_payload["filter"] = filter_expression
                    
                # Use aiohttp for async request
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, json=search_payload) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            # Convert to standard format
                            results = []
                            if "value" in result:
                                for doc in result["value"]:
                                    # Create result with consistent field naming
                                    item = {}
                                    
                                    # Copy all fields except for special handling of page_content
                                    for key, value in doc.items():
                                        if key not in ["@search.score", "@search.rerankerScore", "@search.vectorSearchScore"]:
                                            if key == "page_content":
                                                item["content"] = value
                                            else:
                                                item[key] = value
                                                
                                    results.append(item)
                            
                            logger.info(f"Vector search succeeded, found {len(results)} results")
                            return results
                        else:
                            error_text = await response.text()
                            logger.warning(f"Vector search failed: {response.status}, {error_text}")
                            return []
            else:
                logger.error("Azure Search settings not available")
                return []
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def add_content(self, content_item: Dict[str, Any]) -> bool:
        """
        Add content to the vector store.
        
        Args:
            content_item: Content item to add
            
        Returns:
            Success status
        """
        try:
            # Prepare text for embedding and search
            text = self._prepare_text_from_content(content_item)
            
            # Create a clean metadata object that complies with Azure Search schema
            metadata = {}
            
            # Process all fields from content_item, mapping as needed
            for key, value in content_item.items():
                # Skip fields that could cause conflicts with Azure Search
                if key in ["embedding", "content"]:
                    continue
                    
                # Handle nested metadata - flatten it to avoid schema issues
                if key == "metadata" and isinstance(value, dict):
                    for meta_key, meta_value in value.items():
                        # Flatten metadata fields with a prefix
                        if meta_key == "content_text":
                            metadata["metadata_content_text"] = meta_value
                        elif meta_key == "transcription":
                            metadata["metadata_transcription"] = meta_value
                        else:
                            # Other metadata fields can be added with a prefix
                            metadata[f"metadata_{meta_key}"] = meta_value
                    continue
                
                # Handle page_content specially - this will be used for the text field in Azure Search
                if key == "page_content":
                    # Skip adding to metadata as we'll use it directly
                    continue
                
                # For certain fields, make sure we're using standard naming
                if key == "content_text":
                    metadata["metadata_content_text"] = value
                    continue
                
                # Add all other fields directly to metadata
                # Skip 'content' field which causes issues with Azure Search schema
                if key != 'content':
                    metadata[key] = value
            
            # Make sure all non-scalar values are properly serialized
            for key, value in metadata.items():
                # Lists and dictionaries need to be properly formatted for Azure Search
                if isinstance(value, (list, dict)):
                    # We already handle topics and keywords elsewhere, so we can skip them
                    if key not in ["topics", "keywords", "grade_level"]:
                        metadata[key] = json.dumps(value)
            
            # Ensure we have document id
            if "id" not in metadata:
                # Generate a consistent ID if URL is available
                if "url" in metadata:
                    import hashlib
                    # Create a hash of the URL for consistent ID generation
                    url_hash = hashlib.md5(metadata["url"].encode()).hexdigest()
                    metadata["id"] = f"url-{url_hash}"
                    logger.info(f"Generated consistent ID from URL: {metadata['id']}")
                else:
                    metadata["id"] = str(uuid.uuid4())
            
            # This is the text field that Azure Search will use
            # Both field names (content and page_content) are supported in our methods
            content_text = text
            
            # Log what we're adding to help debug
            logger.info(f"Processing content for vector store: id={metadata.get('id')}, title={metadata.get('title')}")
            
            # Use direct Azure Search API approach
            # Get Azure Search settings
            from backend.config.settings import Settings
            settings = Settings()
            
            # Check if Azure Search settings are available
            if (settings.AZURE_SEARCH_ENDPOINT and 
                settings.AZURE_SEARCH_KEY and 
                settings.AZURE_SEARCH_INDEX_NAME):
                
                # Check if document with same ID already exists
                existing_document = await self.get_content(metadata.get("id"))
                if existing_document:
                    logger.info(f"Document with ID {metadata.get('id')} already exists. Using update method instead.")
                    return await self.update_content(metadata.get("id"), content_item)
                        
                import requests
                import json
                from backend.rag.openai_adapter import get_openai_adapter
                
                # Get embedding for the text
                openai_client = await get_openai_adapter()
                embedding_result = await openai_client.create_embedding(
                    model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                    text=content_text
                )
                        
                # Log embedding type for debugging
                logger.info(f"Embedding result type: {type(embedding_result)}")
                if isinstance(embedding_result, dict):
                    logger.info(f"Embedding dict keys: {list(embedding_result.keys())}")
                        
                # Ensure embedding is in the correct format for Azure Search (array of floats)
                # Check if it's already an array
                if isinstance(embedding_result, list):
                    embedding = embedding_result
                # Check if it has a 'vector' attribute (like from OpenAI response)
                elif hasattr(embedding_result, 'vector'):
                    embedding = embedding_result.vector
                # Check if it's a dict with embedding data
                elif isinstance(embedding_result, dict):
                    # For OpenAI and Azure OpenAI, different structures may be returned
                    if 'vector' in embedding_result:
                        embedding = embedding_result['vector']
                    elif 'data' in embedding_result and len(embedding_result['data']) > 0:
                        # This is the typical OpenAI API format
                        if 'embedding' in embedding_result['data'][0]:
                            embedding = embedding_result['data'][0]['embedding']
                        else:
                            logger.error(f"No embedding found in data[0]: {list(embedding_result['data'][0].keys())}")
                            embedding = [0.0] * 1536
                    else:
                        logger.error(f"No vector or data found in embedding dict: {list(embedding_result.keys())}")
                        embedding = [0.0] * 1536
                else:
                    # Log error and use a default embedding (not ideal but prevents crashes)
                    logger.error(f"Couldn't parse embedding result type: {type(embedding_result)}")
                    # Create a placeholder embedding of right dimension
                    embedding = [0.0] * 1536  # Standard OpenAI embedding size
                        
                # Create a minimal document with only the required fields
                # This matches our successful test case
                embedding_list = list(embedding)
                embedding_list = [float(x) for x in embedding_list]
                
                minimal_doc = {
                    "@search.action": "upload",
                    "id": metadata.get("id", str(uuid.uuid4())),
                    "title": metadata.get("title", "Untitled"),
                    "page_content": content_text,
                    "embedding": embedding_list
                }
                
                # Only add additional fields based on what's in the index schema
                valid_fields = [
                    "description", "content_type", "subject", "topics", 
                    "url", "source", "difficulty_level", "grade_level", 
                    "duration_minutes", "keywords", "created_at", "updated_at", 
                    "metadata_content_text", "metadata_transcription", "metadata_thumbnail_url"
                ]
                
                # Copy other metadata fields if they are in the valid fields list
                for key, value in metadata.items():
                    if key in valid_fields:
                        # Handle arrays and collection fields appropriately
                        if key in ["topics", "keywords", "grade_level"] and not isinstance(value, list):
                            if value is not None:
                                if isinstance(value, str):
                                    minimal_doc[key] = [value]
                                else:
                                    minimal_doc[key] = [value]
                        else:
                            minimal_doc[key] = value
                
                # Log document info
                logger.info(f"Document fields: {list(minimal_doc.keys())}")
                
                # Log the embedding shape for debugging
                logger.info(f"Embedding type: {type(minimal_doc['embedding'])}")
                logger.info(f"Embedding length: {len(minimal_doc['embedding']) if isinstance(minimal_doc['embedding'], list) else 'not a list'}")
                        
                # Build the request payload with a minimal document
                payload = {
                    "value": [minimal_doc]
                }
                
                # Log payload size for debugging
                logger.info(f"Payload size: {len(json.dumps(payload))} bytes")
                
                # Log a small sample of the payload for debugging
                try:
                    # Create a small sample of the payload for diagnostic purposes
                    payload_sample = payload.copy()
                    if 'value' in payload_sample and len(payload_sample['value']) > 0:
                        doc_sample = payload_sample['value'][0].copy()
                        
                        # Include only non-embedding fields in the sample
                        if 'embedding' in doc_sample:
                            doc_sample['embedding'] = f"[array of {len(doc_sample['embedding'])} floats]"
                            
                        payload_sample['value'] = [doc_sample]
                        
                        # Log the sample payload with sensitive info redacted
                        logger.info(f"Payload sample: {json.dumps(payload_sample, indent=2)[:1000]}...")
                except Exception as sample_err:
                    logger.error(f"Error creating payload sample: {sample_err}")
                        
                # Azure Search endpoint
                url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{settings.AZURE_SEARCH_INDEX_NAME}/docs/index?api-version=2023-11-01"
                
                # Headers
                headers = {
                    "Content-Type": "application/json",
                    "api-key": settings.AZURE_SEARCH_KEY
                }
                        
                # Make the request
                response = requests.post(url, headers=headers, json=payload)
                
                # Check response
                if response.status_code in [200, 201, 202, 204]:
                    logger.info(f"Document successfully added to Azure Search: {minimal_doc.get('id')}")
                    return True
                else:
                    logger.error(f"Error adding document to Azure Search: {response.status_code}, {response.text}")
                    # Log payload info for debugging without exposing entire payload
                    logger.error(f"Document ID: {minimal_doc.get('id')}")
                    logger.error(f"Document keys: {list(minimal_doc.keys())}")
                    # Parse response error if possible
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_message = error_data.get('error', {}).get('message', 'Unknown error')
                            logger.error(f"Azure Search error message: {error_message}")
                            
                            # Check for field-related errors to help troubleshoot schema issues
                            if 'property' in error_message and 'does not exist' in error_message:
                                import re
                                field_match = re.search(r"property '([^']+)'", error_message)
                                if field_match:
                                    problem_field = field_match.group(1)
                                    logger.error(f"Schema mismatch for field: {problem_field}")
                                    
                                    # Try to fix the error by removing the problematic field
                                    if problem_field in minimal_doc:
                                        logger.info(f"Removing problematic field '{problem_field}' and retrying")
                                        del minimal_doc[problem_field]
                                        
                                        # Update payload with fixed document
                                        payload = {
                                            "value": [
                                                {
                                                    "@search.action": "mergeOrUpload",
                                                    **minimal_doc
                                                }
                                            ]
                                        }
                                        
                                        # Retry the request
                                        logger.info("Retrying with fixed document")
                                        retry_response = requests.post(url, headers=headers, json=payload)
                                        
                                        if retry_response.status_code in [200, 201, 202, 204]:
                                            logger.info(f"Document successfully added to Azure Search after fixing schema issue: {minimal_doc.get('id')}")
                                            return True
                                        else:
                                            logger.error(f"Retry also failed: {retry_response.status_code}, {retry_response.text}")
                    except Exception as parse_error:
                        logger.error(f"Error parsing error response: {parse_error}")
                        
                    return False
            else:
                logger.error("Azure Search settings not available")
                return False
                
        except Exception as e:
            logger.error(f"Error adding content to vector store: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def update_content(self, content_id: str, updated_fields: Dict[str, Any]) -> bool:
        """
        Update content in the vector store by deleting and re-adding it.
        
        Args:
            content_id: ID of the content to update
            updated_fields: Fields to update
            
        Returns:
            Success status
        """
        try:
            # Get existing content
            existing = await self.get_content(content_id)
            if not existing:
                return False
                
            # Update fields
            updated_content = {**existing, **updated_fields}
            
            # Use add_content to update
            return await self.add_content(updated_content)
            
        except Exception as e:
            logger.error(f"Error updating content: {e}")
            return False
    
    async def delete_content(self, content_id: str) -> bool:
        """
        Delete content from the vector store.
        
        Args:
            content_id: ID of the content to delete
            
        Returns:
            Success status
        """
        try:
            # Use direct Azure Search API approach
            # Get Azure Search settings
            from backend.config.settings import Settings
            settings = Settings()
            
            if (settings.AZURE_SEARCH_ENDPOINT and 
                settings.AZURE_SEARCH_KEY and 
                settings.AZURE_SEARCH_INDEX_NAME):
                
                import requests
                
                # Prepare the delete payload
                payload = {
                    "value": [
                        {
                            "@search.action": "delete",
                            "id": content_id
                        }
                    ]
                }
                
                # Azure Search endpoint
                url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{settings.AZURE_SEARCH_INDEX_NAME}/docs/index?api-version=2023-11-01"
                
                # Headers
                headers = {
                    "Content-Type": "application/json",
                    "api-key": settings.AZURE_SEARCH_KEY
                }
                
                # Make the request
                response = requests.post(url, headers=headers, json=payload)
                
                # Check response
                if response.status_code in [200, 201, 202, 204]:
                    logger.info(f"Document successfully deleted from Azure Search: {content_id}")
                    return True
                else:
                    logger.error(f"Error deleting document from Azure Search: {response.status_code}, {response.text}")
                    return False
            else:
                logger.error("Azure Search settings not available")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting content: {e}")
            return False
    
    async def filter_search(
        self,
        filter_expression: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for content using filter expressions.
        
        Args:
            filter_expression: Filter expression
            limit: Maximum number of results to return
            
        Returns:
            List of matching content items
        """
        try:
            # Use direct Azure Search API approach
            # Get Azure Search settings
            from backend.config.settings import Settings
            settings = Settings()
            
            if (settings.AZURE_SEARCH_ENDPOINT and 
                settings.AZURE_SEARCH_KEY and 
                settings.AZURE_SEARCH_INDEX_NAME):
                
                import aiohttp
                import json
                
                # Azure Search endpoint
                url = f"{settings.AZURE_SEARCH_ENDPOINT}/indexes/{settings.AZURE_SEARCH_INDEX_NAME}/docs/search?api-version=2023-11-01"
                
                # Headers
                headers = {
                    "Content-Type": "application/json",
                    "api-key": settings.AZURE_SEARCH_KEY
                }
                
                # Prepare search payload
                search_payload = {
                    "search": "*",  # Match all documents
                    "filter": filter_expression,
                    "top": limit
                }
                
                # Use aiohttp for async request
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, json=search_payload) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            # Convert to standard format
                            results = []
                            if "value" in result:
                                for doc in result["value"]:
                                    # Create result with consistent field naming
                                    item = {}
                                    
                                    # Copy all fields except for special handling of page_content
                                    for key, value in doc.items():
                                        if key not in ["@search.score", "@search.rerankerScore"]:
                                            if key == "page_content":
                                                item["content"] = value
                                            else:
                                                item[key] = value
                                                
                                    results.append(item)
                            
                            logger.info(f"Filter search succeeded, found {len(results)} results")
                            return results
                        else:
                            error_text = await response.text()
                            logger.warning(f"Filter search failed: {response.status}, {error_text}")
                            return []
            else:
                logger.error("Azure Search settings not available")
                return []
                
        except Exception as e:
            logger.error(f"Error in filter search: {e}")
            return []
    
    def _prepare_text_from_content(self, content_item: Dict[str, Any]) -> str:
        """
        Extract text from content item for embedding.
        
        Args:
            content_item: Content item
            
        Returns:
            Text for embedding
        """
        # Combine relevant fields
        text_parts = []
        
        # Add title and subject
        if "title" in content_item:
            text_parts.append(f"Title: {content_item['title']}")
        if "subject" in content_item:
            text_parts.append(f"Subject: {content_item['subject']}")
            
        # Add content type if available (helps for search)
        if "content_type" in content_item:
            text_parts.append(f"Content Type: {content_item['content_type']}")
        
        # Add difficulty level if available
        if "difficulty_level" in content_item:
            text_parts.append(f"Difficulty: {content_item['difficulty_level']}")
            
        # Add description
        if "description" in content_item:
            text_parts.append(f"Description: {content_item['description']}")
            
        # Add topics if available
        if "topics" in content_item and content_item["topics"]:
            if isinstance(content_item["topics"], list):
                topics_text = ", ".join(content_item["topics"])
            else:
                topics_text = str(content_item["topics"])
            text_parts.append(f"Topics: {topics_text}")
        
        # Add keywords if available
        if "keywords" in content_item and content_item["keywords"]:
            if isinstance(content_item["keywords"], list):
                keywords_text = ", ".join(content_item["keywords"])
            else:
                keywords_text = str(content_item["keywords"])
            text_parts.append(f"Keywords: {keywords_text}")
            
        # Add content from either page_content or content fields
        # Try page_content first (langchain format)
        if "page_content" in content_item:
            text_parts.append(f"Content: {content_item['page_content']}")
        # Then try content (Azure Search format)
        elif "content" in content_item:
            text_parts.append(f"Content: {content_item['content']}")
            
        # Check metadata
        if "metadata" in content_item:
            metadata = content_item["metadata"]
            
            # Add content text from metadata if available
            if "content_text" in metadata:
                text_parts.append(f"Content: {metadata['content_text']}")
                
            # Add transcription if available (for videos/audio)
            if "transcription" in metadata:
                text_parts.append(f"Transcription: {metadata['transcription']}")
                
            # Add video-specific information
            if "video_url" in metadata:
                text_parts.append(f"Video URL: {metadata['video_url']}")
                
            if "video_platform" in metadata:
                text_parts.append(f"Video Platform: {metadata['video_platform']}")
                
        # Also check flattened metadata fields - these are more Azure Search friendly
        if "metadata_content_text" in content_item:
            text_parts.append(f"Content: {content_item['metadata_content_text']}")
            
        if "metadata_transcription" in content_item:
            text_parts.append(f"Transcription: {content_item['metadata_transcription']}")
            
        # Join all parts
        return "\n\n".join(text_parts)

# Singleton instance
vector_store = None

async def get_vector_store():
    """Get or create vector store singleton."""
    global vector_store
    if vector_store is None:
        vector_store = AzureSearchVectorStore()
    return vector_store