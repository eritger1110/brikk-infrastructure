# -*- coding: utf-8 -*-
"""
Task Queue Service

Provides an interface for adding tasks to a background processing queue (e.g., Celery).
"""

import os
from typing import Any, Dict

from celery import Celery
from src.services.structured_logging import get_logger

logger = get_logger("brikk.tasks")

# Configure Celery
celery_app = Celery(
    "brikk_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/2"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/3"),
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


class TaskQueueService:
    """Service for managing asynchronous tasks"""

    def __init__(self, app: Celery):
        self.app = app

    def submit_task(self, task_name: str, *args, **kwargs) -> str:
        """Submit a task to the queue"""
        try:
            task = self.app.send_task(task_name, args=args, kwargs=kwargs)
            logger.info(f"Submitted task {task_name} with ID: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to submit task {task_name}: {e}")
            raise

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task"""
        try:
            result = self.app.AsyncResult(task_id)
            return {
                "id": task_id,
                "status": result.status,
                "result": result.result if result.successful() else str(
                    result.info),
            }
        except Exception as e:
            logger.error(f"Failed to get status for task {task_id}: {e}")
            return {"id": task_id, "status": "UNKNOWN", "error": str(e)}

# --- Example Tasks ---


@celery_app.task(name="tasks.send_webhook")
def send_webhook_task(event_id: int):
    """Celery task to send a webhook event"""
    from src.services.webhook_service import WebhookService
    from src.database import get_db

    logger.info(f"Processing webhook event task for event ID: {event_id}")
    db_session = next(get_db())
    webhook_service = WebhookService(db_session)
    webhook_service.send_webhook_event(event_id)


@celery_app.task(name="tasks.process_analytics")
def process_analytics_task(time_range_hours: int):
    """Celery task to process performance analytics"""
    from src.services.monitoring_service import monitoring_service

    logger.info(
        f"Processing analytics task for time range: {time_range_hours} hours")
    monitoring_service.get_performance_analytics(time_range_hours)


# Global task queue service instance
task_queue_service = TaskQueueService(celery_app)
