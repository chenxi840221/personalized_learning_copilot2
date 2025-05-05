"""
API routes for task status tracking.
Allows clients to check on the status of long-running tasks.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import Dict, List, Any, Optional
import logging

from auth.entra_auth import get_current_user
from utils import task_status_tracker

# Setup logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str = Path(..., description="Task ID to check status for"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the status of a task.
    
    Args:
        task_id: The unique identifier for the task
        current_user: Current authenticated user
        
    Returns:
        Task status object
    """
    task_status = task_status_tracker.get_task_status(task_id)
    
    if not task_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
    
    # Check if task belongs to the current user 
    # Administrators can view any task
    if task_status["user_id"] != current_user["id"] and not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this task"
        )
    
    return task_status

@router.get("/")
async def get_user_tasks(
    task_type: Optional[str] = Query(None, description="Filter tasks by type"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all tasks for the current user.
    
    Args:
        task_type: Optional filter by task type
        current_user: Current authenticated user
        
    Returns:
        List of task status objects
    """
    tasks = task_status_tracker.get_user_tasks(current_user["id"], task_type)
    return tasks