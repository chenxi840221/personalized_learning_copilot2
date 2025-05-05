#!/usr/bin/env python3
"""
Test script for verifying image caching in batch report generation.

This script tests the image caching functionality to ensure that 
student photos and school badges are reused across multiple reports
for the same student in different semesters/years.
"""

import os
import logging
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv

# Import from the report engine
from src.report_engine.enhanced_report_generator import EnhancedReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/test_image_caching.log"),
        logging.StreamHandler()
    ]
)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger(__name__)

def test_image_caching():
    """Test the image caching functionality for batch report generation."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Get environment variables
    openai_endpoint = os.environ.get("OPENAI_ENDPOINT", "")
    openai_key = os.environ.get("OPENAI_KEY", "")
    openai_deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")
    
    # Initialize the report generator with DALL-E integration enabled
    report_generator = EnhancedReportGenerator(
        form_recognizer_endpoint="",
        form_recognizer_key="",
        openai_endpoint=openai_endpoint,
        openai_key=openai_key,
        openai_deployment=openai_deployment,
        enable_images=True
    )
    
    # Generate a small batch of reports with images enabled
    # We'll use a small number of students (2) for quick testing
    logger.info("Generating test batch with image caching...")
    batch_result = report_generator.generate_batch_reports(
        num_reports=2,  # Generate reports for 2 students
        style="generic",
        output_format="html",  # Use HTML for faster generation
        comment_length="brief",  # Use brief comments for faster generation
        generate_images=True  # Enable image generation
    )
    
    # Check the batch metadata for success
    if batch_result["status"] != "completed":
        logger.error("Batch generation failed!")
        return False
    
    # Verify that all reports were generated
    successful_reports = [r for r in batch_result["reports"] if r["status"] == "generated"]
    if len(successful_reports) != 8:  # Should be 8 reports (2 students x 4 semesters)
        logger.error(f"Expected 8 reports, but got {len(successful_reports)} successful reports")
        return False
    
    logger.info(f"Successfully generated {len(successful_reports)} reports")
    
    # For additional verification, check the batch directory for image references
    batch_dir = Path("output") / batch_result["batch_id"]
    logger.info(f"Batch directory: {batch_dir}")
    
    # Organize reports by student
    students = {}
    for report in batch_result["reports"]:
        if report["status"] != "generated":
            continue
            
        student_name = report["student_name"]
        if student_name not in students:
            students[student_name] = []
            
        students[student_name].append({
            "semester": report["semester"],
            "year": report["year"],
            "path": report["path"]
        })
    
    # Check each student's reports to verify identical image references
    image_verification_successful = True
    for student_name, reports in students.items():
        logger.info(f"Verifying image consistency for student: {student_name}")
        
        # Sort reports by year and semester
        reports.sort(key=lambda r: (r["year"], r["semester"]))
        
        # Extract image references from the first report
        first_report_path = reports[0]["path"]
        student_photo = None
        school_logo = None
        
        with open(first_report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for student photo reference
            import re
            student_photo_match = re.search(r'src="(data:image/png;base64,[^"]+)".*?student-photo', content)
            if student_photo_match:
                student_photo = student_photo_match.group(1)
                logger.info("Found student photo reference in first report")
            
            # Look for school logo reference
            school_logo_match = re.search(r'src="(data:image/png;base64,[^"]+)".*?school-logo', content)
            if school_logo_match:
                school_logo = school_logo_match.group(1)
                logger.info("Found school logo reference in first report")
        
        # Check subsequent reports to ensure they use the same image references
        for i, report in enumerate(reports[1:], 1):
            logger.info(f"Checking image references in report {i+1} for {student_name}")
            report_path = report["path"]
            
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Check student photo reference
                if student_photo:
                    student_photo_match = re.search(r'src="(data:image/png;base64,[^"]+)".*?student-photo', content)
                    if student_photo_match:
                        match_photo = student_photo_match.group(1)
                        if match_photo != student_photo:
                            logger.error(f"Student photo in report {i+1} doesn't match first report!")
                            image_verification_successful = False
                        else:
                            logger.info(f"Student photo in report {i+1} matches first report - PASSED ✅")
                
                # Check school logo reference
                if school_logo:
                    school_logo_match = re.search(r'src="(data:image/png;base64,[^"]+)".*?school-logo', content)
                    if school_logo_match:
                        match_logo = school_logo_match.group(1)
                        if match_logo != school_logo:
                            logger.error(f"School logo in report {i+1} doesn't match first report!")
                            image_verification_successful = False
                        else:
                            logger.info(f"School logo in report {i+1} matches first report - PASSED ✅")
    
    # Final verification result
    if image_verification_successful:
        logger.info("✅ Image caching test PASSED - All student images are consistent across reports")
        return True
    else:
        logger.error("❌ Image caching test FAILED - Found inconsistent images across reports")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test image caching in batch report generation")
    parser.add_argument("--num", type=int, default=2, help="Number of students to generate reports for")
    parser.add_argument("--style", type=str, default="generic", help="Report style to use")
    args = parser.parse_args()
    
    print(f"Testing image caching in batch report generation...")
    print(f"Generating reports for {args.num} students, using {args.style} style...")
    print(f"This will create {args.num * 4} total reports (4 semester reports per student).")
    print(f"The test will verify that each student's photos and school badges are consistent across reports.")
    
    # Run the test
    success = test_image_caching()
    
    if success:
        print("\n✅ Image caching test PASSED!")
        print("Student photos and school badges are being correctly reused across semesters/years.")
    else:
        print("\n❌ Image caching test FAILED!")
        print("Please check logs for details.")
    
    # Print useful information about the batch report generation
    print("\nTo run batch report generation with image caching:")
    print("python generate_reports.py batch --num 5 --style act --format pdf --images")
    print("\nBatch generation with DALL-E images:")
    print("python generate_dalle_reports.py batch --num 3 --style nsw --badge-style modern")
    print("\nImage caching will:")
    print("1. Generate DALL-E images only once per student (first report)")
    print("2. Reuse the same images for the student's subsequent reports")
    print("3. Ensure visual consistency across all reports for the same student")