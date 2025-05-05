# API Routes (routes.py)
# ./personalized_learning_copilot/backend/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from models.user import User
from models.content import Content
from models.learning_plan import LearningPlan
from auth.authentication import get_current_user
from api.endpoints import (
    get_user_endpoint,
    get_content_endpoint,
    get_recommendations_endpoint,
    search_content_endpoint,
    get_content_by_id_endpoint,
    get_learning_plans_endpoint,
    create_learning_plan_endpoint,
    update_activity_status_endpoint
)
# Create routers
user_router = APIRouter(prefix="/users", tags=["users"])
content_router = APIRouter(prefix="/content", tags=["content"])
learning_plan_router = APIRouter(prefix="/learning-plans", tags=["learning-plans"])
# User routes
user_router.add_api_route("/me", get_user_endpoint, methods=["GET"], response_model=User)
# Content routes
content_router.add_api_route("/", get_content_endpoint, methods=["GET"], response_model=List[Content])
content_router.add_api_route("/recommendations", get_recommendations_endpoint, methods=["GET"], response_model=List[Content])
content_router.add_api_route("/search", search_content_endpoint, methods=["GET"], response_model=List[Content])
content_router.add_api_route("/{content_id}", get_content_by_id_endpoint, methods=["GET"], response_model=Content)
# Learning plan routes
learning_plan_router.add_api_route("/", get_learning_plans_endpoint, methods=["GET"], response_model=List[LearningPlan])
learning_plan_router.add_api_route("/", create_learning_plan_endpoint, methods=["POST"], response_model=LearningPlan)
learning_plan_router.add_api_route("/{plan_id}/activities/{activity_id}", update_activity_status_endpoint, methods=["PUT"])
# Export routers
routers = [
    user_router,
    content_router,
    learning_plan_router
]