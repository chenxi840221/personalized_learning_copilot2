# backend/api/debug_cors_routes.py
from fastapi import APIRouter, Request, Response, Header
from typing import Dict, List, Any, Optional
import logging

# Setup logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/debug/cors", tags=["debug-cors"])

@router.options("/{path:path}")
async def cors_preflight(
    request: Request,
    path: str
):
    """
    Handle OPTIONS preflight requests for any path.
    This is a debug endpoint to help diagnose CORS issues.
    """
    # Log the request details
    logger.info(f"DEBUG: CORS preflight request for path: {path}")
    logger.info(f"DEBUG: Method: {request.method}")
    logger.info(f"DEBUG: Headers: {dict(request.headers)}")
    
    # Get origin from headers
    origin = request.headers.get("origin", "*")
    
    # Create response with CORS headers
    response = Response(
        status_code=200,
        content="",
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400",  # 24 hours for preflight caching
        },
    )
    
    # Log the response
    logger.info(f"DEBUG: CORS preflight response headers: {dict(response.headers)}")
    
    return response

@router.get("/test", response_model=Dict[str, Any])
async def test_cors(request: Request):
    """
    Test endpoint for CORS issues.
    Returns the request headers and information for debugging.
    """
    return {
        "status": "ok",
        "request_headers": dict(request.headers),
        "method": request.method,
        "url": str(request.url),
        "client": request.client.host if request.client else None
    }

@router.delete("/test", response_model=Dict[str, str])
async def test_delete_cors(request: Request):
    """
    Test DELETE endpoint for CORS issues.
    """
    return {
        "status": "ok",
        "message": "DELETE request successful"
    }