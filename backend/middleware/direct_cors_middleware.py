"""Direct CORS middleware to ensure all requests get proper CORS headers."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging
from typing import List

logger = logging.getLogger(__name__)

class DirectCorsMiddleware(BaseHTTPMiddleware):
    """
    A more direct CORS middleware that adds headers to all responses.
    This ensures even error responses get proper CORS headers.
    """
    
    def __init__(self, app, allowed_origins=None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
        logger.info(f"DirectCorsMiddleware initialized with origins: {self.allowed_origins}")
    
    async def dispatch(self, request: Request, call_next):
        # Get the origin from the request
        origin = request.headers.get("origin")
        
        # If no origin or the origin isn't in the allowed list, use "*"
        if not origin:
            logger.debug(f"No origin header found in request to {request.url.path}")
            # Use "*" as default only if we're allowing all origins
            origin = "*" if "*" in self.allowed_origins else self.allowed_origins[0]
        elif self.allowed_origins != ["*"] and origin not in self.allowed_origins:
            logger.warning(f"Origin {origin} is not in allowed origins for {request.url.path}. Using default.")
            origin = "*" if "*" in self.allowed_origins else self.allowed_origins[0]
        
        # For OPTIONS preflight requests
        if request.method == "OPTIONS":
            logger.info(f"Handling OPTIONS preflight request from origin: {origin}")
            logger.info(f"Request path: {request.url.path}")
            logger.info(f"Request headers: {dict(request.headers)}")
            
            # Return a proper preflight response
            response = Response(
                status_code=200,
                content="",
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "86400",  # 24 hours
                },
            )
            logger.info(f"Returning preflight response with headers: {dict(response.headers)}")
            return response
        
        # For DELETE requests, log extra info
        if request.method == "DELETE":
            logger.info(f"Processing DELETE request to {request.url.path} from origin: {origin}")
            logger.info(f"DELETE request headers: {dict(request.headers)}")
        
        # For regular requests
        try:
            # Proceed with the request
            response = await call_next(request)
            
            # Add CORS headers to the response
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            
            # Special handling for DELETE responses
            if request.method == "DELETE":
                logger.info(f"Added CORS headers to DELETE response for {request.url.path}")
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")
            
            return response
        except Exception as e:
            # For any exceptions, ensure we still return a response with CORS headers
            logger.error(f"Error in request: {e}")
            
            # Create an error response with CORS headers
            response = Response(
                status_code=500,
                content=f"Internal Server Error: {str(e)}",
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                    "Access-Control-Allow-Headers": "*",
                },
            )
            return response