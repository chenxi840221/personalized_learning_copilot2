# backend/utils/cognitive_services.py
"""
Utility functions for Azure Cognitive Services Multi-Service Resource.
Handles endpoint formatting and validation.
"""

import logging
import re
from typing import Optional
from urllib.parse import urljoin

# Initialize logger
logger = logging.getLogger(__name__)

def format_cognitive_endpoint(base_endpoint: str, service_path: str) -> str:
    """
    Format a cognitive service endpoint correctly.
    
    Args:
        base_endpoint: The base Cognitive Services endpoint
        service_path: The service-specific path
        
    Returns:
        Properly formatted endpoint URL
    """
    # Ensure the base endpoint ends with a slash
    if not base_endpoint.endswith('/'):
        base_endpoint += '/'
        
    # Remove any leading slash from service path to prevent double slashes
    if service_path.startswith('/'):
        service_path = service_path[1:]
        
    # Join the base endpoint and service path
    return urljoin(base_endpoint, service_path)


def validate_cognitive_key(key) -> bool:
    """
    Validate that a cognitive services key is properly formatted.
    
    Args:
        key: The Cognitive Services key to validate
        
    Returns:
        True if the key appears valid, False otherwise
    """
    # Verify the key is a string
    if not isinstance(key, str):
        logger.warning("Cognitive Services key must be a string")
        return False
        
    # Most Azure keys are 32 character hex strings
    if re.match(r'^[0-9a-fA-F]{32}$', key):
        return True
        
    # Some keys might be longer JWT-like strings
    if len(key) > 20 and '.' in key:
        return True
        
    logger.warning("Cognitive Services key appears to be improperly formatted")
    return False


def get_service_specific_endpoint(base_endpoint: str, service_name: str, api_version: Optional[str] = None) -> str:
    """
    Get the endpoint for a specific cognitive service.
    
    Args:
        base_endpoint: Base Cognitive Services endpoint
        service_name: Service name (e.g., 'openai', 'formrecognizer', etc.)
        api_version: Optional API version
        
    Returns:
        Service-specific endpoint
    """
    service_paths = {
        'openai': 'openai',
        'formrecognizer': 'formrecognizer/documentAnalysis',
        'textanalytics': 'text/analytics/v3.1',
        'computervision': 'vision/v3.2',
        'language': 'language'
    }
    
    if service_name not in service_paths:
        logger.warning(f"Unknown service: {service_name}. Using as-is.")
        return format_cognitive_endpoint(base_endpoint, service_name)
    
    service_path = service_paths[service_name]
    
    # Add API version if provided and not already in the base endpoint
    if api_version and '?api-version=' not in base_endpoint:
        service_path = f"{service_path}?api-version={api_version}"
        
    return format_cognitive_endpoint(base_endpoint, service_path)