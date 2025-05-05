#!/usr/bin/env python3
"""
Test script for measuring learning plan generation times across different subjects.
This helps identify optimal timeouts for the frontend and backend.
"""
import asyncio
import logging
import time
import json
import os
import sys
from datetime import datetime
import uuid
import statistics

# Fix import paths for relative imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import necessary modules
from models.user import User, LearningStyle
from models.learning_plan import LearningPeriod
from rag.generator import get_plan_generator
from rag.retriever import retrieve_relevant_content
from services.azure_learning_plan_service import get_learning_plan_service

# List of subjects to test
TEST_SUBJECTS = [
    "Mathematics", 
    "Science", 
    "English", 
    "History", 
    "Geography", 
    "Art", 
    "Music",
    "Computer Science",
    "Physical Education"
]

# Different learning periods to test
TEST_PERIODS = [
    LearningPeriod.ONE_WEEK,
    LearningPeriod.TWO_WEEKS,
    LearningPeriod.ONE_MONTH
]

# Create a test user
def create_test_user():
    return User(
        id=str(uuid.uuid4()),
        username="test_user",
        email="test@example.com",
        full_name="Test User",
        grade_level=8,
        subjects_of_interest=["Mathematics", "Science", "Computer Science"],
        learning_style=LearningStyle.VISUAL,
        is_active=True
    )

async def test_learning_plan_generation(subject, learning_period, user):
    """
    Test the generation of a learning plan for a specific subject and period.
    
    Args:
        subject: Subject for the learning plan
        learning_period: Learning period enum value
        user: User object
        
    Returns:
        Tuple of (success, time_taken, plan_id)
    """
    start_time = time.time()
    
    try:
        logger.info(f"Testing learning plan generation for subject: {subject}, period: {learning_period.value}")
        
        # Get plan generator
        plan_generator = await get_plan_generator()
        
        # Get relevant content
        logger.info(f"Retrieving content for {subject}")
        content_start = time.time()
        relevant_content = await retrieve_relevant_content(
            student_profile=user,
            subject=subject,
            k=15  # Get more content to ensure we have enough for all activities
        )
        content_time = time.time() - content_start
        logger.info(f"Content retrieval took {content_time:.2f} seconds, found {len(relevant_content)} items")
        
        # If we got no results, try the fallback content
        if not relevant_content:
            logger.warning(f"No content found for {subject}, using fallback content")
            from scripts.add_fallback_content import get_fallback_content
            relevant_content = get_fallback_content(subject)
            
        # Calculate days based on learning period
        days = LearningPeriod.to_days(learning_period)
        weeks_in_period = (days + 6) // 7  # Ceiling division to get full weeks
        
        # Generate a plan for each week of the learning period
        all_activities = []
        generation_time = 0
        
        logger.info(f"Generating plan with {weeks_in_period} weeks for period: {learning_period.value} ({days} days)")
        for week_num in range(weeks_in_period):
            week_start = time.time()
            week_plan_dict = await plan_generator.generate_plan(
                student=user,
                subject=subject,
                relevant_content=relevant_content,
                days=7,  # Always use 7 days for a weekly plan
                is_weekly_plan=True
            )
            week_time = time.time() - week_start
            generation_time += week_time
            
            # Adjust day numbers to be relative to the entire learning period
            week_activities = week_plan_dict.get("activities", [])
            for activity in week_activities:
                activity["day"] = activity["day"] + (week_num * 7)
                all_activities.append(activity)
            
            logger.info(f"Week {week_num+1} generation took {week_time:.2f} seconds, created {len(week_activities)} activities")
        
        # Create the final plan
        now = datetime.utcnow()
        plan_id = str(uuid.uuid4())
        
        # Create metadata with learning period
        metadata = {
            "learning_period": learning_period.value,
            "period_days": days,
            "weeks_in_period": weeks_in_period,
            "activity_days": days  # Now we create activities for all days
        }
        
        # Create the learning plan object
        from models.learning_plan import LearningPlan, ActivityStatus, LearningActivity
        
        learning_plan = LearningPlan(
            id=plan_id,
            student_id=user.id,
            title=f"{subject} Learning Plan for {learning_period.value.replace('_', ' ').title()}",
            description=f"A {learning_period.value.replace('_', ' ')} learning plan for {subject}",
            subject=subject,
            topics=[subject],
            activities=[LearningActivity(**activity) for activity in all_activities],
            status=ActivityStatus.NOT_STARTED,
            progress_percentage=0.0,
            created_at=now,
            updated_at=now,
            start_date=now,
            end_date=now,
            metadata=metadata,
            owner_id=user.id
        )
        
        # Save the plan
        save_start = time.time()
        learning_plan_service = await get_learning_plan_service()
        success = await learning_plan_service.create_learning_plan(learning_plan)
        save_time = time.time() - save_start
        
        # Calculate total time
        end_time = time.time()
        total_time = end_time - start_time
        
        result = {
            "subject": subject,
            "learning_period": learning_period.value,
            "weeks": weeks_in_period,
            "activities": len(all_activities),
            "content_retrieval_time": content_time,
            "plan_generation_time": generation_time,
            "save_time": save_time,
            "total_time": total_time,
            "success": success,
            "plan_id": plan_id if success else None
        }
        
        logger.info(f"Plan generation completed in {total_time:.2f} seconds: {success}")
        return result
        
    except Exception as e:
        end_time = time.time()
        total_time = end_time - start_time
        
        logger.error(f"Error generating plan for {subject}: {e}")
        return {
            "subject": subject,
            "learning_period": learning_period.value,
            "error": str(e),
            "total_time": total_time,
            "success": False,
            "plan_id": None
        }

async def run_tests():
    """Run the learning plan generation tests for all subjects and periods."""
    # Create a test user
    user = create_test_user()
    
    # Store all test results
    results = []
    
    # Test all subjects with all periods
    for subject in TEST_SUBJECTS:
        for period in TEST_PERIODS:
            result = await test_learning_plan_generation(subject, period, user)
            results.append(result)
            
            # Add a small delay to avoid overloading the system
            await asyncio.sleep(2)
    
    # Calculate and display summary statistics
    successful_times = [r["total_time"] for r in results if r["success"]]
    if successful_times:
        avg_time = statistics.mean(successful_times)
        max_time = max(successful_times)
        min_time = min(successful_times)
        p95_time = sorted(successful_times)[int(len(successful_times) * 0.95)]
        
        logger.info("=== TIMING SUMMARY ===")
        logger.info(f"Total tests: {len(results)}")
        logger.info(f"Successful tests: {len(successful_times)}")
        logger.info(f"Average time: {avg_time:.2f} seconds")
        logger.info(f"Min time: {min_time:.2f} seconds")
        logger.info(f"Max time: {max_time:.2f} seconds")
        logger.info(f"95th percentile: {p95_time:.2f} seconds")
        logger.info(f"Recommended frontend timeout: {max(300000, int(p95_time * 1.5 * 1000))} ms")
    
    # Save results to a JSON file
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "learning_plan_timing_results.json")
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info(f"Results saved to {output_file}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_tests())