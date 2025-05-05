#!/usr/bin/env python3
"""
DALL-E API Test Script

This script tests the Azure OpenAI DALL-E image generation capabilities
with a simple prompt.
"""

import os
import base64
import requests
import json
import time
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_dalle_generation(
    api_key, 
    endpoint="https://australiaeast.api.cognitive.microsoft.com/", 
    deployment_name="dall-e-3", 
    api_version="2024-02-01",
    prompt="A cute cartoon owl wearing glasses and reading a book",
    size="1024x1024",
    save_image=True
):
    """Test DALL-E image generation using Azure OpenAI's direct API."""
    
    # Construct the proper endpoint URL
    url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment_name}/images/generations?api-version={api_version}"
    
    print(f"Testing DALL-E with URL: {url}")
    print(f"Prompt: {prompt}")
    
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
        "api-key": api_key
    }
    
    try:
        # Make the API request
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        end_time = time.time()
        
        # Check for errors
        if response.status_code != 200:
            print(f"Error: Status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Parse the response
        response_data = response.json()
        
        # Extract the image URL
        if 'data' in response_data and len(response_data['data']) > 0:
            image_url = response_data['data'][0]['url']
            print(f"Image generated in {end_time - start_time:.2f} seconds")
            print(f"Image URL: {image_url}")
            
            if save_image:
                # Download the image
                image_response = requests.get(image_url, timeout=10)
                image_data = image_response.content
                
                # Save to file
                timestamp = int(time.time())
                filename = f"dalle_test_{timestamp}.png"
                with open(filename, "wb") as f:
                    f.write(image_data)
                print(f"Image saved to {filename}")
            
            return True
        else:
            print("No image data in the response")
            print(f"Full response: {json.dumps(response_data, indent=2)}")
            return False
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test Azure OpenAI DALL-E image generation")
    parser.add_argument("--key", default=os.environ.get("OPENAI_KEY", ""), help="Azure OpenAI API key")
    parser.add_argument("--endpoint", default=os.environ.get("OPENAI_ENDPOINT", "https://australiaeast.api.cognitive.microsoft.com/"), help="Azure OpenAI endpoint")
    parser.add_argument("--deployment", default="dall-e-3", help="DALL-E deployment name")
    parser.add_argument("--api-version", default="2024-02-01", help="API version")
    parser.add_argument("--prompt", default="A logo for Sunshine Primary School with a sun and books", help="Image generation prompt")
    parser.add_argument("--size", default="1024x1024", choices=["1024x1024", "1024x1792", "1792x1024"], help="Image size")
    parser.add_argument("--no-save", action="store_true", help="Don't save the generated image")
    
    args = parser.parse_args()
    
    # Test DALL-E
    success = test_dalle_generation(
        api_key=args.key,
        endpoint=args.endpoint,
        deployment_name=args.deployment,
        api_version=args.api_version,
        prompt=args.prompt,
        size=args.size,
        save_image=not args.no_save
    )
    
    if success:
        print("✅ DALL-E test completed successfully!")
    else:
        print("❌ DALL-E test failed")

if __name__ == "__main__":
    main()