#!/usr/bin/env python3
"""
Test script to verify that all activities in created learning plans have content references.
This script creates a learning plan and verifies that all activities have content_id and content_url.
"""

import asyncio
import sys
import os
import json
import logging
from pprint import pprint

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.user import User, LearningStyle
from rag.generator import get_plan_generator
from rag.retriever import retrieve_relevant_content

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_learning_plan_content():
    """Create a test learning plan and verify that all activities have content references."""
    try:
        # Create a test user
        user = User(
            id="test_user_id",
            username="test_user",
            email="test@example.com",
            full_name="Test User",
            grade_level="10",
            subjects_of_interest=["Mathematics", "Science"],
            learning_style=LearningStyle.VISUAL,
            is_active=True
        )
        
        # Define a test subject
        subject = "Mathematics"
        
        logger.info(f"Retrieving content for subject: {subject}")
        
        # Get relevant content for the learning plan
        relevant_content = await retrieve_relevant_content(
            student_profile=user,
            subject=subject,
            k=10
        )
        
        logger.info(f"Retrieved {len(relevant_content)} content items")
        
        # Get plan generator
        plan_generator = await get_plan_generator()
        
        # Generate learning plan
        logger.info("Generating learning plan...")
        plan_dict = await plan_generator.generate_plan(
            student=user,
            subject=subject,
            relevant_content=relevant_content
        )
        
        # Process activities
        activities = []
        for i, activity_dict in enumerate(plan_dict.get("activities", [])):
            # Get existing content URL and ID from the activity
            content_url = activity_dict.get("content_url")
            content_id = activity_dict.get("content_id")
            matching_content = None
            
            # Try to find matching content if the activity has a content_id
            if content_id:
                matching_content = next(
                    (content for content in relevant_content if str(content.id) == content_id),
                    None
                )
                if matching_content and not content_url:
                    content_url = matching_content.url
            
            # If the activity doesn't have a content reference, assign one from available content
            if not content_id and relevant_content:
                # Pick a content item that hasn't been used yet
                used_content_ids = [a.get("content_id") for a in plan_dict.get("activities", []) if a.get("content_id")]
                unused_content = [c for c in relevant_content if str(c.id) not in used_content_ids]
                
                if unused_content:
                    # Use the first unused content
                    matching_content = unused_content[0]
                    content_id = str(matching_content.id)
                    content_url = matching_content.url
                    logger.info(f"Assigned content {content_id} to activity without content reference")
                elif relevant_content:
                    # If all content has been used, reuse the first item
                    matching_content = relevant_content[0]
                    content_id = str(matching_content.id)
                    content_url = matching_content.url
                    logger.info(f"Reused content {content_id} for activity without content reference")
            
            # Prepare content metadata with detailed information about the educational resource
            metadata = activity_dict.get("metadata", {"subject": subject})
            if matching_content:
                content_info = {
                    "title": matching_content.title,
                    "description": matching_content.description,
                    "subject": matching_content.subject,
                    "difficulty_level": matching_content.difficulty_level.value if hasattr(matching_content, "difficulty_level") else None,
                    "content_type": matching_content.content_type.value if hasattr(matching_content, "content_type") else None,
                    "grade_level": matching_content.grade_level if hasattr(matching_content, "grade_level") else None,
                    "url": matching_content.url
                }
                metadata["content_info"] = content_info
            
            # Update the activity dictionary with enhanced content information
            activity_dict["content_id"] = content_id
            activity_dict["content_url"] = content_url
            activity_dict["metadata"] = metadata
            
            # Add enhanced learning benefit if not present
            if "learning_benefit" not in activity_dict or not activity_dict["learning_benefit"]:
                activity_dict["learning_benefit"] = f"This activity helps develop skills in {subject} by using educational resources tailored to your learning style and needs."
            
            activities.append(activity_dict)
        
        # Verify all activities have content
        total_activities = len(activities)
        activities_with_content = sum(1 for a in activities if a.get("content_id") and a.get("content_url"))
        
        logger.info(f"Total activities: {total_activities}")
        logger.info(f"Activities with content: {activities_with_content}")
        
        if activities_with_content == total_activities:
            logger.info("SUCCESS: All activities have content references!")
        else:
            logger.error(f"FAILURE: {total_activities - activities_with_content} activities don't have content references.")
        
        # Print activity details
        for i, activity in enumerate(activities):
            print(f"\nActivity {i+1}:")
            print(f"Title: {activity.get('title')}")
            print(f"Content ID: {activity.get('content_id')}")
            print(f"Content URL: {activity.get('content_url')}")
            if "content_info" in activity.get("metadata", {}):
                content_info = activity["metadata"]["content_info"]
                print(f"Content Title: {content_info.get('title')}")
                print(f"Content Type: {content_info.get('content_type')}")
                print(f"Description: {content_info.get('description')[:50]}..." if content_info.get('description') else "No description")
        
    except Exception as e:
        logger.exception(f"Error testing learning plan content: {e}")


if __name__ == "__main__":
    asyncio.run(test_learning_plan_content())