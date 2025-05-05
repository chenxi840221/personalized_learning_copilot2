# backend/api/debug_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
import logging
import os
import importlib
import sys
import traceback
from typing import Dict, Any, List

from config.settings import Settings
from auth.entra_auth import get_current_user
from services.search_service import get_search_service

# Import settings
settings = Settings()

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/check-indexes")
async def check_indexes(current_user: Dict = Depends(get_current_user)):
    """Check if all required indexes exist in Azure AI Search."""
    logger.info(f"Check indexes request from user: {current_user}")
    
    # Ensure the user is authenticated
    if not current_user or not current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
        
    try:
        # Get search service
        search_service = await get_search_service()
        
        if not search_service:
            logger.error("Search service not available")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"message": "Search service is not available"}
            )
            
        # Check indexes
        indexes_to_check = [
            ("student-reports", settings.REPORTS_INDEX_NAME),
            ("student-profiles", "student-profiles"),
            ("educational-content", settings.CONTENT_INDEX_NAME),
            ("user-profiles", settings.USERS_INDEX_NAME),
            ("learning-plans", settings.PLANS_INDEX_NAME)
        ]
        
        index_status = {}
        
        for index_type, index_name in indexes_to_check:
            if not index_name:
                logger.warning(f"Index name not configured for {index_type}")
                index_status[index_type] = {
                    "name": "Not configured",
                    "exists": False,
                    "error": "Index name not configured"
                }
                continue
                
            try:
                exists = await search_service.check_index_exists(index_name)
                index_status[index_type] = {
                    "name": index_name,
                    "exists": exists,
                    "error": None
                }
            except Exception as e:
                logger.error(f"Error checking index {index_name}: {e}")
                index_status[index_type] = {
                    "name": index_name,
                    "exists": False,
                    "error": str(e)
                }
                
        return {
            "indexes": index_status,
            "azure_search_endpoint": settings.AZURE_SEARCH_ENDPOINT,
            "azure_search_key_configured": bool(settings.AZURE_SEARCH_KEY)
        }
    
    except Exception as e:
        logger.error(f"Error checking indexes: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Error checking indexes: {str(e)}"}
        )

@router.post("/extract-profile/{report_id}")
async def extract_profile(
    report_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Manually extract student profile from a report and index it."""
    logger.info(f"Extract profile request for report_id={report_id} from user_id={current_user.get('id')}")
    
    # Ensure the user is authenticated
    if not current_user or not current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Get search service
        search_service = await get_search_service()
        
        if not search_service:
            logger.error("Search service not available")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"message": "Search service is not available"}
            )
        
        # First get the report data
        filter_expression = f"id eq '{report_id}'"
        try:
            reports = await search_service.search_documents(
                index_name=settings.REPORTS_INDEX_NAME,
                query="*",
                filter=filter_expression,
                top=1
            )
            
            if not reports:
                logger.error(f"Report not found: {report_id}")
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"message": f"Report not found: {report_id}"}
                )
                
            report_data = reports[0]
            logger.info(f"Found report with ID: {report_id}")
            
            # Get the profile manager
            from utils.student_profile_manager import get_student_profile_manager
            profile_manager = await get_student_profile_manager()
            
            if not profile_manager:
                logger.error("Profile manager not available")
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={"message": "Profile manager is not available"}
                )
            
            # Process the profile
            logger.info(f"Extracting profile from report ID: {report_id}")
            profile_result = await profile_manager.create_or_update_student_profile(
                report_data, 
                report_id
            )
            
            if profile_result:
                logger.info(f"Successfully processed student profile for report: {report_id}")
                return {
                    "message": "Profile extraction successful",
                    "profile_id": profile_result.get("id"),
                    "student_name": profile_result.get("full_name"),
                    "profile_data": profile_result
                }
            else:
                logger.error(f"Failed to process student profile for report: {report_id}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"message": "Profile extraction failed"}
                )
            
        except Exception as e:
            logger.error(f"Error retrieving report: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": f"Error retrieving report: {str(e)}"}
            )
    
    except Exception as e:
        logger.error(f"Error extracting profile: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Error extracting profile: {str(e)}"}
        )

@router.post("/recreate-index/{index_type}")
async def recreate_index(
    index_type: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Recreate the specified index in Azure AI Search.
    
    Args:
        index_type: Type of index to recreate (student-reports, student-profiles, etc.)
    """
    logger.info(f"Recreate index request for {index_type} from user: {current_user}")
    
    # Ensure the user is authenticated
    if not current_user or not current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
        
    # Map index types to recreation script functions
    index_scripts = {
        "student-reports": {
            "module": "backend.scripts.update_report_index",
            "function": "update_student_reports_index"
        },
        "student-profiles": {
            "module": "backend.scripts.create_student_profiles_index",
            "function": "create_student_profiles_index"
        }
    }
    
    if index_type not in index_scripts:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": f"Unsupported index type: {index_type}"}
        )
        
    try:
        # Import the script module
        script_info = index_scripts[index_type]
        module_name = script_info["module"]
        function_name = script_info["function"]
        
        try:
            module = importlib.import_module(module_name)
            recreate_function = getattr(module, function_name)
        except (ImportError, AttributeError) as import_err:
            logger.error(f"Error importing index recreation module: {import_err}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": f"Error importing index recreation module: {str(import_err)}"}
            )
            
        # Call the recreation function
        logger.info(f"Recreating index {index_type} using {module_name}.{function_name}")
        result = await recreate_function()
        
        if result:
            logger.info(f"Successfully recreated index {index_type}")
            return {"message": f"Successfully recreated index {index_type}"}
        else:
            logger.error(f"Failed to recreate index {index_type}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": f"Failed to recreate index {index_type}"}
            )
    
    except Exception as e:
        logger.error(f"Error recreating index: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Error recreating index: {str(e)}"}
        )
        
# Add the debug router to app in app.py
debug_router = router