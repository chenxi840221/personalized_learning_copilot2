#!/usr/bin/env python3
# backend/scrapers/two_step_scraper.py
import asyncio
import argparse
import logging
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Add the project root to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, project_root)  # Add project root first

# Now we can properly import from the backend package
from backend.utils.vector_store import get_vector_store
from backend.config.settings import Settings
from backend.rag.openai_adapter import get_openai_adapter
from backend.scrapers.edu_resource_indexer import run_indexer
from backend.scrapers.content_extractor import run_extractor

# Now for LangChain imports - always use the community imports
try:
    from langchain_community.document_loaders import WebBaseLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.embeddings import AzureOpenAIEmbeddings
    from langchain_community.vectorstores import AzureSearch
except ImportError:
    print("Warning: LangChain imports failed. Make sure to install required packages.")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('two_step_scraper.log')
    ]
)

logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()

class EnhancedScraperManager:
    """Enhanced scraper with Azure OpenAI and Azure Search integration."""
    
    def __init__(self):
        self.openai_client = None
        self.azure_embeddings = None
        self.azure_search = None
        self.vector_store = None
        
    async def initialize(self):
        """Initialize Azure OpenAI and Azure Search clients."""
        try:
            # Initialize Azure OpenAI client
            self.openai_client = await get_openai_adapter()
            
            # Initialize Azure OpenAI Embeddings for LangChain
            self.azure_embeddings = AzureOpenAIEmbeddings(
                azure_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_KEY
            )
            
            # Initialize Azure Search vector store
            self.vector_store = await get_vector_store()
            
            # Initialize Azure Search for LangChain if needed
            if (settings.AZURE_SEARCH_ENDPOINT and 
                settings.AZURE_SEARCH_KEY and 
                settings.AZURE_SEARCH_INDEX_NAME):
                
                self.azure_search = AzureSearch(
                    azure_search_endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    azure_search_key=settings.AZURE_SEARCH_KEY,
                    index_name=settings.AZURE_SEARCH_INDEX_NAME,
                    embedding_function=self.azure_embeddings.embed_query,
                    vector_field_name="embedding",
                    text_field_name="page_content",  # Use page_content instead of content
                    fields_mapping={
                        "content": "page_content",  # Map legacy 'content' field to 'page_content'
                        "content_text": "metadata_content_text"  # Map content text to metadata field
                    }
                )
            
            logger.info("Azure OpenAI and Azure Search clients initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing Azure clients: {e}")
            return False
    
    async def process_content(self, url: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process content with LangChain and Azure services.
        
        Args:
            url: URL of the content to process
            metadata: Metadata about the content
            
        Returns:
            Processed content with embeddings
        """
        try:
            # Load content with LangChain
            loader = WebBaseLoader(url)
            documents = await asyncio.to_thread(loader.load)
            
            if not documents:
                logger.warning(f"No content loaded from {url}")
                return metadata
            
            # Split text into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100
            )
            chunks = await asyncio.to_thread(text_splitter.split_documents, documents)
            
            # Combine all text content
            full_text = "\n\n".join([doc.page_content for doc in chunks])
            
            # Update metadata
            content_info = metadata.copy()
            
            # Add full text to metadata
            if "metadata" not in content_info:
                content_info["metadata"] = {}
            content_info["metadata"]["content_text"] = full_text[:10000]  # Limit size
            
            # Also add flattened metadata fields for Azure Search
            content_info["metadata_content_text"] = full_text[:10000]
            
            # Add page_content field for LangChain compatibility
            content_info["page_content"] = full_text[:10000]
            
            # Determine content type, difficulty level, etc. using extracted text
            content_type, difficulty, grade_levels = await self.extract_content_properties(
                content_info.get("title", ""), 
                full_text[:2000]  # Use first 2000 chars for analysis
            )
            
            # Update content properties
            content_info["content_type"] = content_type
            content_info["difficulty_level"] = difficulty
            content_info["grade_level"] = grade_levels
            
            # Generate embedding
            embedding_text = self.prepare_text_for_embedding(content_info, full_text)
            embedding = await self.openai_client.create_embedding(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                text=embedding_text
            )
            
            # Add embedding to content
            content_info["embedding"] = embedding
            
            # Add content_id if not present
            if "id" not in content_info:
                import uuid
                content_info["id"] = str(uuid.uuid4())
                
            # Add timestamps if not present
            current_time = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
            if "created_at" not in content_info:
                content_info["created_at"] = current_time
            if "updated_at" not in content_info:
                content_info["updated_at"] = current_time
            
            # Add to Azure Search if available
            if self.vector_store:
                await self.vector_store.add_content(content_info)
                logger.info(f"Successfully indexed content: {content_info.get('title', 'Untitled')}")
            
            return content_info
            
        except Exception as e:
            logger.error(f"Error processing content {url}: {e}")
            return metadata
    
    async def extract_content_properties(self, title: str, text_sample: str) -> Tuple[str, str, List[int]]:
        """
        Extract content properties using Azure OpenAI.
        
        Args:
            title: The content title
            text_sample: Sample of the content text
            
        Returns:
            Tuple of (content_type, difficulty_level, grade_levels)
        """
        try:
            system_message = "You are an educational content analyzer. Extract relevant properties from content."
            
            prompt = f"""
            Analyze this educational content and determine:
            1. The content type (article, video, interactive, quiz, worksheet, lesson, activity)
            2. The difficulty level (beginner, intermediate, advanced)
            3. The appropriate grade levels (numbers from 1-12)
            
            Title: {title}
            
            Content sample: 
            {text_sample[:1000]}
            
            Return only a JSON object with these three properties:
            {{
                "content_type": "one of [article, video, interactive, quiz, worksheet, lesson, activity]",
                "difficulty_level": "one of [beginner, intermediate, advanced]",
                "grade_levels": [array of numbers between 1-12]
            }}
            """
            
            # Get response from Azure OpenAI
            response = await self.openai_client.create_chat_completion(
                model=settings.AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse the JSON response
            response_text = response["choices"][0]["message"]["content"]
            
            try:
                result = json.loads(response_text)
                
                # Extract and validate the properties
                content_type = result.get("content_type", "article")
                difficulty_level = result.get("difficulty_level", "intermediate")
                grade_levels = result.get("grade_levels", [6, 7, 8])
                
                # Validate content_type
                valid_content_types = ["article", "video", "interactive", "quiz", "worksheet", "lesson", "activity"]
                if content_type not in valid_content_types:
                    logger.warning(f"Invalid content_type: {content_type}, defaulting to 'article'")
                    content_type = "article"
                
                # Validate difficulty_level
                valid_difficulty_levels = ["beginner", "intermediate", "advanced"]
                if difficulty_level not in valid_difficulty_levels:
                    logger.warning(f"Invalid difficulty_level: {difficulty_level}, defaulting to 'intermediate'")
                    difficulty_level = "intermediate"
                
                # Ensure grade_levels is a list of integers
                if not isinstance(grade_levels, list):
                    if isinstance(grade_levels, int):
                        grade_levels = [grade_levels]
                    else:
                        grade_levels = [6, 7, 8]  # Default
                
                # Filter grade levels to valid range
                grade_levels = [g for g in grade_levels if isinstance(g, int) and 1 <= g <= 12]
                if not grade_levels:
                    grade_levels = [6, 7, 8]  # Default if no valid grades
                
                return content_type, difficulty_level, grade_levels
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {response_text}")
                return "article", "intermediate", [6, 7, 8]  # Default values
            
        except Exception as e:
            logger.error(f"Error extracting content properties: {e}")
            return "article", "intermediate", [6, 7, 8]  # Default values
    
    def prepare_text_for_embedding(self, content_info: Dict[str, Any], full_text: str) -> str:
        """Prepare text for embedding by combining metadata with content."""
        # Combine relevant fields
        text_parts = [
            f"Title: {content_info.get('title', 'Untitled')}",
            f"Subject: {content_info.get('subject', 'General')}",
        ]
        
        # Add description if available
        if content_info.get('description'):
            text_parts.append(f"Description: {content_info['description']}")
            
        # Add topics if available
        if content_info.get('topics'):
            topics_text = ', '.join(content_info['topics']) if isinstance(content_info['topics'], list) else content_info['topics']
            text_parts.append(f"Topics: {topics_text}")
        
        # Add content text (truncated)
        if full_text:
            if len(full_text) > 4000:  # Limit text size for embedding
                text_parts.append(f"Content: {full_text[:4000]}...")
            else:
                text_parts.append(f"Content: {full_text}")
        
        # Join all parts with newlines
        return "\n".join(text_parts)
    
    async def batch_process_resources(self, resources: List[Dict[str, Any]], batch_size: int = 5) -> List[Dict[str, Any]]:
        """Process multiple resources in batches."""
        processed_resources = []
        
        # Process in batches to avoid overwhelming services
        for i in range(0, len(resources), batch_size):
            batch = resources[i:i+batch_size]
            
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} resources)")
            
            # Process each resource in the batch
            batch_tasks = [self.process_content(resource["url"], resource) for resource in batch]
            results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Add successful results to the list
            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing resource: {result}")
                else:
                    processed_resources.append(result)
            
            # Add a small delay between batches
            await asyncio.sleep(2)
        
        return processed_resources

async def enhance_extraction(extracted_resources: List[Dict[str, Any]], subject_limit: Optional[int] = None, 
                          resource_limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Enhance the extraction step with Azure OpenAI and Azure Search integration.
    
    Args:
        extracted_resources: Resources extracted from the indexing step
        subject_limit: Maximum number of subjects to process
        resource_limit: Maximum number of resources per subject
        
    Returns:
        Dictionary with enhanced extraction results
    """
    logger.info("Starting enhanced extraction with Azure services")
    
    # Initialize the enhanced scraper
    enhancer = EnhancedScraperManager()
    success = await enhancer.initialize()
    
    if not success:
        logger.error("Failed to initialize Azure services, falling back to basic extraction")
        # Fall back to the regular extraction
        return await run_extractor("education_resources/resource_index.json", subject_limit, resource_limit)
    
    try:
        # Organize resources by subject
        subjects = {}
        for resource in extracted_resources:
            subject = resource.get("subject")
            if subject not in subjects:
                subjects[subject] = []
            subjects[subject].append(resource)
        
        # Apply subject limit if specified
        if subject_limit and isinstance(subject_limit, int) and subject_limit > 0:
            subject_names = list(subjects.keys())[:subject_limit]
            subjects = {k: subjects[k] for k in subject_names if k in subjects}
        
        processed_count = 0
        processed_subjects = 0
        
        # Process each subject
        for subject, resources in subjects.items():
            logger.info(f"Processing subject: {subject} ({len(resources)} resources)")
            
            # Apply resource limit if specified
            if resource_limit and isinstance(resource_limit, int) and resource_limit > 0:
                resources = resources[:resource_limit]
            
            # Process resources
            processed = await enhancer.batch_process_resources(resources)
            processed_count += len(processed)
            processed_subjects += 1
            
            logger.info(f"Completed processing for {subject}: {len(processed)}/{len(resources)} resources")
        
        return {
            "processed_count": processed_count,
            "subjects_processed": processed_subjects,
            "enhanced": True
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced extraction: {e}")
        # Fall back to regular extraction
        return await run_extractor("education_resources/resource_index.json", subject_limit, resource_limit)

async def run_two_step_scraper(
    step: str = "both",
    subject_limit: Optional[int] = None,
    resource_limit: Optional[int] = None,
    headless: bool = True,
    max_pages_per_subject: int = 10,
    use_azure: bool = True
) -> Dict[str, Any]:
    """
    Run the two-step scraper process with optional Azure enhancements.
    
    Args:
        step: Which step to run ('index', 'extract', or 'both')
        subject_limit: Maximum number of subjects to process
        resource_limit: Maximum number of resources per subject to process
        headless: Whether to run browser in headless mode
        max_pages_per_subject: Maximum pages to process per subject in indexing step
        use_azure: Whether to use Azure OpenAI and Azure Search for enhancement
        
    Returns:
        Dictionary with results
    """
    results = {
        "step_1_results": None,
        "step_2_results": None
    }
    
    # Get the absolute path to the output directory in the project root
    output_dir = os.path.join(os.getcwd(), "education_resources")
    os.makedirs(output_dir, exist_ok=True)
    
    # Define index path
    index_path = os.path.join(output_dir, "resource_index.json")
    
    # Step 1: Index resources
    if step in ["index", "both"]:
        logger.info("Starting Step 1: Indexing education resources...")
        
        results["step_1_results"] = await run_indexer(
            subject_limit=subject_limit,
            headless=headless,
            max_pages_per_subject=max_pages_per_subject
        )
        
        logger.info(f"Step 1 completed. Results: {results['step_1_results'].get('total_resources', 0)} resources indexed.")
    
    # Step 2: Extract content from resources
    if step in ["extract", "both"]:
        logger.info("Starting Step 2: Extracting content from education resources...")
        
        # Check if index file exists
        if not os.path.exists(index_path):
            logger.error(f"Index file not found: {index_path}")
            if step == "extract":
                return {"error": f"Index file not found: {index_path}. Run the indexer step first."}
        else:
            # Load the resources from the index
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                all_resources = []
                if "subjects" in index_data:
                    for subject_name, subject_data in index_data["subjects"].items():
                        if "resources" in subject_data:
                            for resource in subject_data["resources"]:
                                # Add subject to resource if not present
                                if "subject" not in resource:
                                    resource["subject"] = subject_name
                                all_resources.append(resource)
                
                if use_azure and all_resources:
                    # Use the enhanced extraction with Azure services
                    results["step_2_results"] = await enhance_extraction(
                        all_resources,
                        subject_limit=subject_limit,
                        resource_limit=resource_limit
                    )
                else:
                    # Use the regular extraction
                    results["step_2_results"] = await run_extractor(
                        index_path=index_path,
                        subject_limit=subject_limit,
                        resource_limit=resource_limit,
                        headless=headless
                    )
                
                logger.info(f"Step 2 completed. Results: {results['step_2_results'].get('processed_count', 0)} resources processed.")
            except Exception as e:
                logger.error(f"Error loading or processing index: {e}")
                results["step_2_results"] = {"error": str(e)}
    
    return results

def main():
    """Main entry point with command line arguments."""
    parser = argparse.ArgumentParser(description="Two-step education resource scraper")
    
    parser.add_argument(
        "--step",
        type=str,
        choices=["index", "extract", "both"],
        default="both",
        help="Which step to run: 'index', 'extract', or 'both' (default: both)"
    )
    
    parser.add_argument(
        "--subject-limit",
        type=int,
        help="Maximum number of subjects to process (default: all)"
    )
    
    parser.add_argument(
        "--resource-limit",
        type=int,
        help="Maximum number of resources per subject to process (default: all)"
    )
    
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run with visible browser (not headless)"
    )
    
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Maximum pages to process per subject in indexing step (default: 10)"
    )
    
    parser.add_argument(
        "--no-azure",
        action="store_true",
        help="Disable Azure OpenAI and Azure Search enhancement"
    )
    
    args = parser.parse_args()
    
    # Run the scraper
    result = asyncio.run(run_two_step_scraper(
        step=args.step,
        subject_limit=args.subject_limit,
        resource_limit=args.resource_limit,
        headless=not args.visible,
        max_pages_per_subject=args.max_pages,
        use_azure=not args.no_azure
    ))
    
    # Print summary
    print("\n===== Scraping Summary =====")
    if args.step in ["index", "both"] and "step_1_results" in result:
        if isinstance(result["step_1_results"], dict) and "total_resources" in result["step_1_results"]:
            print(f"Step 1 (Indexing): {result['step_1_results']['total_resources']} resources indexed across {len(result['step_1_results'].get('subjects', {}))} subjects")
        else:
            print(f"Step 1 (Indexing): Completed with issues.")
    
    if args.step in ["extract", "both"] and "step_2_results" in result:
        if isinstance(result["step_2_results"], dict) and "processed_count" in result["step_2_results"]:
            print(f"Step 2 (Extraction): {result['step_2_results']['processed_count']} resources processed across {result['step_2_results']['subjects_processed']} subjects")
            if result["step_2_results"].get("enhanced", False):
                print("  - Enhanced with Azure OpenAI and Azure Search")
        else:
            print(f"Step 2 (Extraction): Completed with issues.")
    
    print(f"\nOutput files saved to: {os.path.abspath(os.path.join(os.getcwd(), 'education_resources'))}")

if __name__ == "__main__":
    main()