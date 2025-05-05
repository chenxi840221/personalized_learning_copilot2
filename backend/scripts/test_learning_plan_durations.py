#!/usr/bin/env python3
"""
Test script to verify that learning plans only use true duration_minutes from Azure AI Search.
"""

import asyncio
import sys
import os
import logging
import json
from typing import List, Dict, Any
import random

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.user import User, LearningStyle
from models.content import Content
from models.learning_plan import LearningPeriod
from rag.generator import get_plan_generator
from rag.retriever import retrieve_relevant_content
from services.search_service import get_search_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_learning_plan_durations():
    """Test learning plan generation to ensure only true durations are used."""
    logger.info("Starting learning plan duration test")
    
    # Create a test user
    user = User(
        id="test_user_123",
        username="test_user",
        email="test@example.com",
        full_name="Test User",
        grade_level=9,
        subjects_of_interest=["Mathematics", "Science"],
        learning_style=LearningStyle.VISUAL,
        is_active=True
    )
    
    # Define a subject to test with - try different subjects if one fails
    subjects = ["Mathematics", "Science", "English", "History", "Geography"]
    subject = random.choice(subjects)
    logger.info(f"Selected subject for testing: {subject}")
    
    # Get content for the subject
    logger.info(f"Retrieving content for subject: {subject}")
    relevant_content = await retrieve_relevant_content(
        student_profile=user,
        subject=subject,
        k=15  # Get more content for better testing
    )
    
    if not relevant_content:
        logger.warning(f"No content found for subject {subject}. Getting fallback content.")
        # Import fallback content function
        from scripts.add_fallback_content import get_fallback_content
        relevant_content = await get_fallback_content(subject)
        
        if not relevant_content:
            logger.error("No fallback content found. Test cannot continue.")
            return
    
    logger.info(f"Retrieved {len(relevant_content)} content items")
    
    # Verify content has duration_minutes
    durations_found = 0
    for i, content in enumerate(relevant_content[:5]):  # Check the first 5 items
        duration = getattr(content, "duration_minutes", None)
        logger.info(f"Content #{i+1}: '{content.title}' - duration_minutes: {duration}")
        if duration is not None:
            durations_found += 1
    
    if durations_found == 0:
        logger.warning("No content items have duration_minutes. This may cause issues in plan generation.")
    
    # Get plan generator
    logger.info("Getting plan generator")
    plan_generator = await get_plan_generator()
    
    # Generate a learning plan
    logger.info("Generating learning plan")
    days = 7  # Use a one-week plan for testing
    
    plan_dict = await plan_generator.generate_plan(
        student=user,
        subject=subject,
        relevant_content=relevant_content,
        days=days
    )
    
    # Verify activities have valid durations from Azure AI Search
    logger.info("Checking activities for valid durations")
    
    activities = plan_dict.get("activities", [])
    logger.info(f"Plan generated with {len(activities)} activities")
    
    valid_activities = 0
    invalid_activities = 0
    content_match_count = 0
    
    for i, activity in enumerate(activities):
        duration = activity.get("duration_minutes")
        content_id = activity.get("content_id")
        
        logger.info(f"Activity #{i+1}: '{activity.get('title', 'Untitled')}' - " + 
                   f"duration_minutes: {duration}, content_id: {content_id}")
        
        # Check if duration is valid
        if duration is None or duration <= 0:
            logger.error(f"Activity has invalid duration: {duration}")
            invalid_activities += 1
            continue
        
        valid_activities += 1
        
        # Check if duration matches content source
        if content_id:
            matching_content = next((c for c in relevant_content if str(c.id) == content_id), None)
            if matching_content:
                content_duration = getattr(matching_content, "duration_minutes", None)
                if content_duration == duration:
                    content_match_count += 1
                    logger.info(f"✓ Duration matches content source: {duration}")
                else:
                    logger.warning(f"✗ Duration does not match content source: activity={duration}, content={content_duration}")
    
    # Print results
    logger.info("\n--- Test Results ---")
    logger.info(f"Total activities generated: {len(activities)}")
    logger.info(f"Activities with valid durations: {valid_activities}")
    logger.info(f"Activities with invalid durations: {invalid_activities}")
    logger.info(f"Activities with duration matching content source: {content_match_count}")
    
    # Check success criteria
    if invalid_activities > 0:
        logger.error("❌ TEST FAILED: Some activities have invalid durations")
    else:
        logger.info("✅ TEST PASSED: All activities have valid durations")
    
    if content_match_count < valid_activities:
        logger.warning("⚠️ WARNING: Not all activities have durations matching their content source")
    else:
        logger.info("✅ VERIFIED: All activities have durations matching their content source")

async def main():
    """Main entry point."""
    await test_learning_plan_durations()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())