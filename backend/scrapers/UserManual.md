User Manual: Two-Step Education Resource Scraper
Introduction
The Two-Step Education Resource Scraper is a comprehensive tool designed to collect educational content from the ABC Education website. It extracts content organized by subject and age group, processes it, and prepares it for use in the Personalized Learning Co-pilot system.
This manual explains how to set up, configure, and run the scraper effectively for various use cases.
System Requirements
•	Python: Version 3.8 or higher
•	Memory: Minimum 4GB RAM (8GB recommended)
•	Disk Space: At least 1GB free space for content storage
•	Network: Stable internet connection
•	Operating System: Windows, macOS, or Linux
•	Azure Services: OpenAI API access and AI Search service for content embedding and storage
Installation Process
Step 1: Clone the Repository
bash
git clone https://github.com/yourusername/personalized-learning-copilot.git
cd personalized-learning-copilot
Step 2: Set Up Python Environment
It's recommended to use a virtual environment:
bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Step 3: Install Dependencies
bash
pip install -r requirements.txt
Step 4: Install Playwright Browsers
Playwright is used for web automation and requires browser installation:
bash
python -m playwright install chromium
Step 5: Configure Environment Variables
Create a .env file in the project root with your Azure credentials:
AZURE_OPENAI_ENDPOINT=https://your-openai-service.openai.azure.com/
AZURE_OPENAI_KEY=your-openai-key
AZURE_OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_KEY=your-search-key
AZURE_SEARCH_INDEX_NAME=educational-content
Running the Scraper
The scraper operates in two steps:
1.	Indexing: Discovers resources on the ABC Education website
2.	Extraction: Processes and extracts content from these resources
You can run both steps together or separately.
Basic Usage
To run the complete process:
bash
python backend/scrapers/two_step_scraper.py
This will run both indexing and extraction steps for all subjects in headless mode.
Command-Line Options
The scraper provides several command-line options for customization:
Option	Description
--step	Which step to run: 'index', 'extract', or 'both' (default)
--subject-limit	Maximum number of subjects to process
--resource-limit	Maximum number of resources per subject/age group
--visible	Run with visible browser (not headless)
--max-pages	Maximum pages to process per subject (default: 10)
Common Use Cases
Quick Test Run
For testing if the scraper is working correctly:
bash
python backend/scrapers/two_step_scraper.py --step both --subject-limit 1 --resource-limit 3 --visible
This processes just one subject with three resources per age group, with visible browser.
Production Run
For a complete run on a server:
bash
python backend/scrapers/two_step_scraper.py --step both
Indexing Only
To update the resource index without extracting content:
bash
python backend/scrapers/two_step_scraper.py --step index
Extraction Only
To process previously indexed resources:
bash
python backend/scrapers/two_step_scraper.py --step extract
Debugging Issues
For troubleshooting with visible browser:
bash
python backend/scrapers/two_step_scraper.py --step both --subject-limit 1 --visible
Output and Results
The scraper generates several output files and directories:
Main Output Directory
•	education_resources/: Main directory for all scraped content 
o	resource_index.json: Complete index of all discovered resources
o	[Subject]_resources.json: Resources for each subject
o	[Subject]_[Age_Group]_resources.json: Resources for specific age groups
o	extracted_content/: Directory containing processed content
Debug Information
•	debug_output/: Contains debugging information 
o	Screenshots of webpages during scraping
o	HTML dumps for troubleshooting
o	Named with timestamps for tracking
Log Files
•	edu_indexer.log: Log for the indexing step
•	content_extractor.log: Log for the extraction step
•	two_step_scraper.log: Overall scraper log
Understanding the Resource Index
The resource_index.json file is structured as follows:
json
{
  "created_at": "2023-06-01T10:15:30.123456",
  "total_resources": 250,
  "subjects": {
    "Mathematics": {
      "count": 80,
      "age_groups": {
        "Years F-2": {
          "count": 25,
          "resources": [...]
        },
        "Years 3-4": {
          "count": 30,
          "resources": [...]
        },
        ...
      },
      "resources": [...]
    },
    "Science": {
      ...
    }
  }
}
Each resource contains:
•	Title
•	URL
•	Subject
•	Age group
•	Additional metadata
Troubleshooting
Common Issues
No Resources Found
If the scraper finds no resources:
1.	Check internet connection
2.	Verify the ABC Education website is accessible
3.	Run with --visible to observe the browser behavior
4.	Check the log files for specific errors
Extraction Failures
If content extraction fails:
1.	Review the error messages in content_extractor.log
2.	Check if your Azure OpenAI credentials are correct
3.	Try running with a smaller --resource-limit to identify problematic resources
Browser Crashes
If the browser crashes:
1.	Ensure sufficient system memory
2.	Update Playwright: pip install --upgrade playwright
3.	Reinstall browser: python -m playwright install chromium
Advanced Debugging
For more detailed debugging:
bash
# Run with verbose logging
python -m backend.scrapers.two_step_scraper --step both --subject-limit 1 --visible --debug
Scheduling Automated Runs
Setting Up a Cron Job (Linux/macOS)
To run the scraper automatically, add a cron job:
bash
# Edit crontab
crontab -e

# Add line to run daily at 2 AM
0 2 * * * cd /path/to/personalized-learning-copilot && /path/to/python /path/to/personalized-learning-copilot/backend/scrapers/two_step_scraper.py --step both > /path/to/logs/scraper_$(date +\%Y\%m\%d).log 2>&1
Windows Task Scheduler
1.	Open Task Scheduler
2.	Create a Basic Task
3.	Set trigger (e.g., daily at 2 AM)
4.	Action: Start a program
5.	Program/script: C:\path\to\python.exe
6.	Arguments: C:\path\to\personalized-learning-copilot\backend\scrapers\two_step_scraper.py --step both
Best Practices
1.	Incremental Updates: Run indexing more frequently than full extraction
2.	Resource Limits: Start with small limits when testing new subjects
3.	Headless Mode: Use headless mode for production runs
4.	Backup: Regularly back up your resource_index.json file
5.	Rate Limiting: Be respectful of the ABC Education website by not running the scraper too frequently
Age Group Handling
The scraper specifically focuses on structured age groups (like "Years F-2", "Years 3-4", etc.) and excludes generic "All Years" content. This approach ensures that content recommendations are properly tailored to specific student grade levels.
Support and Maintenance
Regularly check for updates to the scraper code, as the ABC Education website structure may change over time. If the website changes significantly, the selectors in the scraper code may need to be updated.
For assistance, contact the development team or raise an issue on the project's GitHub repository.

