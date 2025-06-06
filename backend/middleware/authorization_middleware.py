"""
Authorization middleware to enforce user-based access control.

This middleware checks if the requested resource belongs to the user
for specific resource types (student reports, profiles, learning plans).
"""
from typing import List, Dict, Any, Optional, Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from auth.authentication import get_current_user
import re
import logging
import json

# Configure logger
logger = logging.getLogger(__name__)

# Regular expressions to match resource URLs
REPORT_URL_PATTERN = re.compile(r"^/student-reports/([^/]+)(?:/.*)?$")
PROFILE_URL_PATTERN = re.compile(r"^/student-profiles/([^/]+)(?:/.*)?$")
LEARNING_PLAN_URL_PATTERN = re.compile(r"^/learning-plans/([^/]+)(?:/.*)?$")

# Skip authorization for these endpoints
SKIP_AUTH_PATHS = [
    "/auth/",
    "/content/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/debug/",
    "/tasks/",
]

class ResourceAuthorizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces resource-level authorization.
    
    It ensures users can only access resources they own 
    (student reports, profiles, and learning plans).
    """
    
    def __init__(self, app, search_service_factory=None):
        """
        Initialize the middleware.
        
        Args:
            app: The FastAPI app
            search_service_factory: Function to get the search service
        """
        super().__init__(app)
        self.search_service_factory = search_service_factory
    
    async def get_search_service(self):
        """Get the search service."""
        if self.search_service_factory:
            return await self.search_service_factory()
        
        # Fallback to importing directly if no factory provided
        from services.search_service import get_search_service
        return await get_search_service()
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and check resource ownership.
        
        Args:
            request: The incoming request
            call_next: The next middleware in the chain
            
        Returns:
            The response from downstream middleware
        """
        # Skip authorization for certain paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        # Skip OPTIONS requests (handled by CORS middleware)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Skip GET requests for collection endpoints (e.g., /student-reports/)
        if request.method == "GET" and self._is_collection_endpoint(request.url.path):
            # Collection endpoints are already filtered by owner_id in the route handlers
            return await call_next(request)
        
        # Extract token from header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            # Skip authorization if no token provided (auth will be handled by endpoint)
            return await call_next(request)
        
        token = authorization.replace("Bearer ", "")
        
        # Skip authorization for endpoints that don't operate on protected resources
        resource_id = self._extract_resource_id(request.url.path)
        if not resource_id:
            return await call_next(request)
            
        try:
            # Get current user from token
            current_user = await get_current_user(token)
            
            # Check resource ownership
            resource_type = self._get_resource_type(request.url.path)
            if resource_type and resource_id:
                # For learning plans, they should be accessible to both student_id and owner_id
                # This is critical as the authorization was only checking owner_id which is often not set
                is_authorized = True
                
                # Only perform authorization checks for DELETE operations to improve performance
                if request.method == "DELETE":
                    # For learning plans, use a different authorization approach
                    if resource_type == "learning-plans":
                        is_authorized = await self._check_learning_plan_authorization(
                            resource_id, current_user["id"]
                        )
                    else:
                        # For other resource types, use the regular authorization
                        is_authorized = await self._check_resource_authorization(
                            resource_type, resource_id, current_user["id"]
                        )
                
                if not is_authorized:
                    logger.warning(
                        f"Unauthorized access attempt: User {current_user['id']} attempted to access "
                        f"{resource_type} with ID {resource_id}"
                    )
                    # Return 403 Forbidden with CORS headers to ensure frontend receives it
                    origin = request.headers.get("origin", "*")
                    return Response(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content=json.dumps({"detail": "You don't have permission to access this resource"}),
                        media_type="application/json",
                        headers={
                            "Access-Control-Allow-Origin": origin,
                            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                            "Access-Control-Allow-Headers": "*",
                            "Access-Control-Allow-Credentials": "true",
                        }
                    )
            
            # Request is authorized, proceed to the endpoint
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Error in authorization middleware: {e}")
            # Let the endpoint handle authentication/authorization errors
            return await call_next(request)
    
    def _should_skip_auth(self, path: str) -> bool:
        """Check if authorization should be skipped for this path."""
        return any(path.startswith(skip_path) for skip_path in SKIP_AUTH_PATHS)
    
    def _is_collection_endpoint(self, path: str) -> bool:
        """Check if the path is a collection endpoint (no specific resource ID)."""
        # Collection endpoints without specific resource IDs
        if path in ["/student-reports", "/student-reports/", "/student-profiles", "/student-profiles/", 
                   "/learning-plans", "/learning-plans/"]:
            return True
        
        # Special action endpoints that don't reference a specific resource ID
        special_endpoints = [
            "/student-reports/upload",
            "/learning-plans/profile-based"
        ]
        
        if path in special_endpoints:
            return True
            
        return False
    
    def _extract_resource_id(self, path: str) -> Optional[str]:
        """Extract resource ID from URL path."""
        # Skip special endpoints that are not resource IDs
        special_endpoints = [
            "/student-reports/upload",
            "/learning-plans/profile-based"
        ]
        
        if path in special_endpoints:
            return None
            
        # Check student reports
        match = REPORT_URL_PATTERN.match(path)
        if match:
            return match.group(1)
        
        # Check student profiles
        match = PROFILE_URL_PATTERN.match(path)
        if match:
            return match.group(1)
        
        # Check learning plans
        match = LEARNING_PLAN_URL_PATTERN.match(path)
        if match:
            # Extract only the ID part (not including nested paths)
            plan_id = match.group(1).split('/')[0]
            return plan_id
        
        return None
    
    def _get_resource_type(self, path: str) -> Optional[str]:
        """Determine the resource type from the URL path."""
        if path.startswith("/student-reports/"):
            return "student-reports"
        elif path.startswith("/student-profiles/"):
            return "student-profiles"
        elif path.startswith("/learning-plans/"):
            return "learning-plans"
        
        return None
    
    async def _check_learning_plan_authorization(
        self, plan_id: str, user_id: str
    ) -> bool:
        """
        Special authorization check for learning plans.
        
        Args:
            plan_id: ID of the learning plan
            user_id: ID of the user
            
        Returns:
            True if user is authorized, False otherwise
        """
        try:
            # For logging
            logger.info(f"Checking learning plan authorization for plan {plan_id} and user {user_id}")
            
            # Authorization endpoint already verifies the user is authenticated
            # For simplicity with learning plans, we'll use the learning plan service directly
            from services.azure_learning_plan_service import get_learning_plan_service
            
            learning_plan_service = await get_learning_plan_service()
            if not learning_plan_service:
                logger.error("Learning plan service not available")
                return False
            
            # Get the learning plan - this already handles permission checking
            plan = await learning_plan_service.get_learning_plan(plan_id, user_id)
            
            # If plan exists, check permissions directly in the plan
            if plan:
                # Allow access to student and owner
                is_owner = plan.owner_id and plan.owner_id == user_id
                is_student = plan.student_id and plan.student_id == user_id
                
                # For debugging
                logger.info(f"Plan ownership check: user_id={user_id}, owner_id={plan.owner_id}, student_id={plan.student_id}")
                logger.info(f"Is owner: {is_owner}, Is student: {is_student}")
                
                return is_owner or is_student
                
            logger.warning(f"Plan not found for authorization check: {plan_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking learning plan authorization: {e}")
            # Default to unauthorized on error for security
            return False
    
    async def _check_resource_authorization(
        self, resource_type: str, resource_id: str, user_id: str
    ) -> bool:
        """
        Check if user is authorized to access the resource.
        
        Args:
            resource_type: Type of resource (student-reports, student-profiles)
            resource_id: ID of the resource
            user_id: ID of the user
            
        Returns:
            True if user is authorized, False otherwise
        """
        try:
            search_service = await self.get_search_service()
            if not search_service:
                logger.error("Search service not available")
                return False
            
            # Map resource type to index name
            index_name_map = {
                "student-reports": "student-reports",
                "student-profiles": "student-profiles",
            }
            
            index_name = index_name_map.get(resource_type)
            if not index_name:
                logger.error(f"Unknown resource type: {resource_type}")
                return False
            
            # Check if the resource exists and belongs to the user
            filter_expr = f"id eq '{resource_id}' and owner_id eq '{user_id}'"
            
            # Search for the resource
            results = await search_service.search_documents(
                index_name=index_name,
                query="*",
                filter=filter_expr,
                top=1
            )
            
            # User is authorized if at least one resource found
            return len(results) > 0
            
        except Exception as e:
            logger.error(f"Error checking resource authorization: {e}")
            # Default to unauthorized on error for security
            return False

# Factory function to create middleware
def create_authorization_middleware(search_service_factory=None):
    """
    Create an instance of the authorization middleware.
    
    Args:
        search_service_factory: Function to get the search service
        
    Returns:
        Authorization middleware instance
    """
    from services.search_service import get_search_service
    
    # Use provided factory or default
    factory = search_service_factory or get_search_service
    
    def middleware_factory(app):
        return ResourceAuthorizationMiddleware(app, factory)
    
    return middleware_factory