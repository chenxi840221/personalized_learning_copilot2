# backend/scrapers/edu_resource_indexer.py
import asyncio
import logging
from typing import List, Dict, Any, Optional
import re
import json
import os
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

# Playwright imports for browser automation
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Setup path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('edu_indexer.log')
    ]
)

logger = logging.getLogger(__name__)

# Predefined list of subjects with their URLs
SUBJECT_LINKS = [
    {"name": "Arts", "url": "https://www.abc.net.au/education/subjects-and-topics/arts"},
    {"name": "English", "url": "https://www.abc.net.au/education/subjects-and-topics/english"},
    {"name": "Geography", "url": "https://www.abc.net.au/education/subjects-and-topics/geography"},
    {"name": "Maths", "url": "https://www.abc.net.au/education/subjects-and-topics/maths"},
    {"name": "Science", "url": "https://www.abc.net.au/education/subjects-and-topics/science"},
    {"name": "Technologies", "url": "https://www.abc.net.au/education/subjects-and-topics/technologies"},
    {"name": "Languages", "url": "https://www.abc.net.au/education/subjects-and-topics/languages"}
]

class EducationResourceIndexer:
    """A scraper that builds an index of educational resources from ABC Education website with age group information."""
    
    def __init__(self):
        """Initialize the indexer."""
        self.base_url = "https://www.abc.net.au/education"
        
        # Will be initialized later
        self.browser = None
        self.context = None
        self.page = None
        
        # Create output directory
        self.output_dir = os.path.join(os.getcwd(), "education_resources")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create debug directory
        self.debug_dir = os.path.join(os.getcwd(), "debug_output")
        os.makedirs(self.debug_dir, exist_ok=True)
    
    async def setup(self, headless=True):
        """Initialize Playwright browser."""
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
    
    async def discover_age_groups(self, subject_url: str) -> List[Dict[str, str]]:
        """
        Discover available age groups for a subject.
        
        Args:
            subject_url: URL of the subject page
            
        Returns:
            List of dictionaries with age group name and URL fragment
        """
        logger.info(f"Discovering age groups for subject at {subject_url}")
        
        # Navigate to the subject page
        await self.page.goto(subject_url, wait_until="networkidle")
        await self.page.wait_for_selector("body", state="visible")
        
        # Take screenshot for debugging
        await self.save_screenshot(f"subject_age_groups_{subject_url.split('/')[-1]}")
        
        # Look for age group tabs/filters
        age_group_selectors = [
            ".tabs a",
            "nav.years a",
            "[data-testid='years-filter'] a",
            "a[href*='#years']",
            ".year-tabs a",
            "a[role='tab']"
        ]
        
        age_groups = []
        
        # Find specific age groups (excluding "All Years")
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
                            
                            # Skip if it's not an age group tab or if it's "All Years" or contains "all-years"
                            if (not (age_group.lower().startswith(("year", "foundation")) or 
                                   re.search(r"f-\d+|years \d+-\d+|\d+-\d+", age_group.lower())) or
                                   age_group.lower() == "all years" or
                                   "all-years" in href.lower()):
                                continue
                            
                            # Check if this age group is already in our list
                            if not any(ag["name"] == age_group for ag in age_groups):
                                age_groups.append({
                                    "name": age_group,
                                    "fragment": fragment,
                                    "url": f"{subject_url}#{fragment}" if fragment else subject_url,
                                    "is_default": False
                                })
                                logger.info(f"Found age group: {age_group} ({fragment})")
                    except Exception as e:
                        logger.error(f"Error processing age group tab: {e}")
                
                # If we found age groups with this selector, stop trying other selectors
                if age_groups:
                    break
        
        logger.info(f"Discovered {len(age_groups)} age groups: {[ag['name'] for ag in age_groups]}")
        return age_groups
    
    async def find_education_resources(self, subject_link: Dict[str, str], age_group: Dict[str, str], max_retry=3) -> List[Dict[str, str]]:
        """
        Find all education resource links for a subject and age group.
        
        Args:
            subject_link: Dictionary with subject name and URL
            age_group: Dictionary with age group name and URL fragment
            max_retry: Maximum number of retries if no resources found
            
        Returns:
            List of dictionaries with resource title, URL, subject, and age group
        """
        subject_name = subject_link["name"]
        age_group_name = age_group["name"]
        age_group_url = age_group["url"]
        fragment = age_group.get("fragment", "")
        
        # Skip if URL contains all-years
        if "all-years" in age_group_url:
            logger.info(f"Skipping all-years URL: {age_group_url}")
            return []
        
        logger.info(f"Finding education resources for {subject_name} - {age_group_name} at {age_group_url}")
        
        # Navigate to the subject page with age group fragment
        await self.page.goto(age_group_url, wait_until="networkidle")
        await self.page.wait_for_selector("body", state="visible")
        
        # Take screenshot and save HTML for debugging
        safe_name = f"{subject_name.replace(' ', '_')}_{age_group_name.replace(' ', '_')}"
        await self.save_screenshot(f"subject_{safe_name}")
        await self.save_html(f"subject_{safe_name}")
        
        # Check if we need to click on a tab to show age-specific content
        resources = []
        retries = 0
        
        while len(resources) == 0 and retries < max_retry:
            if retries > 0:
                logger.info(f"Retry {retries} for {subject_name} - {age_group_name}")
            
            # Handle age group tab clicking strategy
            if fragment and retries == 0:
                try:
                    # Try different tab selection strategies
                    tab_selectors = [
                        f"a[href*='#{fragment}']",
                        f"a[data-testid='{fragment}']",
                        f"a[data-value='{fragment}']",
                        f"a[aria-controls='{fragment}']",
                        f"a:has-text('{age_group_name}')"
                    ]
                    
                    tab_clicked = False
                    for selector in tab_selectors:
                        tab = await self.page.query_selector(selector)
                        if tab and await tab.is_visible():
                            await tab.click()
                            tab_clicked = True
                            logger.info(f"Clicked tab for age group using selector: {selector}")
                            # Wait for content to update
                            await asyncio.sleep(2)
                            await self.page.wait_for_load_state("networkidle")
                            # Take another screenshot after clicking
                            await self.save_screenshot(f"subject_{safe_name}_after_click")
                            await self.save_html(f"subject_{safe_name}_after_click")
                            break
                            
                    if not tab_clicked:
                        logger.warning(f"Could not find clickable tab for age group: {age_group_name}")
                except Exception as e:
                    logger.error(f"Error clicking age group tab: {e}")
            
            # Different retry strategies
            if retries == 1:
                # Second try: reload page and wait longer
                await self.page.reload(wait_until="networkidle")
                await asyncio.sleep(3)
            elif retries == 2:
                # Third try: try clicking the tab again with a different approach
                if fragment:
                    try:
                        # Click any element that looks like the age group
                        elements = await self.page.query_selector_all("a, button, li, div")
                        for element in elements:
                            text = await element.text_content()
                            if text and age_group_name.lower() in text.lower() and await element.is_visible():
                                await element.click()
                                logger.info(f"Clicked element with text matching age group: {text}")
                                await asyncio.sleep(2)
                                break
                    except Exception as e:
                        logger.error(f"Error in alternate tab clicking: {e}")
            
            # Get the main content area
            main_content_selectors = [
                "main",
                "#main",
                ".main-content",
                "article",
                ".content-main",
                ".content-wrapper",
                ".content-block-tiles__container",  # ABC Education specific content container
                ".content-body",
                "body"  # Fallback to body if no other containers found
            ]
            
            main_content = None
            for selector in main_content_selectors:
                content = await self.page.query_selector(selector)
                if content:
                    main_content = content
                    logger.info(f"Found main content with selector: {selector}")
                    break
            
            if not main_content:
                logger.warning(f"Could not find main content area for {subject_name} - {age_group_name}")
                retries += 1
                continue
            
            # Find all links in the main content
            links = await main_content.query_selector_all("a")
            logger.info(f"Found {len(links)} links in the main content for {subject_name} - {age_group_name}")
            
            # Get resource containers - sometimes resources are in cards or tiles
            resource_container_selectors = [
                ".content-card",
                ".content-tile",
                ".card",
                ".tile",
                ".resource-item",
                ".content-block-tiles__item",
                "li.tile",
                "article"
            ]
            
            resource_containers = []
            for selector in resource_container_selectors:
                containers = await self.page.query_selector_all(selector)
                if containers and len(containers) > 0:
                    logger.info(f"Found {len(containers)} resource containers with selector: {selector}")
                    resource_containers.extend(containers)
            
            # Process resource containers if found
            if resource_containers:
                for container in resource_containers:
                    try:
                        # Find the link inside the container
                        container_link = await container.query_selector("a")
                        if not container_link:
                            continue
                        
                        # Get href and title
                        href = await container_link.get_attribute("href")
                        if not href:
                            continue
                        
                        # Skip URLs with #all-years
                        if "#all-years" in href:
                            continue
                        
                        # Make absolute URL if needed
                        if href.startswith('/'):
                            href = urljoin(self.base_url, href)
                        
                        # Skip non-ABC links or navigation links
                        if not ('abc.net.au' in href and '/education/' in href):
                            continue
                        
                        # Skip if it's the current subject page
                        if href == subject_link["url"]:
                            continue
                        
                        # Skip if it contains hash fragments (likely tab navigation)
                        if "#" in href:
                            continue
                        
                        # Get title - first try the link text, then look for heading elements
                        title = await container_link.text_content()
                        if not title or len(title.strip()) < 3:
                            heading = await container.query_selector("h1, h2, h3, h4, h5, h6")
                            if heading:
                                title = await heading.text_content()
                        
                        title = title.strip() if title else ""
                        
                        # Skip if no title
                        if not title:
                            continue
                        
                        # This looks like a resource - add to list
                        resources.append({
                            "title": title,
                            "url": href,
                            "subject": subject_name,
                            "age_group": age_group_name
                        })
                        logger.info(f"Found resource from container: {title[:40]}{'...' if len(title) > 40 else ''}")
                    except Exception as e:
                        logger.error(f"Error processing resource container: {e}")
            
            # If no resources found from containers, fall back to processing all links
            if not resources:
                for link in links:
                    try:
                        # Get href and text
                        href = await link.get_attribute("href")
                        if not href:
                            continue
                        
                        # Skip URLs with #all-years
                        if "#all-years" in href:
                            continue
                        
                        # Make absolute URL if needed
                        if href.startswith('/'):
                            href = urljoin(self.base_url, href)
                        
                        # Skip non-ABC links or navigation links
                        if not ('abc.net.au' in href and '/education/' in href):
                            continue
                        
                        # Skip if it's the current subject page
                        if href == subject_link["url"]:
                            continue
                        
                        # Skip if it contains hash fragments (likely tab navigation)
                        if "#" in href:
                            continue
                        
                        # Get text content
                        text = await link.text_content()
                        text = text.strip() if text else ""
                        
                        # Skip if no text or very short text (likely UI elements)
                        if not text or len(text) < 5:
                            continue
                        
                        # Check if it's not in a typical navigation element
                        is_navigation = await link.evaluate("""el => {
                            let parent = el.parentElement;
                            for (let i = 0; i < 5 && parent; i++) {
                                if (parent.tagName && ['NAV', 'HEADER', 'FOOTER'].includes(parent.tagName)) {
                                    return true;
                                }
                                if (parent.className && ['nav', 'header', 'footer', 'menu', 'navigation'].some(c => parent.className.includes(c))) {
                                    return true;
                                }
                                parent = parent.parentElement;
                            }
                            return false;
                        }""")
                        
                        if is_navigation:
                            continue
                        
                        # Check if it looks like a content link - has some visual prominence
                        # like being in a card, having a heading as parent or being styled prominently
                        is_content_link = await link.evaluate("""el => {
                            // Check if inside a card or tile-like element
                            let parent = el.parentElement;
                            for (let i = 0; i < 4 && parent; i++) {
                                if (parent.className && ['card', 'tile', 'item', 'content-'].some(c => parent.className.includes(c))) {
                                    return true;
                                }
                                parent = parent.parentElement;
                            }
                            
                            // Check if the link is a heading or has a heading as a child
                            if (el.tagName && ['H1', 'H2', 'H3', 'H4', 'H5', 'H6'].includes(el.tagName)) {
                                return true;
                            }
                            
                            if (el.querySelector('h1, h2, h3, h4, h5, h6')) {
                                return true;
                            }
                            
                            // Check if link has an image
                            if (el.querySelector('img')) {
                                return true;
                            }
                            
                            // Check if link text is prominent (not too short, not too long)
                            if (el.textContent && el.textContent.trim().length > 10 && el.textContent.trim().length < 100) {
                                return true;
                            }
                            
                            return false;
                        }""")
                        
                        if not is_content_link and retries < 2:
                            continue
                        
                        # Looks like an education resource - add to list
                        resources.append({
                            "title": text,
                            "url": href,
                            "subject": subject_name,
                            "age_group": age_group_name
                        })
                        logger.info(f"Found resource: {text[:40]}{'...' if len(text) > 40 else ''}")
                        
                    except Exception as e:
                        logger.error(f"Error processing link: {e}")
            
            retries += 1
            
            # If we found resources, no need to retry
            if resources:
                break
                
            logger.warning(f"No resources found for {subject_name} - {age_group_name} on attempt {retries}. Retrying...")
            await asyncio.sleep(1)
        
        logger.info(f"Identified {len(resources)} education resources for {subject_name} - {age_group_name}")
        
        # Save the resource links to a JSON file
        self.save_resource_links_to_json(resources, subject_name, age_group_name)
        
        return resources
    
    def save_resource_links_to_json(self, resource_links: List[Dict[str, str]], subject_name: str, age_group_name: str = None):
        """Save resource links to a JSON file."""
        if not resource_links:
            return
            
        # Create a safe filename
        safe_subject = subject_name.replace(" ", "_").replace("/", "_")
        safe_age_group = ""
        if age_group_name:
            safe_age_group = f"_{age_group_name.replace(' ', '_').replace('/', '_')}"
        
        filename = os.path.join(self.output_dir, f"{safe_subject}{safe_age_group}_resources.json")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(resource_links, f, indent=2)
                
            logger.info(f"Saved {len(resource_links)} resource links to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving resource links to JSON: {e}")
    
    async def click_load_more(self) -> bool:
        """Attempt to click 'Load More' button if it exists."""
        load_more_selectors = [
            "button:has-text('Load more')",
            "button:has-text('Show more')",
            "button.load-more",
            ".content-block-tiles__load-more",
            "[data-testid='load-more-button']",
            ".load-more button",
            ".show-more button"
        ]
        
        for selector in load_more_selectors:
            try:
                # Check if button is visible
                button = await self.page.query_selector(selector)
                if button and await button.is_visible():
                    logger.info(f"Clicking 'Load more' button with selector: {selector}")
                    await button.click()
                    # Wait for new content to load
                    await asyncio.sleep(2)
                    await self.page.wait_for_load_state("networkidle")
                    return True
            except Exception as e:
                logger.debug(f"Could not click button with selector '{selector}': {e}")
        
        # Try to find any button that looks like "Load more"
        try:
            all_buttons = await self.page.query_selector_all("button")
            for button in all_buttons:
                text = await button.text_content()
                if text and ("load more" in text.lower() or "show more" in text.lower()) and await button.is_visible():
                    logger.info("Clicking 'Load more' button found by text")
                    await button.click()
                    await asyncio.sleep(2)
                    await self.page.wait_for_load_state("networkidle")
                    return True
        except Exception as e:
            logger.debug(f"Could not find 'Load more' button by text: {e}")
        
        logger.info("No 'Load more' button found or clickable")
        return False
    
    async def process_subject_age_group(self, 
                                       subject_link: Dict[str, str], 
                                       age_group: Dict[str, str],
                                       max_pages: int = 10) -> List[Dict[str, str]]:
        """
        Process a subject with specific age group to extract all educational resources, handling pagination.
        
        Args:
            subject_link: Dictionary with subject name and URL
            age_group: Dictionary with age group name and URL fragment
            max_pages: Maximum number of pages to process
            
        Returns:
            List of resource links
        """
        subject_name = subject_link["name"]
        age_group_name = age_group["name"]
        
        # Skip if this is an all-years URL
        if "all-years" in age_group.get("fragment", "") or "all-years" in age_group.get("url", ""):
            logger.info(f"Skipping all-years age group: {subject_name} - {age_group_name}")
            return []
        
        logger.info(f"Processing subject: {subject_name} - Age group: {age_group_name}")
        
        # Find initial education resources
        resources = await self.find_education_resources(subject_link, age_group)
        
        # Try to click "Load More" button up to max_pages times
        page_count = 1
        while page_count < max_pages:
            # Try to click "Load More" button
            clicked = await self.click_load_more()
            if not clicked:
                break
                
            # Find resources on the new page
            logger.info(f"Loading more content (page {page_count + 1})")
            await asyncio.sleep(2)  # Wait for content to load
            
            # Take screenshot after loading more
            safe_name = f"{subject_name.replace(' ', '_')}_{age_group_name.replace(' ', '_')}"
            await self.save_screenshot(f"subject_{safe_name}_page_{page_count + 1}")
            
            # Get new resources
            new_resources = await self.find_education_resources(subject_link, age_group)
            
            # Add new resources to the list (avoid duplicates by URL)
            existing_urls = {r["url"] for r in resources}
            for resource in new_resources:
                if resource["url"] not in existing_urls:
                    resources.append(resource)
                    existing_urls.add(resource["url"])
            
            page_count += 1
            logger.info(f"Now have {len(resources)} total resources for {subject_name} - {age_group_name}")
        
        # Save the final list of resources
        self.save_resource_links_to_json(resources, subject_name, age_group_name)
        
        return resources
    
    async def process_subject(self, subject_link: Dict[str, str], max_pages: int = 10) -> Dict[str, Any]:
        """
        Process a subject to discover age groups and extract resources for each age group.
        
        Args:
            subject_link: Dictionary with subject name and URL
            max_pages: Maximum number of pages to process per age group
            
        Returns:
            Dictionary with resources by age group
        """
        subject_name = subject_link["name"]
        subject_url = subject_link["url"]
        
        logger.info(f"Processing subject: {subject_name} at {subject_url}")
        
        # Discover available age groups
        age_groups = await self.discover_age_groups(subject_url)
        
        if not age_groups:
            logger.warning(f"No age groups found for {subject_name}. Using default.")
            # Using a specific age group range when no age groups found
            age_groups = [
                {
                    "name": "Years F-2",
                    "fragment": "years-f-2",
                    "url": f"{subject_url}#years-f-2",
                    "is_default": False
                },
                {
                    "name": "Years 3-4", 
                    "fragment": "years-3-4",
                    "url": f"{subject_url}#years-3-4",
                    "is_default": False
                },
                {
                    "name": "Years 5-6",
                    "fragment": "years-5-6",
                    "url": f"{subject_url}#years-5-6",
                    "is_default": False
                }
            ]
        
        # Filter out all-years age groups
        filtered_age_groups = [
            g for g in age_groups 
            if "all-years" not in g.get("fragment", "") and "all-years" not in g.get("url", "")
        ]
        
        logger.info(f"Found {len(filtered_age_groups)} specific age groups for {subject_name}: {[g['name'] for g in filtered_age_groups]}")
        
        # Process each age group
        result = {
            "subject_name": subject_name,
            "subject_url": subject_url,
            "age_groups": {},
            "all_resources": []
        }
        
        for age_group in filtered_age_groups:
            try:
                resources = await self.process_subject_age_group(subject_link, age_group, max_pages)
                
                # Add to the result structure
                result["age_groups"][age_group["name"]] = {
                    "resources": resources,
                    "count": len(resources)
                }
                
                # Add resources to the all_resources list, avoiding duplicates
                existing_urls = {r["url"] for r in result["all_resources"]}
                for resource in resources:
                    if resource["url"] not in existing_urls:
                        result["all_resources"].append(resource)
                        existing_urls.add(resource["url"])
                
                # Add a small delay between age groups
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Error processing age group {age_group['name']} for subject {subject_name}: {e}")
        
        # Save combined resources for all age groups
        self.save_resource_links_to_json(result["all_resources"], subject_name)
        
        return result
    
    async def create_resource_index(self) -> Dict[str, Any]:
        """
        Create a comprehensive index of all educational resources by subject and age group.
        
        Returns:
            Dictionary with index information
        """
        # Dictionary to hold the index
        index = {
            "created_at": datetime.now().isoformat(),
            "total_resources": 0,
            "subjects": {}
        }
        
        # Scan the output directory for resource files
        resource_files = [f for f in os.listdir(self.output_dir) if f.endswith('_resources.json')]
        
        for file in resource_files:
            try:
                # Extract subject and age group from filename
                file_parts = file.replace('_resources.json', '').split('_')
                subject_name = file_parts[0].replace('_', ' ')
                
                # Determine if this file is for a specific age group
                age_group = None
                if len(file_parts) > 1:
                    age_group = ' '.join(file_parts[1:]).replace('_', ' ')
                
                # Skip if all-years is in the age group
                if age_group and "all-years" in age_group.lower():
                    continue
                
                # Read the file
                with open(os.path.join(self.output_dir, file), 'r', encoding='utf-8') as f:
                    resources = json.load(f)
                
                # Add to index
                if subject_name not in index["subjects"]:
                    index["subjects"][subject_name] = {
                        "count": 0,
                        "age_groups": {},
                        "resources": []
                    }
                
                # If this is an age-specific file
                if age_group:
                    if age_group not in index["subjects"][subject_name]["age_groups"]:
                        index["subjects"][subject_name]["age_groups"][age_group] = {
                            "count": len(resources),
                            "resources": resources
                        }
                    else:
                        # Merge resources if age group already exists (avoiding duplicates)
                        existing_urls = {r["url"] for r in index["subjects"][subject_name]["age_groups"][age_group]["resources"]}
                        for resource in resources:
                            if resource["url"] not in existing_urls:
                                index["subjects"][subject_name]["age_groups"][age_group]["resources"].append(resource)
                                existing_urls.add(resource["url"])
                        
                        index["subjects"][subject_name]["age_groups"][age_group]["count"] = len(index["subjects"][subject_name]["age_groups"][age_group]["resources"])
                else:
                    # This is the combined file for all age groups
                    # Merge resources (avoiding duplicates)
                    existing_urls = {r["url"] for r in index["subjects"][subject_name]["resources"]}
                    for resource in resources:
                        if resource["url"] not in existing_urls:
                            index["subjects"][subject_name]["resources"].append(resource)
                            existing_urls.add(resource["url"])
                
                # Update subject count
                index["subjects"][subject_name]["count"] = len(index["subjects"][subject_name]["resources"])
                
            except Exception as e:
                logger.error(f"Error processing resource file {file}: {e}")
        
        # Calculate total resources across all subjects
        total = 0
        for subject in index["subjects"].values():
            total += subject["count"]
        
        index["total_resources"] = total
        
        # Save the complete index
        index_path = os.path.join(self.output_dir, "resource_index.json")
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)
            logger.info(f"Saved complete resource index to {index_path} with {total} resources")
        except Exception as e:
            logger.error(f"Error saving resource index: {e}")
        
        return index

async def run_indexer(subject_limit=None, headless=True, max_pages_per_subject=10):
    """
    Run the education resource indexer with age group support.
    
    Args:
        subject_limit: Maximum number of subjects to process (None for all)
        headless: Whether to run browser in headless mode
        max_pages_per_subject: Maximum pages to process per subject
        
    Returns:
        Dictionary with resource index
    """
    indexer = EducationResourceIndexer()
    
    try:
        # Setup browser
        await indexer.setup(headless=headless)
        
        # Get subjects to process
        subjects = SUBJECT_LINKS
        if subject_limit and isinstance(subject_limit, int) and subject_limit > 0:
            subjects = subjects[:subject_limit]
        
        logger.info(f"Starting indexer with {len(subjects)} subjects")
        
        # Process each subject
        all_results = {}
        for subject in subjects:
            try:
                subject_result = await indexer.process_subject(subject, max_pages=max_pages_per_subject)
                all_results[subject["name"]] = subject_result
                # Add a small delay between subjects
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Error processing subject {subject['name']}: {e}")
        
        # Create comprehensive resource index
        resource_index = await indexer.create_resource_index()
        
        logger.info(f"Indexing completed. Found {resource_index['total_resources']} resources across {len(subjects)} subjects")
        return resource_index
        
    except Exception as e:
        logger.error(f"Error running indexer: {e}")
        return {"error": str(e)}
        
    finally:
        # Clean up resources
        await indexer.teardown()

if __name__ == "__main__":
    # Run the indexer
    asyncio.run(run_indexer(
        subject_limit=2,  # Process 2 subjects for testing
        headless=False,  # Run with visible browser for debugging
        max_pages_per_subject=5  # Process up to 5 pages per subject
    ))