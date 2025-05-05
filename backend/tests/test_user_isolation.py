"""
Test script to verify user isolation for student reports, profiles, and learning plans.

This script tests that users can only access resources they own.
"""

import os
import sys
import asyncio
import logging
import uuid
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import from the backend
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from services.search_service import get_search_service
# We'll use our mock users directly instead of importing from auth
# from auth.entra_auth import get_current_user
from models.student_report import StudentReport, ReportType, Subject
from models.learning_plan import LearningPlan, LearningActivity, ActivityStatus

# Mock users for testing
USER1 = {
    "id": str(uuid.uuid4()),
    "username": "teacher1",
    "email": "teacher1@example.com"
}

USER2 = {
    "id": str(uuid.uuid4()),
    "username": "teacher2",
    "email": "teacher2@example.com"
}

async def create_test_report(owner_id: str, name_suffix: str = "") -> str:
    """Create a test student report owned by the specified user."""
    logger.info(f"Creating test report for owner {owner_id}")
    
    # Create a student report
    # Create a student report without encrypted_fields
    # Since we're creating a simplified version for testing
    report_id = str(uuid.uuid4())
    report_data = {
        "id": report_id,
        "student_id": str(uuid.uuid4()),
        "student_name": f"Test Student {name_suffix}",
        "report_type": "PRIMARY",
        "school_name": f"Test School {name_suffix}",
        "school_year": "2024",
        "term": "S1",
        "grade_level": 5,
        "teacher_name": f"Teacher {name_suffix}",
        "general_comments": "Overall good progress",
        "subjects": [
            {
                "name": f"Math {name_suffix}",
                "grade": "A",
                "comments": "Good progress",
                "strengths": ["Problem solving", "Multiplication"],
                "areas_for_improvement": ["Division"]
            }
        ],
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "owner_id": owner_id
    }
    
    # Add the report to the search index
    search_service = await get_search_service()
    success = await search_service.index_document(
        index_name="student-reports",
        document=report_data
    )
    
    if success:
        logger.info(f"Created test report {report_id} for owner {owner_id}")
        return report_id
    else:
        logger.error(f"Failed to create test report for owner {owner_id}")
        return None

async def create_test_profile(owner_id: str, name_suffix: str = "") -> str:
    """Create a test student profile owned by the specified user."""
    logger.info(f"Creating test profile for owner {owner_id}")
    
    # Create a student profile
    profile_id = str(uuid.uuid4())
    profile = {
        "id": profile_id,
        "full_name": f"Test Student Profile {name_suffix}",
        "grade_level": 5,
        "gender": "female",
        "learning_style": "visual",
        "school_name": f"Test School {name_suffix}",
        "teacher_name": f"Teacher {name_suffix}",
        "strengths": ["Math", "Science"],
        "interests": ["Reading", "Art"],
        "areas_for_improvement": ["Writing", "History"],
        "current_school_year": "2024",
        "current_term": "S1",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "owner_id": owner_id
    }
    
    # Add the profile to the search index
    search_service = await get_search_service()
    success = await search_service.index_document(
        index_name="student-profiles",
        document=profile
    )
    
    if success:
        logger.info(f"Created test profile {profile_id} for owner {owner_id}")
        return profile_id
    else:
        logger.error(f"Failed to create test profile for owner {owner_id}")
        return None

async def create_test_learning_plan(owner_id: str, name_suffix: str = "") -> str:
    """Create a test learning plan owned by the specified user."""
    logger.info(f"Creating test learning plan for owner {owner_id}")
    
    # Create a learning plan
    plan = LearningPlan(
        id=str(uuid.uuid4()),
        student_id=str(uuid.uuid4()),
        title=f"Test Learning Plan {name_suffix}",
        description=f"Test learning plan description {name_suffix}",
        subject=f"Math {name_suffix}",
        topics=["Addition", "Subtraction"],
        activities=[
            LearningActivity(
                id=str(uuid.uuid4()),
                title=f"Activity 1 {name_suffix}",
                description="Test activity",
                duration_minutes=30,
                order=1,
                status=ActivityStatus.NOT_STARTED
            )
        ],
        status=ActivityStatus.NOT_STARTED,
        progress_percentage=0.0,
        owner_id=owner_id
    )
    
    # Convert to dict for indexing
    plan_dict = plan.dict()
    
    # Store activities as a JSON string for Azure Search
    activities_json = []
    for activity in plan.activities:
        activity_dict = activity.dict()
        activities_json.append(activity_dict)
    
    plan_dict["activities_json"] = json.dumps(activities_json)
    
    # Remove the original activities field
    if "activities" in plan_dict:
        del plan_dict["activities"]
    
    # Add the plan to the search index
    search_service = await get_search_service()
    success = await search_service.index_document(
        index_name="learning-plans",
        document=plan_dict
    )
    
    if success:
        logger.info(f"Created test learning plan {plan.id} for owner {owner_id}")
        return plan.id
    else:
        logger.error(f"Failed to create test learning plan for owner {owner_id}")
        return None

async def test_report_isolation(user1_id: str, user2_id: str, report1_id: str, report2_id: str):
    """Test that users can only access their own reports."""
    logger.info("Testing student report isolation...")
    search_service = await get_search_service()
    
    # Debug: Query all reports to make sure they exist
    all_reports = await search_service.search_documents(
        index_name="student-reports",
        query="*"
    )
    
    logger.info(f"Total reports in index: {len(all_reports)}")
    all_report_ids = [r["id"] for r in all_reports]
    logger.info(f"All report IDs: {all_report_ids}")
    all_report_owner_ids = [r.get("owner_id") for r in all_reports]
    logger.info(f"All report owner IDs: {all_report_owner_ids}")
    
    # Test that user1 can see their report but not user2's report using owner_id
    user1_reports = await search_service.search_documents(
        index_name="student-reports",
        query="*",
        owner_id=user1_id
    )
    
    logger.info(f"User1 can see {len(user1_reports)} reports")
    
    user1_report_ids = [r["id"] for r in user1_reports]
    assert report1_id in user1_report_ids, f"User1 should be able to see their own report {report1_id}"
    assert report2_id not in user1_report_ids, f"User1 should not be able to see user2's report {report2_id}"
    
    # Test that user2 can see their report but not user1's report using owner_id
    user2_reports = await search_service.search_documents(
        index_name="student-reports",
        query="*",
        owner_id=user2_id
    )
    
    logger.info(f"User2 can see {len(user2_reports)} reports")
    
    user2_report_ids = [r["id"] for r in user2_reports]
    assert report2_id in user2_report_ids, f"User2 should be able to see their own report {report2_id}"
    assert report1_id not in user2_report_ids, f"User2 should not be able to see user1's report {report1_id}"
    
    logger.info("Student report isolation test passed!")

async def test_profile_isolation(user1_id: str, user2_id: str, profile1_id: str, profile2_id: str):
    """Test that users can only access their own profiles."""
    logger.info("Testing student profile isolation...")
    search_service = await get_search_service()
    
    # Debug: Query all profiles to make sure they exist
    all_profiles = await search_service.search_documents(
        index_name="student-profiles",
        query="*"
    )
    
    logger.info(f"Total profiles in index: {len(all_profiles)}")
    all_profile_ids = [p["id"] for p in all_profiles]
    logger.info(f"All profile IDs: {all_profile_ids}")
    
    # Get profiles for first user directly by owner_id parameter
    user1_profiles = await search_service.search_documents(
        index_name="student-profiles",
        query="*",
        owner_id=user1_id
    )
    
    logger.info(f"User1 can see {len(user1_profiles)} profiles")
    
    user1_profile_ids = [p["id"] for p in user1_profiles]
    assert profile1_id in user1_profile_ids, f"User1 should be able to see their own profile {profile1_id}"
    assert profile2_id not in user1_profile_ids, f"User1 should not be able to see user2's profile {profile2_id}"
    
    # Get profiles for second user directly by owner_id parameter  
    user2_profiles = await search_service.search_documents(
        index_name="student-profiles",
        query="*",
        owner_id=user2_id
    )
    
    logger.info(f"User2 can see {len(user2_profiles)} profiles")
    
    user2_profile_ids = [p["id"] for p in user2_profiles]
    assert profile2_id in user2_profile_ids, f"User2 should be able to see their own profile {profile2_id}"
    assert profile1_id not in user2_profile_ids, f"User2 should not be able to see user1's profile {profile1_id}"
    
    logger.info("Student profile isolation test passed!")

async def test_learning_plan_isolation(user1_id: str, user2_id: str, plan1_id: str, plan2_id: str):
    """Test that users can only access their own learning plans."""
    logger.info("Testing learning plan isolation...")
    search_service = await get_search_service()
    
    # Debug: Query all plans to make sure they exist
    all_plans = await search_service.search_documents(
        index_name="learning-plans",
        query="*"
    )
    
    logger.info(f"Total plans in index: {len(all_plans)}")
    all_plan_ids = [p["id"] for p in all_plans]
    logger.info(f"All plan IDs: {all_plan_ids}")
    
    # Get plans for first user directly by owner_id parameter
    user1_plans = await search_service.search_documents(
        index_name="learning-plans",
        query="*",
        owner_id=user1_id
    )
    
    logger.info(f"User1 can see {len(user1_plans)} learning plans")
    
    user1_plan_ids = [p["id"] for p in user1_plans]
    assert plan1_id in user1_plan_ids, f"User1 should be able to see their own learning plan {plan1_id}"
    assert plan2_id not in user1_plan_ids, f"User1 should not be able to see user2's learning plan {plan2_id}"
    
    # Get plans for second user directly by owner_id parameter
    user2_plans = await search_service.search_documents(
        index_name="learning-plans",
        query="*",
        owner_id=user2_id
    )
    
    logger.info(f"User2 can see {len(user2_plans)} learning plans")
    
    user2_plan_ids = [p["id"] for p in user2_plans]
    assert plan2_id in user2_plan_ids, f"User2 should be able to see their own learning plan {plan2_id}"
    assert plan1_id not in user2_plan_ids, f"User2 should not be able to see user1's learning plan {plan1_id}"
    
    logger.info("Learning plan isolation test passed!")

async def cleanup_test_data(report1_id: str, report2_id: str, profile1_id: str, profile2_id: str, plan1_id: str, plan2_id: str):
    """Clean up test data."""
    logger.info("Cleaning up test data...")
    search_service = await get_search_service()
    
    # Delete test reports
    for report_id in [report1_id, report2_id]:
        if report_id:
            await search_service.delete_document(
                index_name="student-reports",
                document_id=report_id
            )
    
    # Delete test profiles
    for profile_id in [profile1_id, profile2_id]:
        if profile_id:
            await search_service.delete_document(
                index_name="student-profiles",
                document_id=profile_id
            )
    
    # Delete test learning plans
    for plan_id in [plan1_id, plan2_id]:
        if plan_id:
            await search_service.delete_document(
                index_name="learning-plans",
                document_id=plan_id
            )
    
    logger.info("Test data cleanup completed!")

async def run_tests():
    """Run all isolation tests."""
    try:
        logger.info("Starting user isolation tests...")
        logger.info(f"User1 ID: {USER1['id']}")
        logger.info(f"User2 ID: {USER2['id']}")
        
        # Create test data for both users
        report1_id = await create_test_report(USER1["id"], "User1")
        report2_id = await create_test_report(USER2["id"], "User2")
        
        profile1_id = await create_test_profile(USER1["id"], "User1")
        profile2_id = await create_test_profile(USER2["id"], "User2")
        
        plan1_id = await create_test_learning_plan(USER1["id"], "User1")
        plan2_id = await create_test_learning_plan(USER2["id"], "User2")
        
        # Run isolation tests
        await test_report_isolation(USER1["id"], USER2["id"], report1_id, report2_id)
        await test_profile_isolation(USER1["id"], USER2["id"], profile1_id, profile2_id)
        await test_learning_plan_isolation(USER1["id"], USER2["id"], plan1_id, plan2_id)
        
        # Clean up test data
        await cleanup_test_data(report1_id, report2_id, profile1_id, profile2_id, plan1_id, plan2_id)
        
        logger.info("All user isolation tests passed!")
        return True
    except AssertionError as e:
        logger.error(f"Test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Run the tests
    asyncio.run(run_tests())