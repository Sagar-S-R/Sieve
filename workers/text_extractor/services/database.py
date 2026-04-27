"""Simple database service - mock for now."""
import time
from workers.text_extractor.core.metrics import db_operation_latency

async def fetch_recent_tasks(group_id: int, limit: int = 10):
    """
    Mock: Fetch recent tasks from database.
    TODO: Implement with asyncpg.
    """
    start_time = time.time()
    try:
        # SQL: SELECT * FROM tasks WHERE group_id = $1 ORDER BY created_at DESC LIMIT $2
        result = []
        return result
    finally:
        duration = time.time() - start_time
        db_operation_latency.labels(operation="fetch_recent_tasks").observe(duration)


async def save_task(task_data: dict):
    """
    Mock: Save task to database.
    TODO: Implement with asyncpg.
    """
    start_time = time.time()
    try:
        # SQL: INSERT INTO tasks (user_id, group_id, title, action_required, deadline) VALUES (...)
        print(f"[DB] Task saved: {task_data}")
        return 1  # Mock task_id
    finally:
        duration = time.time() - start_time
        db_operation_latency.labels(operation="save_task").observe(duration)
