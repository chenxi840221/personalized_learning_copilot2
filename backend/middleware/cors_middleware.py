"""Custom CORS middleware to better handle preflight OPTIONS requests."""
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)

def setup_cors(app: FastAPI, allowed_origins: List[str] = None):
    """
    Set up enhanced CORS handling for the FastAPI application.
    
    This adds both the standard FastAPI CORSMiddleware and a custom
    middleware to properly handle preflight OPTIONS requests.
    
    Args:
        app: FastAPI application instance
        allowed_origins: List of allowed origins, or None to allow all
    """
    # If allowed_origins is None or empty, allow all origins with "*"
    if not allowed_origins:
        allowed_origins = ["*"]
        
    # Add standard CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        max_age=86400,  # 24 hours for preflight caching
    )
    
    # Add custom preflight handler
    app.add_middleware(PreflightOptionsMiddleware)
    
    logger.info(f"CORS setup completed with allowed origins: {allowed_origins}")

class PreflightOptionsMiddleware(BaseHTTPMiddleware):
    """
    Custom middleware to handle preflight OPTIONS requests.
    
    This addresses potential issues with CORS preflight requests
    by ensuring the OPTIONS method is properly handled.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Handle OPTIONS requests
        if request.method == "OPTIONS":
            # Log preflight request
            origin = request.headers.get("origin", "unknown")
            logger.info(f"Handling OPTIONS preflight request from origin: {origin}")
            logger.info(f"Request path: {request.url.path}")
            
            # Create response with appropriate CORS headers
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
            return response
            
        # For regular requests, add CORS headers to the response
        response = await call_next(request)
        
        # Add CORS headers to every response to ensure they are always present
        origin = request.headers.get("origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response