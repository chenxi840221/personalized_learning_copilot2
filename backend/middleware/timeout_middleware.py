"""
Timeout middleware for extending request timeouts for specific endpoints.
"""
from typing import Dict, Callable, Set, Optional
import asyncio
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from starlette.types import ASGIApp

# Configure logger
logger = logging.getLogger(__name__)

class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware to override timeouts for specific endpoints.
    This allows learning plan creation to have a longer timeout.
    """
    
    def __init__(
        self, 
        app: ASGIApp, 
        timeout_paths: Dict[str, int],
        path_prefixes: Optional[Dict[str, int]] = None,
        default_timeout: int = 60
    ):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI app
            timeout_paths: Dictionary of exact paths and their timeouts in seconds
            path_prefixes: Dictionary of path prefixes and their timeouts in seconds
            default_timeout: Default timeout for all other paths
        """
        super().__init__(app)
        self.timeout_paths = timeout_paths
        self.path_prefixes = path_prefixes or {}
        self.default_timeout = default_timeout
        
        # Log the configured timeouts
        logger.info(f"Timeout middleware configured:")
        logger.info(f"Default timeout: {default_timeout} seconds")
        logger.info(f"Path timeouts: {timeout_paths}")
        logger.info(f"Prefix timeouts: {path_prefixes}")
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process the request and apply the appropriate timeout.
        
        Args:
            request: The incoming request
            call_next: The next middleware in the chain
            
        Returns:
            The response from downstream middleware
        """
        # Get the path
        path = request.url.path
        
        # Determine the timeout for this path
        timeout = self.default_timeout
        
        # Check exact path matches
        if path in self.timeout_paths:
            timeout = self.timeout_paths[path]
            logger.debug(f"Using exact path timeout for {path}: {timeout}s")
        else:
            # Check prefix matches
            for prefix, prefix_timeout in self.path_prefixes.items():
                if path.startswith(prefix):
                    timeout = prefix_timeout
                    logger.debug(f"Using prefix timeout for {path} (matches {prefix}): {timeout}s")
                    break
        
        # Create a task for the next middleware
        action_task = asyncio.create_task(call_next(request))
        
        # Set up a timeout
        try:
            # Wait for the task with a timeout
            response = await asyncio.wait_for(action_task, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            # Cancel the task if it times out
            action_task.cancel()
            
            # Return a timeout error response
            logger.error(f"Request timed out after {timeout}s: {request.method} {path}")
            
            # Create a JSON response with proper CORS headers
            return Response(
                content='{"detail":"Request timed out"}',
                status_code=504,
                media_type="application/json",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
            )

def add_timeout_middleware(app: ASGIApp):
    """
    Add timeout middleware to the app.
    
    Args:
        app: FastAPI app
    """
    # Configure longer timeouts for learning plan creation
    app.add_middleware(
        TimeoutMiddleware,
        timeout_paths={
            "/learning-plans": 300,  # 5 minutes for POST to learning-plans
        },
        path_prefixes={
            "/learning-plans/profile-based": 600,  # 10 minutes for profile-based plans
            "/tasks/": 600,  # 10 minutes for long-running tasks
        },
        default_timeout=120  # 2 minutes for most endpoints
    )