async def save_task(task_data: dict):
    """
    Mock function to save a task to the database.
    TODO: Implement real SQL logic here using asyncpg or SQLAlchemy.
    
    Expected fields in task_data:
    - user_id (int)
    - group_id (int)
    - title (str)
    - action_required (str)
    - deadline (datetime, optional)
    """
    # SQL: INSERT INTO tasks (user_id, group_id, title, action_required, deadline) 
    #      VALUES ($1, $2, $3, $4, $5) RETURNING id
    print(f"[DB] Task saved: {task_data}")
    return True
