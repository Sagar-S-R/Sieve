from workers.text_extractor.graph.state import AgentState
from shared.redis_client import get_raw_message_window
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
import json


async def fetch_context_agentic(state: AgentState) -> AgentState:
    """
    Agentic context fetching: LLM decides what context to retrieve based on intent and message.
    
    New flow:
    1. Get rolling message buffer (last 20 messages from Redis)
    2. Pass buffer + current message + intent to LLM
    3. LLM decides: what DB queries to run (recent tasks? specific title search? none?)
    4. Execute queries based on LLM decision
    5. Return enriched context
    """
    group_id = state.get("group_id")
    message_text = state.get("message_text", "")
    intent = state.get("intent", "UNKNOWN")

    logger.info("Context Node (Agentic) started", extra={
        "node": "context_node",
        "group_id": group_id,
        "intent": intent
    })

    # Personal tasks — no group history, skip all context fetching
    if state.get("is_personal", False):
        state["db_context"] = ""
        state["message_buffer"] = []
        state["context_retrieval_reasoning"] = "Personal task — skipping group context fetch"
        logger.info("Context Node completed - personal task", extra={"node": "context_node"})
        return state

    if not group_id:
        state["db_context"] = ""
        state["message_buffer"] = []
        state["context_retrieval_reasoning"] = "No group_id provided"
        logger.info("Context Node completed - no group_id", extra={"node": "context_node"})
        return state

    
    # Step 1: Get rolling message buffer
    message_buffer = await get_raw_message_window(group_id, limit=20)
    state["message_buffer"] = message_buffer
    
    logger.info(f"Retrieved {len(message_buffer)} messages from buffer", extra={"node": "context_node"})
    
    # Step 2: Ask LLM what context to fetch
    buffer_text = "\n".join([f"- {msg}" for msg in message_buffer[-10:]])  # Last 10 for context
    
    context_decision_prompt = f"""You are a context retrieval agent for a university group chat reminder bot.

**Current Situation:**
- Intent: {intent}
- Current message: "{message_text}"

**Recent chat history (last 10 messages):**
{buffer_text if buffer_text else "(empty)"}

**Your task:**
Decide what database context (if any) should be fetched to process this message correctly.

**Available queries:**
1. RECENT_TASKS - Fetch last 10 tasks from this group (for pronoun resolution, updates, corrections)
2. SEARCH_BY_TITLE - Search for tasks matching a specific title (for UPDATE intent)
3. NONE - No database context needed (for NEW tasks with no dependencies)

**Decision rules:**
- UPDATE intent → ALWAYS use SEARCH_BY_TITLE (extract likely title from message)
- NEW intent → use RECENT_TASKS only if message has pronouns ("it", "that", "the assignment")
- CHITCHAT, QUERY → use NONE
- VENUE_CHANGE, SCHEDULE_CHANGE → use RECENT_TASKS (need to find what's being changed)
- ANNOUNCEMENT → use NONE

Respond with ONLY a JSON object:
{{
    "query_type": "RECENT_TASKS" | "SEARCH_BY_TITLE" | "NONE",
    "search_title": "extracted title if SEARCH_BY_TITLE, null otherwise",
    "reasoning": "one line explaining your decision"
}}"""

    try:
        response = await llm.ainvoke(context_decision_prompt)
        content = response.content.strip()
        
        # Strip markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        decision = json.loads(content)
        query_type = decision.get("query_type", "NONE")
        search_title = decision.get("search_title")
        reasoning = decision.get("reasoning", "")
        
        logger.info(f"LLM context decision: {query_type} | {reasoning}", extra={"node": "context_node"})
        
        state["context_retrieval_reasoning"] = reasoning
        
        # Get excluded_task_ids from state
        excluded = state.get("excluded_task_ids", [])
        
        # Step 3: Execute the decided query
        if query_type == "RECENT_TASKS":
            from shared.database import fetch_recent_tasks
            
            tasks = await fetch_recent_tasks(group_id, limit=10, excluded_task_ids=excluded)
            
            if tasks:
                context_lines = ["Recent tasks from this group:"]
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
        
        elif query_type == "SEARCH_BY_TITLE":
            if not search_title:
                logger.warning("SEARCH_BY_TITLE requested but no title provided", extra={"node": "context_node"})
                state["db_context"] = "No search title provided."
            else:
                from shared.database import search_tasks_by_title_fuzzy
                
                # Fuzzy search for matching tasks (with exclusions)
                matching_tasks = await search_tasks_by_title_fuzzy(group_id, search_title, limit=5, excluded_task_ids=excluded)
                
                if matching_tasks:
                    state["update_candidates"] = matching_tasks  # Store for confirmation flow
                    
                    context_lines = [f"Found {len(matching_tasks)} potential matching tasks:"]
                    for i, task in enumerate(matching_tasks, 1):
                        title = task.get("title", "Untitled")
                        deadline = task.get("deadline")
                        match_score = task.get("similarity", 0.0)
                        context_lines.append(f"{i}. {title} (deadline: {deadline}, match: {match_score:.2f})")
                    
                    state["db_context"] = "\n".join(context_lines)
                    logger.info(f"Found {len(matching_tasks)} candidates for UPDATE", extra={"node": "context_node"})
                else:
                    state["db_context"] = f"No tasks found matching '{search_title}'. Treating as NEW task."
                    state["intent"] = "NEW"  # Fallback to NEW if no match
                    logger.info("No UPDATE candidates found, falling back to NEW", extra={"node": "context_node"})
        
        else:  # NONE
            state["db_context"] = ""
    
    except Exception as e:
        logger.error(f"Context decision LLM failed: {e}", extra={"node": "context_node"}, exc_info=True)
        state["db_context"] = ""
        state["context_retrieval_reasoning"] = f"Error: {str(e)}"
    
    logger.info("Context Node (Agentic) completed", extra={
        "node": "context_node",
        "db_context_length": len(state.get("db_context", "")),
        "message_buffer_size": len(state.get("message_buffer", []))
    })
    
    return state
