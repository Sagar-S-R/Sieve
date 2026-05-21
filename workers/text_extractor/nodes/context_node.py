from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.services.database import fetch_recent_tasks
from workers.text_extractor.core.logger import logger
import asyncio
from difflib import SequenceMatcher
from typing import Optional


def detect_update_intent(message_text: str) -> bool:
    """
    Detect if message is updating a previous task.
    
    Args:
        message_text: The message text
        
    Returns:
        True if update detected, False otherwise
    """
    update_keywords = [
        "sorry", "correction", "actually", "change", "update",
        "no wait", "my bad", "wrong", "mistake", "oops",
        "new deadline", "deadline changed", "moved to",
        "extend", "postpone", "reschedule", "shift"
    ]
    
    message_lower = message_text.lower()
    return any(keyword in message_lower for keyword in update_keywords)


def find_matching_task(message_text: str, recent_tasks: list) -> Optional[dict]:
    """
    Find matching task using fuzzy title matching.
    
    Args:
        message_text: The message text
        recent_tasks: List of recent tasks
        
    Returns:
        Best matching task if found, None otherwise
    """
    best_match = None
    best_score = 0
    
    message_lower = message_text.lower()
    
    for task in recent_tasks:
        title_lower = task['title'].lower()
        
        # Calculate similarity score
        score = SequenceMatcher(None, title_lower, message_lower).ratio()
        
        # Update best match if score is higher and above threshold
        if score > best_score and score > 0.6:  # 60% similarity threshold
            best_match = task
            best_score = score
    
    return best_match


def fetch_context(state: AgentState) -> AgentState:
    """Fetch recent tasks for pronoun resolution context and detect updates."""
    group_id = state.get("group_id")
    message_text = state.get("message_text", "")
    
    logger.info("Context Node started", extra={
        "node": "context_node",
        "group_id": group_id
    })
    
    if not group_id:
        state["db_context"] = ""
        logger.info("Context Node completed - no group_id", extra={
            "node": "context_node",
            "db_context": ""
        })
        return state
    
    try:
        tasks = asyncio.run(fetch_recent_tasks(group_id, limit=10))
        
        if tasks:
            context_lines = ["Recent tasks:"]
            for task in tasks:
                title = task.get("title", "Untitled")
                deadline = task.get("deadline")
                if deadline:
                    context_lines.append(f"- {title} (deadline: {deadline})")
                else:
                    context_lines.append(f"- {title}")
            state["db_context"] = "\n".join(context_lines)
            
            # Detect if this is an update message
            is_update = detect_update_intent(message_text)
            
            if is_update:
                # Find matching task
                matching_task = find_matching_task(message_text, tasks)
                
                if matching_task:
                    state['is_update'] = True
                    state['updating_task_title'] = matching_task['title']
                    logger.info(f"[CONTEXT] Detected update for task: {matching_task['title']}", extra={
                        "node": "context_node",
                        "is_update": True,
                        "updating_task_title": matching_task['title']
                    })
        else:
            state["db_context"] = "No recent tasks found."
        
        logger.info("Context Node completed", extra={
            "node": "context_node",
            "tasks_count": len(tasks),
            "db_context_length": len(state["db_context"]),
            "is_update": state.get('is_update', False)
        })
            
    except Exception as e:
        logger.error("Context Node error", extra={
            "node": "context_node",
            "error": str(e)
        }, exc_info=True)
        state["db_context"] = ""
    
    return state
