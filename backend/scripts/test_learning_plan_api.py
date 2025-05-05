#!/usr/bin/env python3
"""
Test script to call the learning plan API and verify content references in activities.
"""

import asyncio
import sys
import os
import json
import logging
import requests

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API base URL (assuming the backend server is running locally)
API_BASE_URL = "http://localhost:8001"

# Test user credentials from the fake_users_db in simple_auth.py
USERNAME = "test-user-123"
PASSWORD = "testpassword"


def login():
    """Login to get an access token."""
    login_url = f"{API_BASE_URL}/auth/token"
    payload = {"username": USERNAME, "password": PASSWORD}
    
    try:
        response = requests.post(login_url, json=payload)
        response.raise_for_status()
        
        token_data = response.json()
        logger.info("Login successful")
        return token_data.get("access_token")
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return None


def create_learning_plan(token, subject="Science"):
    """Create a learning plan and return the response."""
    url = f"{API_BASE_URL}/learning-plans/"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"subject": subject}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        learning_plan = response.json()
        logger.info(f"Created learning plan with ID: {learning_plan.get('id')}")
        return learning_plan
    except Exception as e:
        logger.error(f"Failed to create learning plan: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response content: {e.response.text}")
        return None


def verify_learning_plan_content(learning_plan):
    """Verify that all activities in the learning plan have content references."""
    if not learning_plan:
        logger.error("No learning plan provided for verification")
        return False
    
    activities = learning_plan.get("activities", [])
    total_activities = len(activities)
    
    if total_activities == 0:
        logger.warning("Learning plan has no activities")
        return False
    
    activities_with_content = sum(1 for a in activities if a.get("content_id") and a.get("content_url"))
    
    logger.info(f"Total activities: {total_activities}")
    logger.info(f"Activities with content: {activities_with_content}")
    
    if activities_with_content == total_activities:
        logger.info("SUCCESS: All activities have content references!")
        return True
    else:
        logger.error(f"FAILURE: {total_activities - activities_with_content} activities don't have content references.")
        
        # Print details of activities without content
        for i, activity in enumerate(activities):
            if not activity.get("content_id") or not activity.get("content_url"):
                logger.error(f"Activity {i+1} is missing content reference:")
                logger.error(f"Title: {activity.get('title')}")
                logger.error(f"Content ID: {activity.get('content_id')}")
                logger.error(f"Content URL: {activity.get('content_url')}")
        
        return False


def main():
    """Main test function."""
    # Login
    token = login()
    if not token:
        logger.error("Authentication failed. Cannot proceed with tests.")
        return
    
    # Create learning plan
    plan = create_learning_plan(token, subject="English")
    
    # Verify content in learning plan activities
    if plan:
        success = verify_learning_plan_content(plan)
        
        # Print more details about the activities
        print("\nActivity Details:")
        for i, activity in enumerate(plan.get("activities", [])):
            print(f"\nActivity {i+1}:")
            print(f"Title: {activity.get('title')}")
            print(f"Description: {activity.get('description')[:50]}..." if activity.get('description') else "No description")
            print(f"Content ID: {activity.get('content_id')}")
            print(f"Content URL: {activity.get('content_url')}")
            print(f"Learning Benefit: {activity.get('learning_benefit')[:50]}..." if activity.get('learning_benefit') else "No learning benefit")
            
            # Print content metadata if available
            metadata = activity.get("metadata", {})
            if metadata.get("content_info"):
                content_info = metadata["content_info"]
                print("Content Info:")
                print(f"  - Title: {content_info.get('title')}")
                print(f"  - Type: {content_info.get('content_type')}")
                print(f"  - Subject: {content_info.get('subject')}")
                print(f"  - URL: {content_info.get('url')}")
    else:
        logger.error("Failed to create learning plan for testing.")


if __name__ == "__main__":
    main()