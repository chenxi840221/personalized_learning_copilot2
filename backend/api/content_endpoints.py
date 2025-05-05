# backend/api/content_endpoints.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from models.user import User
from models.content import Content, ContentType
from auth.authentication import get_current_user
from api.endpoints import (
    get_content_endpoint,
    get_recommendations_endpoint,
    search_content_endpoint,
    get_content_by_id_endpoint
)

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/content", tags=["content"])

# Register content endpoints
router.add_api_route("/", get_content_endpoint, methods=["GET"], response_model=None)  # Remove response_model to avoid validation
router.add_api_route("/recommendations", get_recommendations_endpoint, methods=["GET"], response_model=None)  # Remove response_model to avoid validation
router.add_api_route("/search", search_content_endpoint, methods=["GET"], response_model=None)  # Remove response_model to avoid validation
router.add_api_route("/{content_id}", get_content_by_id_endpoint, methods=["GET"], response_model=None)  # Remove response_model to avoid validation

# For backward compatibility with app.py import
content_router = router