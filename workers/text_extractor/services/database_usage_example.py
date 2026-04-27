"""
Example usage of the database service.
This file demonstrates how to initialize and use the database service.
"""
import asyncio
from workers.text_extractor.services.database import (
    init_pool,
    close_pool,
    fetch_recent_tasks,
    save_task,
    DatabaseError,
    ConnectionError,
    QueryError
)
from workers.text_extractor.core.config import settings


async def example_usage():
    """Example of how to use the database service."""
    
    # 1. Initialize the connection pool (do this once at startup)
    try:
        await init_pool(
            database_url=settings.DATABASE_URL,
            min_size=settings.DB_POOL_MIN_SIZE,
            max_size=settings.DB_POOL_MAX_SIZE
        )
        print("✓ Database connection pool initialized")
    except ConnectionError as e:
        print(f"✗ Failed to initialize database: {e}")
        return
    
    try:
        # 2. Fetch recent tasks for a group
        group_id = 123456789
        tasks = await fetch_recent_tasks(group_id, limit=10)
        print(f"✓ Fetched {len(tasks)} recent tasks for group {group_id}")
        
        for task in tasks:
            print(f"  - Task {task['id']}: {task['title']}")
            print(f"    Action: {task['action_required']}")
            print(f"    Deadline: {task['deadline']}")
        
        # 3. Save a new task
        task_data = {
            'user_id': 987654321,
            'group_id': group_id,
            'title': 'Review PR #123',
            'action_required': 'Review and approve the pull request',
            'deadline': None  # Optional field
        }
        
        task_id = await save_task(task_data)
        print(f"✓ Saved new task with ID: {task_id}")
        
    except QueryError as e:
        print(f"✗ Database query failed: {e}")
    except ValueError as e:
        print(f"✗ Invalid task data: {e}")
    except DatabaseError as e:
        print(f"✗ Database error: {e}")
    finally:
        # 4. Close the connection pool (do this at shutdown)
        await close_pool()
        print("✓ Database connection pool closed")


async def example_with_context_node():
    """Example of how the Context Node would use the database service."""
    
    # Initialize pool (already done at startup in main.py)
    await init_pool(settings.DATABASE_URL, settings.DB_POOL_MIN_SIZE, settings.DB_POOL_MAX_SIZE)
    
    try:
        # Fetch recent tasks for context
        group_id = 123456789
        tasks = await fetch_recent_tasks(group_id)
        
        # Format context for LLM
        if tasks:
            context_lines = ["Recent tasks in this group:"]
            for task in tasks:
                deadline_str = task['deadline'].strftime('%Y-%m-%d') if task['deadline'] else 'No deadline'
                context_lines.append(f"- {task['title']} (Deadline: {deadline_str})")
            
            db_context = "\n".join(context_lines)
        else:
            db_context = "No recent tasks found."
        
        print(f"Context for LLM:\n{db_context}")
        
    except QueryError as e:
        # Handle error gracefully - set empty context
        print(f"Failed to fetch context: {e}")
        db_context = ""
    
    await close_pool()


async def example_error_handling():
    """Example of error handling patterns."""
    
    # Example 1: Missing required fields
    try:
        invalid_task = {
            'user_id': 123,
            'title': 'Incomplete task'
            # Missing group_id and action_required
        }
        await save_task(invalid_task)
    except ValueError as e:
        print(f"✓ Caught validation error: {e}")
    
    # Example 2: Pool not initialized
    try:
        await fetch_recent_tasks(123)
    except ConnectionError as e:
        print(f"✓ Caught connection error: {e}")
    
    # Example 3: Query failure (simulated)
    try:
        await init_pool(settings.DATABASE_URL)
        # If query fails, QueryError will be raised
        tasks = await fetch_recent_tasks(-1)  # Invalid group_id might cause issues
    except QueryError as e:
        print(f"✓ Caught query error: {e}")
    finally:
        await close_pool()


if __name__ == '__main__':
    print("=== Basic Usage Example ===")
    asyncio.run(example_usage())
    
    print("\n=== Context Node Example ===")
    asyncio.run(example_with_context_node())
    
    print("\n=== Error Handling Example ===")
    asyncio.run(example_error_handling())
