# backend/config/settings.py
from pydantic import BaseSettings
import os
from typing import List, Optional, Any, Dict
import logging

# Try to import dotenv, but handle gracefully if not installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logging.warning("python-dotenv not installed, using environment variables as is")

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Personalized Learning Co-pilot"
    API_VERSION: str = "v1"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    
    # Legacy Authentication Settings (for backward compatibility)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your_secret_key_here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # Entra ID / Microsoft Identity Settings
    TENANT_ID: str = os.getenv("MS_TENANT_ID", "")
    CLIENT_ID: str = os.getenv("MS_CLIENT_ID", "")
    CLIENT_SECRET: str = os.getenv("MS_CLIENT_SECRET", "")
    REDIRECT_URI: str = os.getenv("MS_REDIRECT_URI", "http://localhost:3000/auth/callback")
    
    # API Scopes
    API_SCOPE: str = os.getenv("API_SCOPE", "api://{CLIENT_ID}/user_impersonation")
    
    # Frontend URL for CORS and redirects
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Azure AI Search Settings
    AZURE_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    AZURE_SEARCH_KEY: str = os.getenv("AZURE_SEARCH_KEY", "")
    AZURE_SEARCH_INDEX_NAME: str = os.getenv("AZURE_SEARCH_INDEX_NAME", "educational-content")
    
    # Azure AI Search Indexes
    CONTENT_INDEX_NAME: str = os.getenv("AZURE_SEARCH_CONTENT_INDEX", "educational-content")
    USERS_INDEX_NAME: str = os.getenv("AZURE_SEARCH_USERS_INDEX", "user-profiles")
    PLANS_INDEX_NAME: str = os.getenv("AZURE_SEARCH_PLANS_INDEX", "learning-plans")
    REPORTS_INDEX_NAME: str = os.getenv("AZURE_SEARCH_REPORTS_INDEX", "student-reports")
    
    # Azure OpenAI Settings 
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_KEY: str = os.getenv("AZURE_OPENAI_KEY", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
    
    # OpenAI API Settings (used by some components)
    OPENAI_API_TYPE: str = os.getenv("OPENAI_API_TYPE", "azure")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", AZURE_OPENAI_ENDPOINT)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", AZURE_OPENAI_KEY)
    OPENAI_API_VERSION: str = os.getenv("OPENAI_API_VERSION", AZURE_OPENAI_API_VERSION)
    
    # Azure AI Services - Form Recognizer
    FORM_RECOGNIZER_ENDPOINT: str = os.getenv("FORM_RECOGNIZER_ENDPOINT", "")
    FORM_RECOGNIZER_KEY: str = os.getenv("FORM_RECOGNIZER_KEY", "")
    
    # Azure AI Services - Speech Service
    SPEECH_KEY: str = os.getenv("SPEECH_KEY", "")
    SPEECH_REGION: str = os.getenv("SPEECH_REGION", "")
    
    # Student Report Settings
    REPORT_CONTAINER_NAME: str = os.getenv("AZURE_STORAGE_REPORT_CONTAINER", "student-reports")
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    
    # Azure Key Vault for Secrets (Used for encryption keys)
    AZURE_KEYVAULT_URL: str = os.getenv("AZURE_KEYVAULT_URL", "")
    AZURE_KEYVAULT_SECRET_NAME: str = os.getenv("AZURE_KEYVAULT_SECRET_NAME", "student-report-encryption-key")
    
    # Helper methods for OpenAI integration
    def get_openai_endpoint(self) -> str:
        """Get the OpenAI endpoint, using Cognitive Services endpoint if OpenAI-specific is not provided."""
        if self.AZURE_OPENAI_ENDPOINT:
            return self.AZURE_OPENAI_ENDPOINT
        
        # If we don't have cognitive_services module, return default endpoint
        try:
            from backend.utils.cognitive_services import get_service_specific_endpoint
            return get_service_specific_endpoint(self.AZURE_COGNITIVE_ENDPOINT, "openai", self.AZURE_OPENAI_API_VERSION)
        except ImportError:
            return self.AZURE_COGNITIVE_ENDPOINT
    
    def get_openai_key(self) -> str:
        """Get the OpenAI key, using Cognitive Services key if OpenAI-specific is not provided."""
        if self.AZURE_OPENAI_KEY:
            return self.AZURE_OPENAI_KEY
        return self.AZURE_COGNITIVE_KEY
    
    # CORS Settings
    @property
    def CORS_ORIGINS(self) -> List[str]:
        default_origins = [
            "http://localhost:3000",  # React frontend
            "http://localhost:8000",  # FastAPI backend (for development)
            self.FRONTEND_URL  # Configured frontend URL
        ]
        
        # Get additional origins from environment
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            try:
                # Try to parse as comma-separated string
                additional_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
                default_origins.extend(additional_origins)
            except Exception as e:
                logging.warning(f"Error parsing CORS_ORIGINS: {e}")
        
        # Remove duplicates and empty strings
        return list(set([origin for origin in default_origins if origin]))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Content Scraper Settings
    SCRAPER_RATE_LIMIT: float = float(os.getenv("SCRAPER_RATE_LIMIT", "1.0"))  # seconds between requests
    USER_AGENT: str = os.getenv("USER_AGENT", "PersonalizedLearningCopilot/1.0")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()