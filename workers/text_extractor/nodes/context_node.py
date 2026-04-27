from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.services.database import fetch_recent_tasks
from workers.text_extractor.core.logger import logger
import asyncio


def fetch_context(state: AgentState) -> AgentState:
    """Fetch recent tasks for pronoun resolution context."""
    group_id = state.get("group_id")
    
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
        else:
            state["db_context"] = "No recent tasks found."
        
        logger.info("Context Node completed", extra={
            "node": "context_node",
            "tasks_count": len(tasks),
            "db_context_length": len(state["db_context"])
        })
            
    except Exception as e:
        logger.error("Context Node error", extra={
            "node": "context_node",
            "error": str(e)
        }, exc_info=True)
        state["db_context"] = ""
    
    return state
