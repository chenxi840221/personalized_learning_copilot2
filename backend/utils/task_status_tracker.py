"""
Task status tracker for long-running processes.
Provides a way to track and report progress of long-running tasks.
"""
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import asyncio
from threading import Lock

# Setup logger
logger = logging.getLogger(__name__)

# In-memory task status store
# Using a simple dictionary with locking for thread safety
_status_store = {}
_store_lock = Lock()

# Task status constants
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress" 
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Cleanup expired tasks after 30 minutes
EXPIRY_TIME_SECONDS = 1800

class TaskStatus:
    """Task status object for tracking long-running operations."""
    
    def __init__(self, task_id: str, user_id: str, task_type: str, params: Optional[Dict[str, Any]] = None):
        """Initialize a new task status."""
        self.task_id = task_id
        self.user_id = user_id
        self.task_type = task_type
        self.status = STATUS_PENDING
        self.progress = 0
        self.message = "Task created"
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at
        self.completed_at = None
        self.result = None
        self.error = None
        self.params = params or {}
        self.steps = []
        self.current_step = None
        self.total_steps = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task status to dictionary."""
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
            "steps": self.steps,
            "current_step": self.current_step,
            "total_steps": self.total_steps
        }
    
    def update(self, 
               status: Optional[str] = None, 
               progress: Optional[int] = None, 
               message: Optional[str] = None,
               result: Optional[Dict[str, Any]] = None,
               error: Optional[str] = None,
               current_step: Optional[str] = None) -> None:
        """Update task status."""
        if status:
            self.status = status
        if progress is not None:
            self.progress = progress
        if message:
            self.message = message
        if result:
            self.result = result
        if error:
            self.error = error
        if current_step:
            self.current_step = current_step
            # Add step to steps list if not already there
            if current_step not in self.steps:
                self.steps.append(current_step)
        
        self.updated_at = datetime.utcnow().isoformat()
        
        # Set completed_at when task is completed or failed
        if status in [STATUS_COMPLETED, STATUS_FAILED] and not self.completed_at:
            self.completed_at = self.updated_at


def create_task(user_id: str, task_type: str, params: Optional[Dict[str, Any]] = None) -> str:
    """Create a new task and return its ID."""
    task_id = str(uuid.uuid4())
    task = TaskStatus(task_id, user_id, task_type, params)
    
    with _store_lock:
        _status_store[task_id] = task
    
    logger.info(f"Created task {task_id} of type {task_type} for user {user_id}")
    return task_id


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a task by ID."""
    with _store_lock:
        task = _status_store.get(task_id)
    
    if task:
        return task.to_dict()
    return None


def update_task_status(task_id: str, 
                      status: Optional[str] = None, 
                      progress: Optional[int] = None, 
                      message: Optional[str] = None,
                      result: Optional[Dict[str, Any]] = None,
                      error: Optional[str] = None,
                      current_step: Optional[str] = None) -> bool:
    """Update the status of a task. Returns True if task was found and updated."""
    with _store_lock:
        task = _status_store.get(task_id)
        if not task:
            return False
        
        task.update(status, progress, message, result, error, current_step)
    
    logger.debug(f"Updated task {task_id} status: {status}, progress: {progress}, message: {message}")
    return True


def get_user_tasks(user_id: str, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all tasks for a specific user, optionally filtered by type."""
    tasks = []
    
    with _store_lock:
        for task in _status_store.values():
            if task.user_id == user_id:
                if task_type is None or task.task_type == task_type:
                    tasks.append(task.to_dict())
    
    return tasks


def cleanup_expired_tasks():
    """Remove expired tasks from the store."""
    now = datetime.utcnow()
    expired_tasks = []
    
    with _store_lock:
        for task_id, task in list(_status_store.items()):
            # Parse updated_at timestamp
            updated_at = datetime.fromisoformat(task.updated_at)
            seconds_since_update = (now - updated_at).total_seconds()
            
            # Remove completed/failed tasks after EXPIRY_TIME_SECONDS
            if ((task.status in [STATUS_COMPLETED, STATUS_FAILED] and seconds_since_update > EXPIRY_TIME_SECONDS) or
                # Remove any task not updated for twice the expiry time
                seconds_since_update > EXPIRY_TIME_SECONDS * 2):
                expired_tasks.append(task_id)
        
        # Remove expired tasks
        for task_id in expired_tasks:
            del _status_store[task_id]
    
    if expired_tasks:
        logger.info(f"Cleaned up {len(expired_tasks)} expired tasks")


async def start_cleanup_job():
    """Start a background task to periodically clean up expired tasks."""
    logger.info("Starting task status cleanup job")
    while True:
        try:
            cleanup_expired_tasks()
        except Exception as e:
            logger.error(f"Error in task status cleanup: {e}")
        
        # Run cleanup every 5 minutes
        await asyncio.sleep(300)


def get_task_count() -> int:
    """Get the current number of tasks in the store."""
    with _store_lock:
        return len(_status_store)