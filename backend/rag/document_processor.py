import logging
import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re
from datetime import datetime
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from models.content import Content
from config.settings import Settings
from rag.openai_adapter import get_openai_adapter

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Process documents for search indexing, including content extraction
    and embedding generation. Works with Cognitive Services Multi-Service Resource.
    """
    def __init__(self):
        # Initialize OpenAI client when needed
        self.openai_client = None
        
        # Initialize Form Recognizer client from Cognitive Services Multi-Service Resource
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=settings.FORM_RECOGNIZER_ENDPOINT,
            credential=AzureKeyCredential(settings.FORM_RECOGNIZER_KEY)
        ) if settings.FORM_RECOGNIZER_ENDPOINT and settings.FORM_RECOGNIZER_KEY else None
    
    async def process_content(self, content: Content) -> Dict[str, Any]:
        """
        Process a content item for indexing with embedding.
        Args:
            content: Content item to process
        Returns:
            Content item with embedding
        """
        try:
            # Prepare text for embedding
            text = self._prepare_text_for_embedding(content)
            
            # Generate embedding
            if not self.openai_client:
                self.openai_client = await get_openai_adapter()
                
            embedding = await self.openai_client.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=text
            )
            
            # Create document for indexing
            content_dict = content.dict()
            content_dict["embedding"] = embedding
            
            return content_dict
            
        except Exception as e:
            logger.error(f"Error processing content {content.id}: {e}")
            raise
    
    def _prepare_text_for_embedding(self, content: Content) -> str:
        """
        Prepare content text for embedding by combining relevant fields.
        Args:
            content: Content item
        Returns:
            Processed text ready for embedding
        """
        # Combine relevant fields
        text_parts = [
            f"Title: {content.title}",
            f"Subject: {content.subject}",
            f"Topics: {', '.join(content.topics)}",
            f"Description: {content.description}",
            f"Content Type: {content.content_type}",
            f"Difficulty Level: {content.difficulty_level}",
            f"Grade Level: {'-'.join(map(str, content.grade_level))}"
        ]
        
        # Add keywords if available
        if content.keywords:
            text_parts.append(f"Keywords: {', '.join(content.keywords)}")
            
        return "\n".join(text_parts)
    
    async def extract_content_from_document(self, document_url: str) -> Dict[str, Any]:
        """
        Extract content from a document URL using Form Recognizer.
        Args:
            document_url: URL to the document
        Returns:
            Extracted content and metadata
        """
        if not self.document_analysis_client:
            raise ValueError("Document Analysis client not initialized. Check Form Recognizer credentials.")
            
        try:
            # Start the document analysis
            poller = await self.document_analysis_client.begin_analyze_document_from_url(
                "prebuilt-document", document_url
            )
            result = await poller.result()
            
            # Extract content
            content = result.content
            
            # Extract key data
            paragraphs = []
            for paragraph in result.paragraphs:
                paragraphs.append(paragraph.content)
                
            # Extract tables
            tables = []
            for table in result.tables:
                rows = []
                for cell in table.cells:
                    rows.append({
                        "row_index": cell.row_index,
                        "column_index": cell.column_index,
                        "content": cell.content,
                        "row_span": cell.row_span,
                        "column_span": cell.column_span
                    })
                tables.append(rows)
                
            # Extract key-value pairs
            key_values = {}
            for kv in result.key_value_pairs:
                if kv.key and kv.value:
                    key_values[kv.key.content] = kv.value.content
                    
            return {
                "content": content,
                "paragraphs": paragraphs,
                "tables": tables,
                "key_values": key_values
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from document {document_url}: {e}")
            raise
    
    def _extract_text_from_html(self, html: str) -> str:
        """
        Extract clean text from HTML content.
        Args:
            html: HTML content
        Returns:
            Extracted text
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
            
        # Get text
        text = soup.get_text(separator="\n")
        
        # Clean the text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)
        
        return text

# Singleton instance
document_processor = None

async def get_document_processor():
    """Get or create the document processor singleton."""
    global document_processor
    if document_processor is None:
        document_processor = DocumentProcessor()
    return document_processor

async def process_all_content():
    """Process all content items in the database and add embeddings."""
    processor = await get_document_processor()
    db = None  # This would be your database connector
    
    # Get all content
    contents = await db.contents.find().to_list(length=1000)
    processed_count = 0
    error_count = 0
    
    for content_dict in contents:
        try:
            # Skip if already has embedding
            if "embedding" in content_dict and content_dict["embedding"]:
                continue
                
            # Convert to Content model
            content = Content(**content_dict)
            
            # Process content
            processed_content = await processor.process_content(content)
            
            # Update in database
            await db.contents.update_one(
                {"id": content.id},
                {"$set": {"embedding": processed_content["embedding"]}}
            )
            
            processed_count += 1
            logger.info(f"Processed content: {content.title}")
            
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing content: {e}")
            
    logger.info(f"Completed processing. Processed: {processed_count}, Errors: {error_count}")
    return processed_count, error_count

async def analyze_document(document_url: str) -> Dict[str, Any]:
    """
    Analyze a document and extract content, structure, and metadata.
    Args:
        document_url: URL to the document
    Returns:
        Extracted content and metadata
    """
    processor = await get_document_processor()
    
    # Extract content from document
    extracted_content = await processor.extract_content_from_document(document_url)
    
    # Generate embedding for the content
    text_to_embed = extracted_content["content"]
    if not processor.openai_client:
        processor.openai_client = await get_openai_adapter()
        
    embedding = await processor.openai_client.create_embedding(
        model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        text=text_to_embed
    )
    
    # Add embedding to the result
    extracted_content["embedding"] = embedding
    extracted_content["key_phrases"] = []  # This would be populated by Text Analytics in a full implementation
    
    return extracted_content