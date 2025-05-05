"""
Content generator module part 2 for project setup.

This module continues the ContentGenerator class implementation.
"""

class ContentGenerator:
    """Generator for Python and configuration file content."""
    
    def get_dalle_image_generator_content(self) -> str:
        """Get content for the DALL-E image generator module."""
        return '''"""
DALL-E Image Generator module for creating realistic school badges and student photos.

This module uses Azure OpenAI's DALL-E model to generate realistic images
for school badges and student photos, integrated directly with the report generator.
"""

import logging
import base64
import os
import requests
import tempfile
from typing import Dict, Any, Optional, Tuple, List
from io import BytesIO
from PIL import Image

# Set up logging
logger = logging.getLogger(__name__)

class DallEImageGenerator:
    """Class for generating synthetic images using Azure OpenAI's DALL-E."""
    
    def __init__(self, openai_client):
        """
        Initialize the DALL-E Image Generator.
        
        Args:
            openai_client: An instance of OpenAI client
        """
        self.openai_client = openai_client
    
    def generate_school_badge(
        self, 
        school_name: str, 
        school_type: str = "Primary School",
        style: str = "modern",
        colors: Optional[List[str]] = None,
        motto: Optional[str] = None,
        image_size: str = "1024x1024"
    ) -> str:
        """
        Generate a school badge using DALL-E.
        
        Args:
            school_name: Name of the school
            school_type: Type of school (Primary School, High School, etc.)
            style: Style of the badge (modern, traditional, minimalist)
            colors: Optional list of color descriptions
            motto: Optional school motto
            image_size: Size of the generated image
            
        Returns:
            Base64 encoded image data URI
        """
        # Default colors if not provided
        if not colors:
            colors = ["navy blue", "gold"]
            
        # Construct colors prompt
        color_prompt = f" with colors {', '.join(colors)},"
        
        # Construct motto prompt
        motto_prompt = ""
        if motto:
            motto_prompt = f" with the motto '{motto}',"
        
        # Construct the prompt
        prompt = f"A professional, high-quality school logo for {school_name}, a {school_type}, in a {style} style{color_prompt}{motto_prompt} with educational symbols. The logo should be on a plain white background with no text, only the emblem."
        
        try:
            # Generate image using DALL-E
            response = self.openai_client.images.generate(
                model="dall-e-3",  # Using DALL-E 3 model
                prompt=prompt,
                n=1,
                size=image_size,
                quality="standard"
            )
            
            # Get the image URL
            image_url = response.data[0].url
            
            # Download the image
            image_data = self._download_image(image_url)
            
            # Convert to base64 data URI
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            data_uri = f"data:image/png;base64,{image_base64}"
            
            logger.info(f"Generated school badge for {school_name}")
            return data_uri
            
        except Exception as e:
            logger.error(f"Failed to generate school badge with DALL-E: {str(e)}")
            # Return a fallback image
            return self._get_fallback_school_badge(school_name, school_type, motto)
    
    def generate_student_photo(
        self,
        gender: str = "neutral",
        age: int = 10,
        ethnicity: Optional[str] = None,
        hair_description: Optional[str] = None,
        style: str = "school portrait",
        image_size: str = "1024x1024"
    ) -> str:
        """
        Generate a student photo using DALL-E.
        
        Args:
            gender: Gender of the student (male, female, neutral)
            age: Age of the student (6-18)
            ethnicity: Optional ethnicity description
            hair_description: Optional hair description
            style: Style of the photo
            image_size: Size of the generated image
            
        Returns:
            Base64 encoded image data URI
        """
        # Ensure age is within school range
        age = max(6, min(18, age))
        
        # Determine school level based on age
        if age <= 12:
            school_level = "primary school"
        else:
            school_level = "high school"
        
        # Construct ethnicity prompt
        ethnicity_prompt = ""
        if ethnicity:
            ethnicity_prompt = f" {ethnicity}"
        
        # Construct hair prompt
        hair_prompt = ""
        if hair_description:
            hair_prompt = f" with {hair_description} hair,"
        
        # Use "child" or "teenager" based on age
        age_term = "child" if age <= 12 else "teenager"
        
        # Construct the prompt - being careful to generate appropriate images
        prompt = f"A professional, appropriate school portrait photograph of a {age} year old {ethnicity_prompt} {gender} {age_term}{hair_prompt} wearing a {school_level} uniform, with a plain blue background, looking directly at the camera with a small smile. The image should be suitable for a school report card."
        
        try:
            # Generate image using DALL-E
            response = self.openai_client.images.generate(
                model="dall-e-3",  # Using DALL-E 3 model
                prompt=prompt,
                n=1,
                size=image_size,
                quality="standard"
            )
            
            # Get the image URL
            image_url = response.data[0].url
            
            # Download the image
            image_data = self._download_image(image_url)
            
            # Convert to base64 data URI
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            data_uri = f"data:image/png;base64,{image_base64}"
            
            logger.info(f"Generated student photo for {gender} {age_term}")
            return data_uri
            
        except Exception as e:
            logger.error(f"Failed to generate student photo with DALL-E: {str(e)}")
            # Return a fallback image
            return self._get_fallback_student_photo(gender, age)
    
    def _download_image(self, image_url: str) -> bytes:
        """
        Download an image from a URL.
        
        Args:
            image_url: URL of the image
            
        Returns:
            Image data as bytes
        """
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        return response.content
    
    def _get_fallback_school_badge(self, school_name: str, school_type: str, motto: Optional[str] = None) -> str:
        """
        Generate a fallback school badge.
        
        Args:
            school_name: Name of the school
            school_type: Type of school
            motto: Optional school motto
            
        Returns:
            Base64 encoded image data URI
        """
        try:
            # Create a simple badge using PIL
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a new image with a white background
            img = Image.new('RGB', (500, 500), color='white')
            draw = ImageDraw.Draw(img)
            
            # Draw a circle for the badge
            draw.ellipse((50, 50, 450, 450), fill='navy')
            draw.ellipse((60, 60, 440, 440), fill='lightblue')
            
            # Draw school name
            try:
                # Try to get a font
                font_large = ImageFont.truetype("arial.ttf", 40)
                font_small = ImageFont.truetype("arial.ttf", 30)
            except IOError:
                # Fallback to default font
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Get text sizes for centering
            text_width = draw.textlength(school_name, font=font_large)
            text_width2 = draw.textlength(school_type, font=font_small)
            
            # Draw text
            draw.text(
                (250 - text_width/2, 200),
                school_name,
                font=font_large,
                fill='white'
            )
            
            draw.text(
                (250 - text_width2/2, 250),
                school_type,
                font=font_small,
                fill='white'
            )
            
            # Add motto if provided
            if motto:
                text_width3 = draw.textlength(motto, font=font_small)
                draw.text(
                    (250 - text_width3/2, 300),
                    motto,
                    font=font_small,
                    fill='white'
                )
            
            # Save the image to a bytes buffer
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            
            # Encode as base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Failed to create fallback badge: {str(e)}")
            
            # Return an empty transparent PNG
            empty_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            return f"data:image/png;base64,{empty_png}"
    
    def _get_fallback_student_photo(self, gender: str, age: int) -> str:
        """
        Generate a fallback student photo.
        
        Args:
            gender: Gender of the student
            age: Age of the student
            
        Returns:
            Base64 encoded image data URI
        """
        try:
            # Create a simple avatar using PIL
            from PIL import Image, ImageDraw
            
            # Create a new image with a light blue background
            img = Image.new('RGB', (500, 500), color='lightblue')
            draw = ImageDraw.Draw(img)
            
            # Draw a simple avatar
            # Face
            draw.ellipse((150, 100, 350, 300), fill='peachpuff')
            
            # Eyes
            draw.ellipse((200, 170, 220, 190), fill='white')
            draw.ellipse((280, 170, 300, 190), fill='white')
            draw.ellipse((206, 176, 214, 184), fill='black')
            draw.ellipse((286, 176, 294, 184), fill='black')
            
            # Mouth
            draw.arc((220, 220, 280, 260), start=0, end=180, fill='black', width=3)
            
            # Hair - different based on gender
            if gender.lower() == 'male':
                draw.rectangle((150, 100, 350, 140), fill='brown')
            elif gender.lower() == 'female':
                draw.ellipse((140, 90, 360, 160), fill='brown')
                draw.rectangle((140, 130, 360, 300), fill='brown')
            else:
                # Neutral
                draw.ellipse((140, 90, 360, 150), fill='brown')
            
            # Body/shoulders
            draw.rectangle((175, 300, 325, 400), fill='navy')
            
            # Save the image to a bytes buffer
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            
            # Encode as base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Failed to create fallback photo: {str(e)}")
            
            # Return an empty transparent PNG
            empty_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            return f"data:image/png;base64,{empty_png}"
'''
    
    def get_enhanced_pdf_converter_content(self) -> str:
        """Get content for enhanced_pdf_converter.py."""
        # This method would be very long, so it's omitted in this implementation
        # Consider implementing this in a separate module if needed
        return '''# Enhanced PDF converter module implementation
"""
Enhanced HTML to PDF Converter

This script provides multiple methods to convert HTML reports to PDF with
improved formatting preservation. It tries multiple libraries in succession
until one succeeds.
"""

# This is a placeholder. The actual implementation would be quite long.
# For a complete implementation, extract this to a separate file.

def convert_html_to_pdf(html_path, pdf_path=None):
    """Convert HTML to PDF using the best available method."""
    # Placeholder implementation
    pass
'''

    def get_pdf_utils_content(self) -> str:
        """Get content for pdf_utils.py."""
        # This method would be very long, so it's shortened in this implementation
        return '''"""
PDF Utilities Module for converting HTML to PDF.

This module provides functions for converting HTML to PDF using various methods.
"""

import os
import logging
from typing import List, Callable, Optional

# Set up logging
logger = logging.getLogger(__name__)

def convert_html_to_pdf_with_weasyprint(html_path: str, pdf_path: Optional[str] = None) -> bool:
    """
    Convert HTML to PDF using WeasyPrint for better CSS support.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        # Import WeasyPrint
        from weasyprint import HTML, CSS
        
        # Set PDF path if not provided
        if pdf_path is None:
            pdf_path = html_path.replace('.html', '.pdf')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(pdf_path)), exist_ok=True)
        
        # Set up custom CSS to improve PDF rendering
        custom_css = CSS(string="""
            @page {
                size: A4;
                margin: 1cm;
            }
            body {
                font-family: Arial, Helvetica, sans-serif;
            }
            /* Add more CSS styling as needed */
        """)
        
        # Convert HTML to PDF
        HTML(filename=html_path).write_pdf(
            pdf_path,
            stylesheets=[custom_css]
        )
        
        logger.info(f"Successfully converted {html_path} to {pdf_path} using WeasyPrint")
        return True
        
    except ImportError:
        logger.warning("WeasyPrint not installed. Try: pip install weasyprint")
        return False
    except Exception as e:
        logger.error(f"Error with WeasyPrint: {str(e)}")
        return False

# Additional conversion methods would be implemented here
# - convert_html_to_pdf_with_xhtml2pdf
# - convert_html_to_pdf_with_wkhtmltopdf
# - convert_html_to_pdf (main function that tries all methods)

def convert_html_to_pdf(html_path: str, pdf_path: Optional[str] = None) -> bool:
    """
    Convert HTML to PDF using the best available method.
    Tries multiple methods in succession until one succeeds.
    
    Args:
        html_path: Path to the HTML file
        pdf_path: Path to save the PDF file (default: same as HTML but with .pdf extension)
    
    Returns:
        True if conversion successful, False otherwise
    """
    # Set PDF path if not provided
    if pdf_path is None:
        pdf_path = html_path.replace('.html', '.pdf')
    
    # Try with WeasyPrint first (would try multiple methods in a full implementation)
    try:
        return convert_html_to_pdf_with_weasyprint(html_path, pdf_path)
    except Exception as e:
        logger.error(f"All PDF conversion methods failed for {html_path}: {str(e)}")
        return False
'''

    def get_requirements_content(self) -> str:
        """Get content for requirements.txt."""
        return '''# Core dependencies
fastapi==0.95.1
uvicorn==0.22.0
python-multipart==0.0.6
openai>=1.0.0
python-dotenv==1.0.0

# Report generation
jinja2==3.1.2
reportlab==3.6.12
pillow==9.5.0
python-docx==0.8.11

# PDF conversion options
xhtml2pdf==0.2.11
weasyprint>=53.0
beautifulsoup4>=4.9.3

# Image processing
requests>=2.28.0

# Data handling
numpy>=1.22.0
pandas>=1.3.0

# Testing and development
pytest>=7.0.0
pytest-cov>=3.0.0
flake8>=4.0.0

# Documentation
sphinx>=4.3.0
sphinx-rtd-theme>=1.0.0
'''

    def get_dalle_integration_readme(self) -> str:
        """Get content for DALLE_INTEGRATION.md."""
        return '''# DALL-E Integration for Student Reports

This project includes integration with Azure OpenAI's DALL-E model to generate custom images for student reports:

1. **School Badges/Logos**: Customized school emblems based on school name, type, and colors
2. **Student Photos**: Realistic student portraits for use in reports

## Usage

### Basic Usage

Use the `--images` flag when generating reports:

```bash
python generate_reports.py single --style act --format pdf --images
```

### Dedicated Script

For more control, use the dedicated DALL-E reports script:

```bash
python generate_dalle_reports.py single --style act --badge-style modern --image-size 512x512
```

## Configuration Options

- **Badge Style**: modern, traditional, minimalist, elegant
- **Badge Colors**: Comma-separated color names (e.g., "navy blue,gold")
- **Photo Style**: school portrait, yearbook, classroom, etc.
- **Image Size**: 1024x1024 (high quality) or 512x512 (faster generation)

## Requirements

- Azure OpenAI API access with DALL-E model capabilities
- OPENAI_ENDPOINT and OPENAI_KEY environment variables configured

## Technical Details

The DALL-E integration is managed by the `DallEImageGenerator` class in `src/report_engine/ai/dalle_image_generator.py`.
'''

    def get_readme_content(self) -> str:
        """Get content for README.md."""
        return '''# Student Report Generation System

An AI-powered system for generating personalized student reports that follow Australian educational standards with support for different state/territory formats.

## Features

- **AI-Generated Content**: Uses Azure OpenAI's GPT-4o to generate realistic, personalized report comments
- **Multiple Report Styles**: Supports different Australian state/territory formats (ACT, NSW, etc.)
- **Customizable Templates**: HTML-based templates for easy customization
- **Batch Processing**: Generate multiple reports at once
- **PDF & HTML Output**: Export reports as PDF or HTML
- **Realistic Student Data**: Generate synthetic student profiles for testing

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables in `.env` file:
   ```
   OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
   OPENAI_KEY=your-openai-key
   OPENAI_DEPLOYMENT=gpt-4o
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## Usage

See `generate_reports.py` for command-line usage options.
'''
    
    def get_gitignore_content(self) -> str:
        """Get content for .gitignore."""
        return '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
venv/
env/
ENV/

# Environment variables
.env

# Generated reports
output/

# Log files
logs/
*.log

# Cache files
.cache/
.pytest_cache/
.coverage
htmlcov/

# IDE files
.idea/
.vscode/
*.swp
*.swo
'''