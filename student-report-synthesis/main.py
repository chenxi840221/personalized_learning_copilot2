#!/usr/bin/env python3
"""
Main entry point for the Student Report Generation System.
"""

import os
import sys
import logging
from dotenv import load_dotenv

from src.report_engine.enhanced_report_generator import EnhancedReportGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to run the report generator."""
    # Load environment variables
    load_dotenv()
    
    # Get API keys from environment variables
    openai_endpoint = os.environ.get("OPENAI_ENDPOINT", "")
    openai_key = os.environ.get("OPENAI_KEY", "")
    openai_deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")
    form_recognizer_endpoint = os.environ.get("FORM_RECOGNIZER_ENDPOINT", "")
    form_recognizer_key = os.environ.get("FORM_RECOGNIZER_KEY", "")
    
    # Check if OpenAI credentials are set
    if not openai_endpoint or not openai_key:
        logger.error("OpenAI credentials are not set. Please set OPENAI_ENDPOINT and OPENAI_KEY environment variables.")
        return 1
    
    # Initialize the report generator
    report_generator = EnhancedReportGenerator(
        form_recognizer_endpoint=form_recognizer_endpoint,
        form_recognizer_key=form_recognizer_key,
        openai_endpoint=openai_endpoint,
        openai_key=openai_key,
        openai_deployment=openai_deployment,
        templates_dir="templates",
        output_dir="output",
        report_styles_dir="src/report_engine/styles"
    )
    
    # Generate a sample report
    output_path = report_generator.generate_report(
        style="act",
        output_format="pdf",
        comment_length="standard"
    )
    
    if output_path:
        logger.info(f"Report generated successfully: {output_path}")
        print(f"✅ Report generated successfully: {output_path}")
        return 0
    else:
        logger.error("Failed to generate report.")
        print("❌ Failed to generate report.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
