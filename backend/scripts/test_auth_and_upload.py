#!/usr/bin/env python
# backend/scripts/test_auth_and_upload.py
import asyncio
import aiohttp
import json
import os
import logging
from urllib.parse import urlencode
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API URL - change to your local server
API_URL = "http://localhost:8001"

async def get_test_token():
    """Get a test access token."""
    url = f"{API_URL}/auth/test-token"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Error getting test token: {response.status}")
                    logger.error(await response.text())
                    return None
                    
                data = await response.json()
                logger.info("Successfully obtained test token")
                return data["access_token"]
        except Exception as e:
            logger.error(f"Error getting test token: {e}")
            return None

async def login(username="testuser", password="password"):
    """Get access token using username/password."""
    url = f"{API_URL}/auth/token"
    
    # Prepare form data
    data = {
        "username": username,
        "password": password
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, data=data) as response:
                if response.status != 200:
                    logger.error(f"Error logging in: {response.status}")
                    logger.error(await response.text())
                    return None
                    
                data = await response.json()
                logger.info("Successfully logged in")
                return data["access_token"]
        except Exception as e:
            logger.error(f"Error logging in: {e}")
            return None

async def get_current_user(token):
    """Get current user profile using token."""
    url = f"{API_URL}/users/me"
    
    # Prepare headers with token
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Error getting user profile: {response.status}")
                    logger.error(await response.text())
                    return None
                    
                data = await response.json()
                logger.info(f"Current user: {data}")
                return data
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None

async def upload_report(token, file_path):
    """Upload a student report."""
    url = f"{API_URL}/student-reports/upload"
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
        
    # Prepare headers with token
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Prepare form data with file
    data = aiohttp.FormData()
    data.add_field(
        "file", 
        open(file_path, "rb"), 
        filename=os.path.basename(file_path), 
        content_type="application/pdf"
    )
    data.add_field("report_type", "primary")
    
    async with aiohttp.ClientSession() as session:
        try:
            start_time = time.time()
            async with session.post(url, headers=headers, data=data) as response:
                elapsed_time = time.time() - start_time
                if response.status != 200:
                    logger.error(f"Error uploading report: {response.status}")
                    logger.error(await response.text())
                    return None
                    
                data = await response.json()
                logger.info(f"Report uploaded successfully in {elapsed_time:.2f} seconds")
                return data
        except Exception as e:
            logger.error(f"Error uploading report: {e}")
            return None

async def main():
    """Main test function."""
    # Get test token
    logger.info("Getting test token...")
    token = await get_test_token()
    if not token:
        logger.error("Failed to get test token. Trying login...")
        token = await login()
        
    if not token:
        logger.error("Authentication failed. Exiting.")
        return
        
    # Get current user
    logger.info("Getting current user profile...")
    current_user = await get_current_user(token)
    if not current_user:
        logger.error("Failed to get current user profile. Exiting.")
        return
        
    # Upload a report
    logger.info("Uploading a sample report...")
    # You'll need to provide a sample PDF file path
    sample_file = "../education_resources/sample_student_report.pdf"
    
    # If sample file doesn't exist, exit
    if not os.path.exists(sample_file):
        logger.error(f"Sample report file not found: {sample_file}")
        logger.error("Please provide a valid sample report PDF file path.")
        return
        
    result = await upload_report(token, sample_file)
    if result:
        logger.info(f"Upload successful. Report ID: {result.get('id')}")
    else:
        logger.error("Report upload failed.")

if __name__ == "__main__":
    asyncio.run(main())