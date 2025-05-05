"""
DALL-E Image Generator module for creating realistic school badges and student photos.

This module uses Azure OpenAI's DALL-E model to generate realistic images
for school badges and student photos, integrated directly with the report generator.
"""

import logging
import base64
import os
import requests
import json
from typing import Dict, Any, Optional, Tuple, List
from io import BytesIO
from PIL import Image

# Set up logging
logger = logging.getLogger(__name__)

class DallEImageGenerator:
    """Class for generating synthetic images using Azure OpenAI's DALL-E."""
    
    def __init__(
        self, 
        openai_endpoint: str,
        openai_key: str,
        openai_deployment: str = "dall-e-3",
        api_version: str = "2024-02-01"
    ):
        """
        Initialize the DALL-E Image Generator.
        
        Args:
            openai_endpoint: Azure OpenAI endpoint
            openai_key: Azure OpenAI API key
            openai_deployment: Azure OpenAI deployment name for DALL-E
            api_version: API version for DALL-E
        """
        # Fix the endpoint URL - make sure we're using the base endpoint only
        # Remove any path components and query parameters
        base_url = openai_endpoint.split('/openai')[0] if '/openai' in openai_endpoint else openai_endpoint
        if '?' in base_url:
            base_url = base_url.split('?')[0]
        
        self.openai_endpoint = base_url.rstrip('/')
        self.openai_key = openai_key
        self.openai_deployment = openai_deployment
        self.api_version = api_version
        logger.info(f"DALL-E generator initialized with endpoint: {self.openai_endpoint}, deployment: {openai_deployment}")
    
    def _generate_dalle_image(self, prompt: str, size: str = "1024x1024") -> Optional[bytes]:
        """
        Make a direct API call to generate an image with DALL-E.
        
        Args:
            prompt: The text prompt for image generation
            size: Image size (1024x1024, 1792x1024, or 1024x1792) - DALL-E 3 only supports these sizes
            
        Returns:
            Image data as bytes or None if generation failed
        """
        # Construct the API URL
        url = f"{self.openai_endpoint}/openai/deployments/{self.openai_deployment}/images/generations?api-version={self.api_version}"
        
        logger.info(f"Using DALL-E URL: {url}")
        
        # Prepare the request payload
        payload = {
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": "standard"
        }
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "api-key": self.openai_key
        }
        
        try:
            # Make the API request
            logger.info(f"Sending DALL-E request to {url}")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"DALL-E API error: Status code {response.status_code}, Response: {response.text}")
                return None
            
            # Parse the response
            response_data = response.json()
            
            # Extract the image URL
            if 'data' in response_data and len(response_data['data']) > 0:
                image_url = response_data['data'][0]['url']
                logger.info(f"Image URL generated: {image_url}")
                
                # Download the image
                image_response = requests.get(image_url, timeout=10)
                return image_response.content
            else:
                logger.error(f"No image data in the response: {json.dumps(response_data)}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate image with DALL-E: {str(e)}")
            return None
    
    def generate_school_badge(
        self, 
        school_name: str, 
        school_type: str = "Primary School",
        style: str = "modern",
        colors: Optional[List[str]] = None,
        motto: Optional[str] = None,
        image_size: str = "1024x1024"  # Updated to use a valid DALL-E 3 size
    ) -> str:
        """
        Generate a school badge using DALL-E.
        
        Args:
            school_name: Name of the school
            school_type: Type of school (Primary School, High School, etc.)
            style: Style of the badge (modern, traditional, minimalist)
            colors: Optional list of color descriptions
            motto: Optional school motto
            image_size: Size of the generated image (must be one of: 1024x1024, 1792x1024, 1024x1792)
            
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
            image_data = self._generate_dalle_image(prompt, image_size)
            
            if image_data:
                # Convert to base64 data URI
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                data_uri = f"data:image/png;base64,{image_base64}"
                
                logger.info(f"Generated school badge for {school_name}")
                return data_uri
            else:
                raise Exception("Failed to generate image")
            
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
        image_size: str = "1024x1024"  # Updated to use a valid DALL-E 3 size
    ) -> str:
        """
        Generate a student photo using DALL-E.
        
        Args:
            gender: Gender of the student (male, female, neutral)
            age: Age of the student (6-18)
            ethnicity: Optional ethnicity description
            hair_description: Optional hair description
            style: Style of the photo
            image_size: Size of the generated image (must be one of: 1024x1024, 1792x1024, 1024x1792)
            
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
            image_data = self._generate_dalle_image(prompt, image_size)
            
            if image_data:
                # Convert to base64 data URI
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                data_uri = f"data:image/png;base64,{image_base64}"
                
                logger.info(f"Generated student photo for {gender} {age_term}")
                return data_uri
            else:
                raise Exception("Failed to generate image")
            
        except Exception as e:
            logger.error(f"Failed to generate student photo with DALL-E: {str(e)}")
            # Return a fallback image
            return self._get_fallback_student_photo(gender, age)
    
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