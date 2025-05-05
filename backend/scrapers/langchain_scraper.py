# backend/scrapers/langchain_scraper.py
"""
LangChain-enhanced scraper for educational content.
Uses LangChain's document loading, text splitting, and embedding capabilities
to improve content extraction and processing.
"""

import asyncio
import logging
import os
import sys
from typing import List, Dict, Any, Optional
import json
import uuid
from datetime import datetime
from urllib.parse import urljoin

# LangChain imports
from langchain.document_loaders import WebBaseLoader, BSHTMLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chat_models import AzureChatOpenAI
from langchain.chains import create_extraction_chain
from langchain.schema import Document

# Playwright imports for browser automation
from playwright.async_api import async_playwright, Page, Browser

# Setup path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import settings
from config.settings import Settings

# Initialize settings
settings = Settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('langchain_scraper.log')
    ]
)

logger = logging.getLogger(__name__)

# Predefined list of subjects with their URLs (same as the original scraper)
SUBJECT_LINKS = [
    {"name": "Arts", "url": "https://www.abc.net.au/education/subjects-and-topics/arts"},
    {"name": "English", "url": "https://www.abc.net.au/education/subjects-and-topics/english"},
    {"name": "Geography", "url": "https://www.abc.net.au/education/subjects-and-topics/geography"},
    {"name": "Maths", "url": "https://www.abc.net.au/education/subjects-and-topics/maths"},
    {"name": "Science", "url": "https://www.abc.net.au/education/subjects-and-topics/science"},
    {"name": "Technologies", "url": "https://www.abc.net.au/education/subjects-and-topics/technologies"},
    {"name": "Languages", "url": "https://www.abc.net.au/education/subjects-and-topics/languages"}
]

class LangChainScraperManager:
    """
    A scraper that uses LangChain capabilities to extract and process educational content.
    """
    
    def __init__(self):
        """Initialize the LangChain scraper."""
        self.base_url = "https://www.abc.net.au/education"
        
        # Will be initialized later
        self.browser = None
        self.context = None
        self.page = None
        self.azure_embeddings = None
        self.azure_llm = None
        
        # Create output directories
        self.output_dir = os.path.join(os.getcwd(), "education_resources")
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.debug_dir = os.path.join(os.getcwd(), "debug_output")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        self.content_dir = os.path.join(self.output_dir, "content")
        os.makedirs(self.content_dir, exist_ok=True)
        
    async def setup(self, headless=True):
        """Initialize Playwright browser and LangChain components."""
        logger.info(f"Setting up Playwright browser (headless={headless})...")
        
        # Initialize Playwright
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless, 
            slow_mo=50  # Add slight delay between actions for stability
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        
        self.page = await self.context.new_page()
        
        # Set default timeout (120 seconds)
        self.page.set_default_timeout(120000)
        
        # Initialize LangChain embeddings if Azure OpenAI settings are available
        if (hasattr(settings, 'AZURE_OPENAI_ENDPOINT') and 
            hasattr(settings, 'AZURE_OPENAI_KEY') and 
            settings.AZURE_OPENAI_ENDPOINT and 
            settings.AZURE_OPENAI_KEY):
            
            self.azure_embeddings = AzureOpenAIEmbeddings(
                azure_deployment=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_KEY
            )
            
            self.azure_llm = AzureChatOpenAI(
                azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_KEY,
                temperature=0.2
            )
            
            logger.info("Azure OpenAI components initialized for LangChain")
        else:
            logger.warning("Azure OpenAI settings not available. LangChain embedding and extraction features will be limited.")
    
    async def teardown(self):
        """Close browser and other resources."""
        logger.info("Tearing down browser...")
        
        if self.page:
            await self.page.close()
        
        if self.context:
            await self.context.close()
        
        if self.browser:
            await self.browser.close()
    
    async def save_screenshot(self, name):
        """Save a screenshot for debugging."""
        if self.page:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(self.debug_dir, f"{name}_{timestamp}.png")
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
    
    async def save_html(self, name):
        """Save the current page HTML for debugging."""
        if self.page:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = os.path.join(self.debug_dir, f"{name}_{timestamp}.html")
            html_content = await self.page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"HTML saved to {html_path}")
    
    async def discover_subjects_and_ages(self):
        """
        Discover subjects and age groups from the ABC Education website.
        
        Returns:
            Dictionary of subjects with their respective age groups
        """
        subjects_data = {}
        
        # Process each predefined subject
        for subject_link in SUBJECT_LINKS:
            subject_name = subject_link["name"]
            subject_url = subject_link["url"]
            
            logger.info(f"Discovering age groups for subject: {subject_name}")
            
            try:
                # Navigate to the subject page
                await self.page.goto(subject_url, wait_until="networkidle")
                await self.page.wait_for_selector("body", state="visible")
                
                # Take screenshot for debugging
                await self.save_screenshot(f"subject_{subject_name.lower().replace(' ', '_')}")
                
                # Extract age groups using Playwright
                age_groups = await self._extract_age_groups_from_page()
                
                # Add subject with age groups to the data
                subjects_data[subject_name] = {
                    "url": subject_url,
                    "age_groups": age_groups
                }
                
                logger.info(f"Found {len(age_groups)} age groups for {subject_name}")
                
                # Add a small delay between subjects
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error discovering age groups for subject {subject_name}: {e}")
        
        return subjects_data
    
    async def _extract_age_groups_from_page(self):
        """Extract age groups from the current page."""
        age_groups = []
        
        # Look for age group tabs/filters using various selectors
        age_group_selectors = [
            ".tabs a",
            "nav.years a",
            "[data-testid='years-filter'] a",
            "a[href*='#years']",
            ".year-tabs a",
            "a[role='tab']"
        ]
        
        for selector in age_group_selectors:
            tabs = await self.page.query_selector_all(selector)
            if tabs:
                logger.info(f"Found {len(tabs)} potential age group tabs with selector: {selector}")
                
                for tab in tabs:
                    try:
                        href = await tab.get_attribute("href")
                        text = await tab.text_content()
                        
                        if href and text:
                            # Extract the fragment from the URL
                            fragment = href.split("#")[-1] if "#" in href else ""
                            
                            # Clean the age group text
                            age_group = text.strip()
                            
                            # Skip if it's "All Years" or contains "all-years"
                            if age_group.lower() == "all years" or "all-years" in href.lower():
                                continue
                            
                            # Check if this age group is already in our list
                            if not any(ag["name"] == age_group for ag in age_groups):
                                age_groups.append({
                                    "name": age_group,
                                    "fragment": fragment,
                                    "url": f"{self.page.url}#{fragment}" if fragment else self.page.url
                                })
                                logger.info(f"Found age group: {age_group} ({fragment})")
                    except Exception as e:
                        logger.error(f"Error processing age group tab: {e}")
                
                # If we found age groups with this selector, stop trying other selectors
                if age_groups:
                    break
        
        return age_groups
    
    async def extract_resources_for_age_group(self, subject_name, age_group, max_retries=3):
        """
        Extract educational resources for a specific subject and age group.
        
        Args:
            subject_name: Name of the subject
            age_group: Dictionary with age group details
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of resource dictionaries
        """
        age_group_name = age_group["name"]
        age_group_url = age_group["url"]
        
        logger.info(f"Extracting resources for {subject_name} - {age_group_name}")
        
        # Navigate to the page
        await self.page.goto(age_group_url, wait_until="networkidle")
        await self.page.wait_for_selector("body", state="visible")
        
        # Take screenshot for debugging
        safe_name = f"{subject_name.replace(' ', '_')}_{age_group_name.replace(' ', '_')}"
        await self.save_screenshot(f"resources_{safe_name}")
        await self.save_html(f"resources_{safe_name}")
        
        # Try to click on the age group tab if needed
        fragment = age_group.get("fragment")
        if fragment:
            try:
                tab_selectors = [
                    f"a[href*='#{fragment}']",
                    f"a[data-testid='{fragment}']",
                    f"a[data-value='{fragment}']",
                    f"a[aria-controls='{fragment}']",
                    f"a:has-text('{age_group_name}')"
                ]
                
                for selector in tab_selectors:
                    tab = await self.page.query_selector(selector)
                    if tab and await tab.is_visible():
                        await tab.click()
                        logger.info(f"Clicked tab for age group using selector: {selector}")
                        # Wait for content to update
                        await asyncio.sleep(2)
                        await self.page.wait_for_load_state("networkidle")
                        # Take another screenshot after clicking
                        await self.save_screenshot(f"resources_{safe_name}_after_click")
                        break
            except Exception as e:
                logger.error(f"Error clicking age group tab: {e}")
        
        # Try to click "Load More" button if it exists
        await self._try_load_more_content()
        
        # Extract resources from the page
        resources = await self._extract_resource_links(subject_name, age_group_name)
        
        # Save the resource list
        self._save_resources_to_json(resources, subject_name, age_group_name)
        
        return resources
    
    async def _try_load_more_content(self, max_clicks=5):
        """Try to click 'Load More' button multiple times."""
        for i in range(max_clicks):
            try:
                # Look for common "Load More" button selectors
                load_more_selectors = [
                    "button:has-text('Load more')",
                    "button:has-text('Show more')",
                    ".load-more button",
                    ".content-block-tiles__load-more",
                    "[data-testid='load-more-button']"
                ]
                
                button_found = False
                for selector in load_more_selectors:
                    button = await self.page.query_selector(selector)
                    if button and await button.is_visible():
                        await button.click()
                        button_found = True
                        logger.info(f"Clicked 'Load More' button ({i+1}/{max_clicks})")
                        await asyncio.sleep(2)  # Wait for content to load
                        await self.page.wait_for_load_state("networkidle")
                        break
                
                if not button_found:
                    logger.info("No more 'Load More' buttons found")
                    break
                    
            except Exception as e:
                logger.error(f"Error clicking 'Load More' button: {e}")
                break
    
    async def _extract_resource_links(self, subject_name, age_group_name):
        """Extract resource links from the current page."""
        resources = []
        
        # Look for cards, tiles, or content containers
        container_selectors = [
            ".content-card",
            ".content-tile",
            ".card",
            ".tile",
            ".resource-item",
            ".content-block-tiles__item",
            "li.tile",
            "article"
        ]
        
        for selector in container_selectors:
            containers = await self.page.query_selector_all(selector)
            if containers:
                logger.info(f"Found {len(containers)} potential resource containers with selector: {selector}")
                
                for container in containers:
                    try:
                        # Find link in the container
                        link = await container.query_selector("a")
                        if not link:
                            continue
                            
                        # Get href attribute
                        href = await link.get_attribute("href")
                        if not href:
                            continue
                            
                        # Make absolute URL if needed
                        if href.startswith('/'):
                            href = urljoin(self.base_url, href)
                            
                        # Skip non-educational content
                        if not ('abc.net.au' in href and '/education/' in href):
                            continue
                            
                        # Skip if it contains hash fragments (likely navigation)
                        if "#" in href:
                            continue
                            
                        # Extract title
                        title = await link.text_content()
                        if not title or len(title.strip()) < 3:
                            # Try to find a heading
                            heading = await container.query_selector("h1, h2, h3, h4, h5, h6")
                            if heading:
                                title = await heading.text_content()
                                
                        title = title.strip() if title else ""
                        if not title:
                            continue
                            
                        # Extract description if available
                        description = ""
                        desc_elem = await container.query_selector("p")
                        if desc_elem:
                            description = await desc_elem.text_content()
                            description = description.strip()
                        
                        # Create resource entry
                        resources.append({
                            "id": str(uuid.uuid4()),
                            "title": title,
                            "url": href,
                            "subject": subject_name,
                            "age_group": age_group_name,
                            "description": description,
                            "discovered_at": datetime.utcnow().isoformat()
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing resource container: {e}")
                
                # If we found resources with this selector, stop trying others
                if resources:
                    break
        
        # If no resources found from containers, try a fallback to all links
        if not resources:
            try:
                # Get all links from the page
                links = await self.page.query_selector_all("main a, .content-main a, .main-content a")
                
                for link in links:
                    try:
                        # Get href attribute
                        href = await link.get_attribute("href")
                        if not href:
                            continue
                            
                        # Make absolute URL if needed
                        if href.startswith('/'):
                            href = urljoin(self.base_url, href)
                            
                        # Skip non-educational content
                        if not ('abc.net.au' in href and '/education/' in href):
                            continue
                            
                        # Skip if it contains hash fragments (likely navigation)
                        if "#" in href:
                            continue
                            
                        # Extract title
                        title = await link.text_content()
                        title = title.strip() if title else ""
                        if not title or len(title) < 5:
                            continue
                            
                        # Skip navigation links
                        is_nav = await link.evaluate("""el => {
                            let parent = el.parentElement;
                            for (let i = 0; i < 3 && parent; i++) {
                                if (parent.tagName && ['NAV', 'HEADER', 'FOOTER'].includes(parent.tagName)) {
                                    return true;
                                }
                                parent = parent.parentElement;
                            }
                            return false;
                        }""")
                        
                        if is_nav:
                            continue
                        
                        # Create resource entry
                        resources.append({
                            "id": str(uuid.uuid4()),
                            "title": title,
                            "url": href,
                            "subject": subject_name,
                            "age_group": age_group_name,
                            "description": "",
                            "discovered_at": datetime.utcnow().isoformat()
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing link: {e}")
                        
            except Exception as e:
                logger.error(f"Error in fallback link extraction: {e}")
        
        logger.info(f"Extracted {len(resources)} resources for {subject_name} - {age_group_name}")
        return resources
    
    def _save_resources_to_json(self, resources, subject_name, age_group_name=None):
        """Save extracted resources to a JSON file."""
        if not resources:
            return
            
        # Create a safe filename
        safe_subject = subject_name.replace(" ", "_").replace("/", "_")
        safe_age_group = ""
        
        if age_group_name:
            safe_age_group = f"_{age_group_name.replace(' ', '_').replace('/', '_')}"
            
        filename = os.path.join(self.output_dir, f"{safe_subject}{safe_age_group}_resources.json")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(resources, f, indent=2)
                
            logger.info(f"Saved {len(resources)} resources to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving resources to JSON: {e}")
    
    async def process_resource_content(self, resource):
        """
        Process a resource to extract detailed content using LangChain.
        
        Args:
            resource: Resource dictionary
            
        Returns:
            Processed content dictionary
        """
        resource_url = resource["url"]
        resource_title = resource["title"]
        
        logger.info(f"Processing content for: {resource_title[:30]}{'...' if len(resource_title) > 30 else ''}")
        
        # Create a unique ID for this content
        content_id = resource.get("id", str(uuid.uuid4()))
        
        try:
            # Load the webpage using LangChain's WebBaseLoader
            loader = WebBaseLoader(resource_url)
            documents = await asyncio.to_thread(loader.load)
            
            # If no documents were loaded, try to load using Playwright instead
            if not documents:
                html_content = await self._get_page_html_with_playwright(resource_url)
                if html_content:
                    # Create a temporary HTML file
                    temp_file = os.path.join(self.debug_dir, f"temp_{content_id}.html")
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    # Load with BSHTMLLoader
                    bs_loader = BSHTMLLoader(temp_file)
                    documents = await asyncio.to_thread(bs_loader.load)
                    
                    # Remove the temporary file
                    os.remove(temp_file)
            
            if not documents:
                logger.warning(f"Could not load content for {resource_url}")
                return None
            
            # Combine document content
            text_content = "\n\n".join([doc.page_content for doc in documents])
            
            # Split text into chunks for processing
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            
            chunks = await asyncio.to_thread(text_splitter.split_text, text_content)
            
            # Create metadata for the content
            metadata = {
                "id": content_id,
                "title": resource_title,
                "url": resource_url,
                "subject": resource.get("subject"),
                "age_group": resource.get("age_group"),
                "source": "ABC Education",
                "scraped_at": datetime.utcnow().isoformat()
            }
            
            # Determine content type using LangChain extraction if Azure OpenAI is available
            if self.azure_llm:
                content_type = await self._extract_content_properties(
                    resource_title,
                    chunks[0] if chunks else ""
                )
                
                # Add extracted properties to metadata
                metadata.update(content_type)
            else:
                # Basic content type detection based on URL and title
                if any(term in resource_url.lower() for term in ['video', 'watch', '.mp4']):
                    metadata["content_type"] = "video"
                elif any(term in resource_url.lower() for term in ['quiz', 'test', 'assessment']):
                    metadata["content_type"] = "quiz"
                elif any(term in resource_url.lower() for term in ['interactive', 'game']):
                    metadata["content_type"] = "interactive"
                else:
                    metadata["content_type"] = "article"
# Create vector store if embeddings are available
            if self.azure_embeddings and chunks:
                # Create document objects with metadata for each chunk
                docs = [
                    Document(
                        page_content=chunk,
                        metadata=metadata
                    ) for chunk in chunks
                ]
                
                # Create a FAISS vector store
                vector_store = await asyncio.to_thread(
                    FAISS.from_documents,
                    docs,
                    self.azure_embeddings
                )
                
                # Save vector store for this content
                vector_filename = os.path.join(
                    self.content_dir,
                    f"{content_id}_vectors"
                )
                
                await asyncio.to_thread(
                    vector_store.save_local,
                    vector_filename
                )
                
                logger.info(f"Saved vector store for {resource_title} to {vector_filename}")
                
                # Add embedding dimensions to metadata
                metadata["has_embeddings"] = True
                metadata["chunk_count"] = len(chunks)
                metadata["vector_store_path"] = vector_filename
            
            # Save the full content
            content_filename = os.path.join(
                self.content_dir,
                f"{content_id}_content.json"
            )
            
            full_content = {
                "metadata": metadata,
                "content": text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                "chunks": chunks[:3] if len(chunks) > 3 else chunks  # Save only first few chunks to keep file size manageable
            }
            
            with open(content_filename, 'w', encoding='utf-8') as f:
                json.dump(full_content, f, indent=2)
            
            logger.info(f"Saved content for {resource_title} to {content_filename}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error processing resource content: {e}")
            return None
    
    async def _get_page_html_with_playwright(self, url):
        """Get page HTML using Playwright."""
        try:
            await self.page.goto(url, wait_until="networkidle")
            await self.page.wait_for_selector("body", state="visible")
            
            # Get HTML content
            html_content = await self.page.content()
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error getting page HTML with Playwright: {e}")
            return None
    
    async def _extract_content_properties(self, title, text_sample):
        """
        Extract content properties using LangChain extraction.
        
        Args:
            title: Content title
            text_sample: Sample of the content text
            
        Returns:
            Dictionary with extracted properties
        """
        # Schema for extraction
        schema = {
            "properties": {
                "content_type": {
                    "type": "string",
                    "enum": ["article", "video", "interactive", "quiz", "worksheet", "lesson", "activity"],
                    "description": "The type of educational content"
                },
                "difficulty_level": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                    "description": "The difficulty level of the content"
                },
                "grade_levels": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "The grade levels this content is appropriate for (1-12)"
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Educational topics covered in this content"
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Estimated time in minutes to complete this content"
                }
            },
            "required": ["content_type", "difficulty_level"]
        }
        
        # Combine title and text sample for analysis
        combined_text = f"Title: {title}\n\nContent sample: {text_sample[:500]}..."
        
        try:
            # Run extraction chain
            extraction_chain = create_extraction_chain(schema, self.azure_llm)
            result = await extraction_chain.arun(combined_text)
            
            if result and len(result) > 0:
                # Process the first extraction result
                properties = result[0]
                
                # Ensure grade_levels is a list
                if "grade_levels" in properties and not isinstance(properties["grade_levels"], list):
                    if isinstance(properties["grade_levels"], int):
                        properties["grade_levels"] = [properties["grade_levels"]]
                    else:
                        properties["grade_levels"] = []
                
                # Ensure topics is a list
                if "topics" in properties and not isinstance(properties["topics"], list):
                    if isinstance(properties["topics"], str):
                        properties["topics"] = [properties["topics"]]
                    else:
                        properties["topics"] = []
                
                return properties
            else:
                # Default values if extraction fails
                return {
                    "content_type": "article",
                    "difficulty_level": "intermediate",
                    "grade_levels": [],
                    "topics": [],
                    "duration_minutes": 15  # Default duration
                }
                
        except Exception as e:
            logger.error(f"Error in content property extraction: {e}")
            
            # Default values
            return {
                "content_type": "article",
                "difficulty_level": "intermediate",
                "grade_levels": [],
                "topics": [],
                "duration_minutes": 15  # Default duration
            }
    
    async def create_content_index(self):
        """Create a comprehensive index of all processed content."""
        # Path to the content directory
        content_files = [
            f for f in os.listdir(self.content_dir) 
            if f.endswith('_content.json')
        ]
        
        if not content_files:
            logger.warning("No content files found in content directory")
            return None
        
        # Create the index
        content_index = {
            "created_at": datetime.utcnow().isoformat(),
            "total_content": len(content_files),
            "subjects": {},
            "age_groups": {},
            "content_types": {}
        }
        
        # Process each content file
        for filename in content_files:
            try:
                # Load the content
                with open(os.path.join(self.content_dir, filename), 'r', encoding='utf-8') as f:
                    content_data = json.load(f)
                
                # Extract metadata
                metadata = content_data.get("metadata", {})
                subject = metadata.get("subject")
                age_group = metadata.get("age_group")
                content_type = metadata.get("content_type")
                
                # Add to subjects index
                if subject:
                    if subject not in content_index["subjects"]:
                        content_index["subjects"][subject] = {
                            "count": 0,
                            "content_ids": []
                        }
                    
                    content_index["subjects"][subject]["count"] += 1
                    content_index["subjects"][subject]["content_ids"].append(metadata.get("id"))
                
                # Add to age groups index
                if age_group:
                    if age_group not in content_index["age_groups"]:
                        content_index["age_groups"][age_group] = {
                            "count": 0,
                            "content_ids": []
                        }
                    
                    content_index["age_groups"][age_group]["count"] += 1
                    content_index["age_groups"][age_group]["content_ids"].append(metadata.get("id"))
                
                # Add to content types index
                if content_type:
                    if content_type not in content_index["content_types"]:
                        content_index["content_types"][content_type] = {
                            "count": 0,
                            "content_ids": []
                        }
                    
                    content_index["content_types"][content_type]["count"] += 1
                    content_index["content_types"][content_type]["content_ids"].append(metadata.get("id"))
                
            except Exception as e:
                logger.error(f"Error processing content file {filename}: {e}")
        
        # Save the content index
        index_path = os.path.join(self.output_dir, "content_index.json")
        
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(content_index, f, indent=2)
                
            logger.info(f"Content index saved to {index_path}")
            
            return content_index
            
        except Exception as e:
            logger.error(f"Error saving content index: {e}")
            return None

async def run_langchain_scraper(
    subject_limit: Optional[int] = None,
    resource_limit: Optional[int] = None,
    process_content: bool = True,
    headless: bool = True
):
    """
    Run the LangChain-enhanced scraper.
    
    Args:
        subject_limit: Maximum number of subjects to process
        resource_limit: Maximum number of resources per subject/age group
        process_content: Whether to process detailed content for resources
        headless: Whether to run browser in headless mode
        
    Returns:
        Dictionary with scraping results
    """
    scraper = LangChainScraperManager()
    
    try:
        # Initialize scraper
        await scraper.setup(headless=headless)
        
        # Discover subjects and age groups
        subjects_data = await scraper.discover_subjects_and_ages()
        
        # Apply subject limit if specified
        subject_names = list(subjects_data.keys())
        if subject_limit and isinstance(subject_limit, int) and subject_limit > 0:
            subject_names = subject_names[:subject_limit]
            
        logger.info(f"Processing {len(subject_names)} subjects")
        
        # Extract resources for each subject and age group
        all_resources = []
        
        for subject_name in subject_names:
            subject_data = subjects_data[subject_name]
            
            # Extract resources for each age group
            for age_group in subject_data["age_groups"]:
                resources = await scraper.extract_resources_for_age_group(
                    subject_name, 
                    age_group
                )
                
                # Apply resource limit if specified
                if resource_limit and isinstance(resource_limit, int) and resource_limit > 0:
                    resources = resources[:resource_limit]
                
                # Add to all resources
                all_resources.extend(resources)
                
                # Process content for each resource if enabled
                if process_content:
                    processed_count = 0
                    
                    for resource in resources:
                        try:
                            await scraper.process_resource_content(resource)
                            processed_count += 1
                            
                            # Add a small delay between processing resources
                            await asyncio.sleep(1)
                            
                        except Exception as e:
                            logger.error(f"Error processing resource content: {e}")
                    
                    logger.info(f"Processed content for {processed_count}/{len(resources)} resources for {subject_name} - {age_group['name']}")
        
        # Create comprehensive content index
        if process_content:
            content_index = await scraper.create_content_index()
        
        logger.info(f"Scraping completed. Found {len(all_resources)} resources across {len(subject_names)} subjects")
        
        return {
            "total_resources": len(all_resources),
            "subjects_processed": len(subject_names),
            "content_processed": process_content
        }
        
    except Exception as e:
        logger.error(f"Error running LangChain scraper: {e}")
        return {"error": str(e)}
        
    finally:
        # Clean up
        await scraper.teardown()

if __name__ == "__main__":
    # Run the scraper
    asyncio.run(run_langchain_scraper(
        subject_limit=2,  # Process 2 subjects for testing
        resource_limit=5,  # Process 5 resources per subject/age group
        process_content=True,  # Process detailed content
        headless=False  # Run with visible browser for debugging
    ))