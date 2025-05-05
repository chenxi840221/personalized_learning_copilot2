#!/usr/bin/env python3
"""
Script to test learning plan creation with various conditions
"""

import asyncio
import sys
import os
import json
import logging

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.learning_plan import LearningPlan, ActivityStatus, LearningPeriod
from models.user import User, LearningStyle
from services.azure_learning_plan_service import get_learning_plan_service
from rag.generator import get_plan_generator
from api.learning_plan_routes import prepare_plan_for_response
from rag.retriever import retrieve_relevant_content
from scripts.add_fallback_content import get_fallback_content
from datetime import datetime, timedelta
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_learning_plan_creation():
    # Create a test user with minimal information
    user = User(
        id=str(uuid.uuid4()),
        username="test_user",
        email="test@example.com",
        full_name="Test User",
        grade_level=8,
        learning_style=LearningStyle.VISUAL,
        subjects_of_interest=["Mathematics", "Science", "English"],
        is_active=True
    )
    
    # Set up test subject and learning period
    subject = "Mathematics"
    learning_period = LearningPeriod.ONE_MONTH
    days = LearningPeriod.to_days(learning_period)
    activity_days = min(days, 14) if days > 14 else days
    
    # Calculate start and end dates
    now = datetime.utcnow()
    start_date = now
    end_date = now + timedelta(days=days)

    logger.info(f"Testing learning plan creation for subject: {subject}, period: {learning_period.value} ({days} days)")
    
    # Get relevant content - will include fallback content if none found
    try:
        relevant_content = await retrieve_relevant_content(
            student_profile=user,
            subject=subject,
            k=10
        )
        logger.info(f"Retrieved {len(relevant_content)} content items")
        
        # Check if we got content with duration_minutes
        has_duration = any(hasattr(content, 'duration_minutes') and content.duration_minutes is not None 
                          for content in relevant_content)
        logger.info(f"Has content with duration_minutes: {has_duration}")
        
        # If no content found or none have duration_minutes, use fallback
        if not relevant_content or not has_duration:
            logger.warning("Using fallback content")
            relevant_content = await get_fallback_content(subject)
            logger.info(f"Retrieved {len(relevant_content)} fallback content items")
        
        # Get plan generator
        plan_generator = await get_plan_generator()
        
        # Generate plan
        plan_dict = await plan_generator.generate_plan(
            student=user,
            subject=subject,
            relevant_content=relevant_content,
            days=activity_days
        )
        
        # Create learning plan object
        activities = plan_dict.get("activities", [])
        logger.info(f"Generated {len(activities)} activities")
        
        # Print activity durations
        for i, activity in enumerate(activities):
            duration = activity.get("duration_minutes")
            logger.info(f"Activity {i+1}: duration_minutes = {duration}")
        
        # Create learning plan object
        learning_plan = LearningPlan(
            id=str(uuid.uuid4()),
            student_id=user.id,
            title=plan_dict.get("title", f"{subject} Learning Plan"),
            description=plan_dict.get("description", f"A learning plan for {subject}"),
            subject=subject,
            topics=plan_dict.get("topics", [subject]),
            activities=[],  # Will be populated after post-processing
            status=ActivityStatus.NOT_STARTED,
            progress_percentage=0.0,
            created_at=now,
            updated_at=now,
            start_date=start_date,
            end_date=end_date,
            metadata={
                "learning_period": learning_period.value,
                "period_days": days,
                "activity_days": activity_days
            },
            owner_id=user.id
        )
        
        # Process the plan for response - this should populate activities for all days
        processed_plan = prepare_plan_for_response(learning_plan)
        
        # Count activities by day
        days_with_activities = {}
        for activity in processed_plan.activities:
            day = activity.day
            if day not in days_with_activities:
                days_with_activities[day] = []
            days_with_activities[day].append(activity)
        
        # Print statistics
        logger.info(f"Processed plan has {len(processed_plan.activities)} activities across {days} days")
        logger.info(f"Days with activities: {len(days_with_activities)}")
        
        # Print activities per day
        for day in range(1, days + 1):
            day_activities = days_with_activities.get(day, [])
            total_minutes = sum(a.duration_minutes or 0 for a in day_activities)
            logger.info(f"Day {day}: {len(day_activities)} activities, {total_minutes} minutes total")
        
        return True
    except Exception as e:
        logger.error(f"Error testing learning plan creation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    result = asyncio.run(test_learning_plan_creation())
    if result:
        print("\nSUCCESS: Learning plan creation test passed!")
    else:
        print("\nFAILURE: Learning plan creation test failed!")