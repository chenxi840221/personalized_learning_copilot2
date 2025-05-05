# backend/app.py
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from typing import List, Optional, Dict, Any
import logging
import os

# Import settings
from config.settings import Settings
settings = Settings()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Personalized Learning Co-pilot API",
    description="API for the Personalized Learning Co-pilot with Entra ID Authentication",
    version="0.2.0",
)

# Add direct CORS middleware to handle all responses including errors
from middleware.direct_cors_middleware import DirectCorsMiddleware
# Ensure we add localhost:3000 to allowed origins for development
dev_origins = settings.CORS_ORIGINS or []
if "http://localhost:3000" not in dev_origins:
    dev_origins.append("http://localhost:3000")
if "http://localhost:8001" not in dev_origins:
    dev_origins.append("http://localhost:8001")

# Use our direct CORS middleware
app.add_middleware(DirectCorsMiddleware, allowed_origins=dev_origins)

# Keeping the standard CORS setup as a fallback
from middleware.cors_middleware import setup_cors
setup_cors(app, dev_origins)

# Add timeout middleware for long-running operations
from middleware.timeout_middleware import add_timeout_middleware
add_timeout_middleware(app)

# Add resource authorization middleware
from middleware.authorization_middleware import create_authorization_middleware
from services.search_service import get_search_service
app.add_middleware(create_authorization_middleware(get_search_service))

# Import API routes
from api.auth_routes import router as auth_router
from api.learning_plan_routes import router as learning_plan_router
from api.student_report_routes import student_report_router
from api.student_profile_routes import student_profile_router
from api.debug_routes import debug_router
from api.direct_profile_indexer import direct_index_router
from api.user_routes import router as user_router
from api.task_status_routes import router as task_status_router
from api.debug_cors_routes import router as debug_cors_router

# Import AI routes if available
try:
    from api.content_endpoints import content_router
    has_content_endpoints = True
except ImportError:
    has_content_endpoints = False
    logger.warning("Content endpoints not available")

try:
    from api.azure_langchain_routes import azure_langchain_router
    has_langchain_endpoints = True
except ImportError:
    has_langchain_endpoints = False
    logger.warning("Azure LangChain endpoints not available")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Initialize Azure LangChain integration if available
    try:
        from rag.azure_langchain_integration import get_azure_langchain
        azure_langchain = await get_azure_langchain()
        logger.info("Azure LangChain integration initialized")
    except Exception as e:
        logger.warning(f"Could not initialize Azure LangChain integration: {e}")
    
    # Initialize LangChain service if available
    try:
        from services.azure_langchain_service import get_azure_langchain_service
        langchain_service = await get_azure_langchain_service()
        logger.info("Azure LangChain service initialized")
    except Exception as e:
        logger.warning(f"Could not initialize Azure LangChain service: {e}")
    
    # Initialize Learning Plan service
    try:
        from services.azure_learning_plan_service import get_learning_plan_service
        learning_plan_service = await get_learning_plan_service()
        logger.info("Azure Learning Plan service initialized")
    except Exception as e:
        logger.warning(f"Could not initialize Learning Plan service: {e}")
    
    # Start task status cleanup
    import asyncio
    from utils.task_status_tracker import start_cleanup_job
    asyncio.create_task(start_cleanup_job())
    logger.info("Task status cleanup job started")
    
    logger.info(f"Server started with Entra ID authentication")
    logger.info(f"Client ID: {settings.CLIENT_ID}")
    logger.info(f"Tenant ID: {settings.TENANT_ID}")

# Include routers
app.include_router(auth_router)
app.include_router(learning_plan_router)
app.include_router(user_router)  # Include the user router
app.include_router(student_report_router)  # Include student report router
app.include_router(student_profile_router)  # Include student profile router
app.include_router(debug_router)  # Include debug router
app.include_router(direct_index_router)  # Include direct profile indexer
app.include_router(task_status_router)  # Include task status router
app.include_router(debug_cors_router)  # Include debug CORS router

# Include optional routers if available
if has_content_endpoints:
    app.include_router(content_router)
    logger.info("Content router included")

if has_langchain_endpoints:
    app.include_router(azure_langchain_router)
    logger.info("Azure LangChain router included")

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    # Check Azure Search indexes
    from services.search_service import get_search_service
    search_service = await get_search_service()
    
    indexes = {
        "student-reports": False,
        "student-profiles": False,
        "educational-content": False,
        "user-profiles": False,
        "learning-plans": False
    }
    
    if search_service:
        for index_name in indexes.keys():
            try:
                exists = await search_service.check_index_exists(index_name)
                indexes[index_name] = exists
            except:
                pass
    
    return {
        "status": "ok",
        "version": "0.2.0",
        "services": {
            "entra_id": settings.CLIENT_ID != "",
            "azure_search": settings.AZURE_SEARCH_ENDPOINT != "",
            "azure_openai": settings.AZURE_OPENAI_ENDPOINT != "",
            "form_recognizer": settings.FORM_RECOGNIZER_ENDPOINT != ""
        },
        "indexes": indexes,
        "environment": {
            "reports_index": settings.REPORTS_INDEX_NAME,
            "content_index": settings.CONTENT_INDEX_NAME,
            "users_index": settings.USERS_INDEX_NAME,
            "plans_index": settings.PLANS_INDEX_NAME
        }
    }

# Main entrypoint
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)