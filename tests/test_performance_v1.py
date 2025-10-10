import pytest
from unittest.mock import patch, MagicMock

from src.services.caching_service import CachingService
from src.services.task_queue import TaskQueueService, celery_app

# --- Caching Service Tests ---

@patch("redis.from_url")
def test_caching_service_get_set(mock_redis_from_url):
    """Test setting and getting a value from the cache"""
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client
    
    caching_service = CachingService()
    
    # Test set
    caching_service.set("test_key", {"data": "test_value"})
    mock_redis_client.setex.assert_called_once()
    
    # Test get (cache hit)
    mock_redis_client.get.return_value = '{"data": "test_value"}'
    result = caching_service.get("test_key")
    assert result == {"data": "test_value"}
    mock_redis_client.get.assert_called_with("test_key")
    
    # Test get (cache miss)
    mock_redis_client.get.return_value = None
    result = caching_service.get("non_existent_key")
    assert result is None

@patch("redis.from_url")
def test_caching_service_delete(mock_redis_from_url):
    """Test deleting a value from the cache"""
    mock_redis_client = MagicMock()
    mock_redis_from_url.return_value = mock_redis_client
    
    caching_service = CachingService()
    caching_service.delete("test_key")
    mock_redis_client.delete.assert_called_once_with("test_key")

# --- Task Queue Service Tests ---

@patch("celery.Celery.send_task")
def test_task_queue_submit_task(mock_send_task):
    """Test submitting a task to the queue"""
    mock_task = MagicMock()
    mock_task.id = "test_task_id"
    mock_send_task.return_value = mock_task
    
    task_queue_service = TaskQueueService(celery_app)
    task_id = task_queue_service.submit_task("tasks.test_task", 1, 2, kwarg1="a")
    
    assert task_id == "test_task_id"
    mock_send_task.assert_called_once_with("tasks.test_task", args=(1, 2), kwargs={"kwarg1": "a"})

@patch("celery.Celery.AsyncResult")
def test_task_queue_get_task_status(mock_async_result):
    """Test getting the status of a task"""
    mock_result = MagicMock()
    mock_result.status = "SUCCESS"
    mock_result.successful.return_value = True
    mock_result.result = {"output": "done"}
    mock_async_result.return_value = mock_result
    
    task_queue_service = TaskQueueService(celery_app)
    status = task_queue_service.get_task_status("test_task_id")
    
    assert status["status"] == "SUCCESS"
    assert status["result"] == {"output": "done"}
    mock_async_result.assert_called_once_with("test_task_id")

