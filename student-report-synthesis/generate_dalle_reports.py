#!/usr/bin/env python3
"""
Demo script for generating school reports with DALL-E generated images.

This script demonstrates the integrated report generation process using
DALL-E to create school badges and student photos.
"""

import os
import sys
import argparse
import logging
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Import the enhanced report generator
from src.report_engine.enhanced_report_generator import EnhancedReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/dalle_demo.log"),
        logging.StreamHandler()
    ]
)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger(__name__)

# DALL-E 3 supported image sizes
VALID_IMAGE_SIZES = ["1024x1024", "1792x1024", "1024x1792"]

def generate_single_report(args, report_generator):
    """Generate a single report with DALL-E images."""
    print(f"Generating a single {args.style} report with DALL-E images...")
    
    output_path = args.output if args.output else None
    
    # Validate image size
    image_size = args.image_size if args.image_size in VALID_IMAGE_SIZES else "1024x1024"
    if args.image_size not in VALID_IMAGE_SIZES:
        print(f"Warning: Image size '{args.image_size}' is not supported by DALL-E 3. Using '1024x1024' instead.")
        print(f"Supported sizes: {', '.join(VALID_IMAGE_SIZES)}")
    
    # Generate the report
    report_path = report_generator.generate_report(
        style=args.style,
        output_format=args.format,
        comment_length=args.comment_length,
        output_path=output_path,
        generate_images=True,
        image_options={
            "badge_style": args.badge_style,
            "badge_colors": args.badge_colors.split(",") if args.badge_colors else ["navy blue", "gold"],
            "photo_style": "school portrait",
            "photo_size": image_size
        }
    )
    
    if report_path:
        print(f"✅ Report successfully generated: {report_path}")
        return 0
    else:
        print("❌ Failed to generate report")
        return 1

def generate_batch_reports(args, report_generator):
    """Generate a batch of reports with DALL-E images."""
    print(f"Generating {args.num} {args.style} reports with DALL-E images...")
    
    # Validate image size
    image_size = args.image_size if args.image_size in VALID_IMAGE_SIZES else "1024x1024"
    if args.image_size not in VALID_IMAGE_SIZES:
        print(f"Warning: Image size '{args.image_size}' is not supported by DALL-E 3. Using '1024x1024' instead.")
        print(f"Supported sizes: {', '.join(VALID_IMAGE_SIZES)}")
        
    # Create a batch ID if not provided
    batch_id = args.batch_id or f"batch_{uuid.uuid4().hex[:8]}"
    
    # Get style-specific settings
    style_key = args.style.lower()
        
    # Generate the batch
    batch_result = report_generator.generate_batch_reports(
        num_reports=args.num,
        style=args.style,
        output_format=args.format,
        comment_length=args.comment_length,
        batch_id=batch_id,
        generate_images=True,
        image_options={
            "badge_style": args.badge_style,
            "badge_colors": args.badge_colors.split(",") if args.badge_colors else ["navy blue", "gold"],
            "photo_style": "school portrait",
            "photo_size": image_size
        }
    )
    
    if batch_result["status"] == "completed":
        successful = len([r for r in batch_result["reports"] if r["status"] == "generated"])
        print(f"✅ Generated {successful} out of {args.num} reports")
        print(f"📁 Batch ID: {batch_result['batch_id']}")
        
        # Create a ZIP archive
        zip_path = report_generator.create_zip_archive(batch_result["batch_id"])
        if zip_path:
            print(f"📦 ZIP archive: {zip_path}")
            
        return 0
    else:
        print("❌ Failed to generate batch reports")
        return 1

def main():
    """Main entry point for the demo script."""
    # Load environment variables
    load_dotenv()
    
    # Get OpenAI credentials
    openai_endpoint = os.environ.get("OPENAI_ENDPOINT")
    openai_key = os.environ.get("OPENAI_KEY")
    openai_deployment = os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o")
    
    # Check if OpenAI credentials are set
    if not openai_endpoint or not openai_key:
        print("❌ OpenAI credentials are required. Please set OPENAI_ENDPOINT and OPENAI_KEY environment variables.")
        return 1
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate school reports with DALL-E images")
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Single report generator
    single_parser = subparsers.add_parser("single", help="Generate a single report with DALL-E images")
    single_parser.add_argument("--style", type=str, default="act", help="Report style (e.g., act, nsw, qld, vic, generic)")
    single_parser.add_argument("--format", type=str, choices=["pdf", "html"], default="pdf", help="Output format")
    single_parser.add_argument("--comment-length", type=str, choices=["brief", "standard", "detailed"], default="standard", help="Comment length")
    single_parser.add_argument("--output", type=str, help="Output file path")
    single_parser.add_argument("--badge-style", type=str, default="modern", help="Style for school badge (modern, traditional, minimalist, elegant)")
    single_parser.add_argument("--badge-colors", type=str, help="Comma-separated colors for badge (e.g., 'navy blue,gold')")
    single_parser.add_argument("--image-size", type=str, default="1024x1024", 
                             help=f"Image size (supported: {', '.join(VALID_IMAGE_SIZES)})")
    
    # Batch report generator
    batch_parser = subparsers.add_parser("batch", help="Generate multiple reports with DALL-E images")
    batch_parser.add_argument("--num", type=int, required=True, help="Number of reports to generate")
    batch_parser.add_argument("--style", type=str, default="act", help="Report style (e.g., act, nsw, qld, vic, generic)")
    batch_parser.add_argument("--format", type=str, choices=["pdf", "html"], default="pdf", help="Output format")
    batch_parser.add_argument("--comment-length", type=str, choices=["brief", "standard", "detailed"], default="standard", help="Comment length")
    batch_parser.add_argument("--batch-id", type=str, help="Batch ID (generated if not provided)")
    batch_parser.add_argument("--badge-style", type=str, default="modern", help="Style for school badge (modern, traditional, minimalist, elegant)")
    batch_parser.add_argument("--badge-colors", type=str, help="Comma-separated colors for badge (e.g., 'navy blue,gold')")
    batch_parser.add_argument("--image-size", type=str, default="1024x1024", 
                            help=f"Image size (supported: {', '.join(VALID_IMAGE_SIZES)})")
    
    # List styles command
    styles_parser = subparsers.add_parser("styles", help="List available report styles with DALL-E settings")
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command provided, show help
    if args.command is None:
        parser.print_help()
        return 1
    
    # Handle the styles command
    if args.command == "styles":
        print("Available report styles with DALL-E settings:")
        style_settings = {
            "act": {
                "badge_colors": ["navy blue", "gold"],
                "badge_style": "modern",
                "photo_style": "school portrait",
            },
            "nsw": {
                "badge_colors": ["blue", "white"],
                "badge_style": "traditional",
                "photo_style": "school portrait",
            },
            "vic": {
                "badge_colors": ["navy blue", "white"],
                "badge_style": "modern",
                "photo_style": "school portrait",
            },
            "qld": {
                "badge_colors": ["maroon", "gold"],
                "badge_style": "traditional",
                "photo_style": "school portrait",
            },
            "generic": {
                "badge_colors": ["blue", "gold"],
                "badge_style": "modern",
                "photo_style": "school portrait",
            }
        }
        
        for style, settings in style_settings.items():
            print(f"\n{style.upper()}:")
            print(f"  Badge Style: {settings['badge_style']}")
            print(f"  Badge Colors: {', '.join(settings['badge_colors'])}")
            print(f"  Photo Style: {settings['photo_style']}")
        
        print(f"\nDALL-E 3 supported image sizes: {', '.join(VALID_IMAGE_SIZES)}")
        return 0
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Initialize the report generator with DALL-E integration
    report_generator = EnhancedReportGenerator(
        form_recognizer_endpoint="",
        form_recognizer_key="",
        openai_endpoint=openai_endpoint,
        openai_key=openai_key,
        openai_deployment=openai_deployment,
        templates_dir="templates",
        output_dir="output",
        report_styles_dir="report_styles",
        enable_images=True,
        dalle_deployment="dall-e-3"  # Specify the DALL-E deployment name
    )
    
    # Execute the requested command
    if args.command == "single":
        return generate_single_report(args, report_generator)
    elif args.command == "batch":
        return generate_batch_reports(args, report_generator)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())