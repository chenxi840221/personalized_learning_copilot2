# backend/rag/openai_adapter.py
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI, AzureOpenAI
from config.settings import Settings

# Initialize settings
settings = Settings()

# Initialize logger
logger = logging.getLogger(__name__)

class OpenAIAdapter:
    """
    Adapter class for Azure OpenAI API using the v1.x OpenAI package.
    Supports Azure Cognitive Services Multi-Service Resource configuration.
    """
    def __init__(self):
        """Initialize the OpenAI client with Azure configuration."""
        # Configure OpenAI with Azure details
        api_key = settings.get_openai_key()
        api_base = settings.get_openai_endpoint()
        api_version = settings.AZURE_OPENAI_API_VERSION

        # Initialize the appropriate client based on the API type
        if hasattr(settings, 'OPENAI_API_TYPE') and settings.OPENAI_API_TYPE == "azure":
            self.client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=api_base
            )
        else:
            self.client = OpenAI(
                api_key=api_key,
                base_url=api_base
            )
    
    async def create_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a chat completion using Azure OpenAI.
        Args:
            model: The deployment name in Azure OpenAI
            messages: List of message dictionaries with role and content
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum number of tokens to generate
            response_format: Optional format specification (e.g., {"type": "json_object"})
        Returns:
            Dictionary containing the completion response
        """
        try:
            # Set up the parameters
            params = {
                "model": model,  # Use the deployment name
                "messages": messages,
                "temperature": temperature
            }
            
            # Add max_tokens if specified
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
                
            # Add response_format if specified (for newer API versions)
            if response_format is not None:
                params["response_format"] = response_format
                
            # Make the API call
            response = self.client.chat.completions.create(**params)
            
            # Convert response to dictionary format for backward compatibility
            # This allows existing code to continue working without major changes
            response_dict = {
                "choices": [
                    {
                        "index": i,
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content
                        },
                        "finish_reason": choice.finish_reason
                    }
                    for i, choice in enumerate(response.choices)
                ],
                "created": response.created,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            return response_dict
            
        except Exception as e:
            logger.error(f"Error creating chat completion: {e}")
            raise
    
    async def create_embedding(
        self,
        model: str,
        text: str
    ) -> List[float]:
        """
        Create an embedding using Azure OpenAI.
        Args:
            model: The deployment name in Azure OpenAI
            text: Text to embed
        Returns:
            List of embedding values
        """
        try:
            # Make the API call
            response = self.client.embeddings.create(
                model=model,  # Use the deployment name 
                input=text
            )
            
            # Extract the embedding and return as a flat list
            return response.data[0].embedding
                
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            raise

# Singleton instance
openai_adapter = None

async def get_openai_adapter():
    """Get or create the OpenAI adapter singleton."""
    global openai_adapter
    if openai_adapter is None:
        openai_adapter = OpenAIAdapter()
    return openai_adapter