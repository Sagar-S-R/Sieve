from langgraph.graph import StateGraph, END
from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.nodes.intent_node import classify_intent
from workers.text_extractor.nodes.context_node import fetch_context_agentic
from workers.text_extractor.nodes.extractor_node import extract_event_data
from workers.text_extractor.nodes.critic_node import critique_extraction
from workers.text_extractor.nodes.hitl_node import require_human_in_loop
from workers.text_extractor.nodes.hitl_merge_node import merge_hitl_clarification
from workers.text_extractor.nodes.hitl_reretrieval_node import hitl_update_confirmation
from workers.text_extractor.nodes.qa_store_node import store_qa_pair


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def route_intent(state: AgentState) -> str:
    """Route after intent classification."""
    intent = state.get("intent")
    
    if intent in ["CHITCHAT", "QUERY"]:
        return "end"
    
    if intent == "QA_PAIR":
        return "qa_store_node"
    
    # NEW, UPDATE, ANNOUNCEMENT, FORM_DEADLINE, VENUE_CHANGE, SCHEDULE_CHANGE, RESOURCE_CALLOUT
    # ALL go through full extraction pipeline
    return "context_node"


def route_critic(state: AgentState) -> str:
    """Route after critic validation."""
    if not state.get("needs_human"):
        return "end"
    
    if state.get("hitl_reason") == "max_rounds_exceeded":
        return "end"
    
    return "hitl_node"


def route_reretrieval(state: AgentState) -> str:
    """Route after reretrieval re-runs critic."""
    if not state.get("needs_human"):
        return "end"
    
    if state.get("hitl_reason") == "max_rounds_exceeded":
        return "end"
    
    return "hitl_node"


# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

workflow = StateGraph(AgentState)

# Register all nodes
workflow.add_node("intent_node", classify_intent)
workflow.add_node("context_node", fetch_context_agentic)
workflow.add_node("extractor_node", extract_event_data)
workflow.add_node("critic_node", critique_extraction)
workflow.add_node("hitl_node", require_human_in_loop)
workflow.add_node("hitl_merge_node", merge_hitl_clarification)
workflow.add_node("hitl_reretrieval_node", hitl_update_confirmation)
workflow.add_node("qa_store_node", store_qa_pair)

# Entry point
workflow.set_entry_point("intent_node")

# intent_node routing
workflow.add_conditional_edges(
    "intent_node",
    route_intent,
    {
        "context_node": "context_node",
        "qa_store_node": "qa_store_node",
        "end": END
    }
)

# Linear pipeline: context → extractor → critic
workflow.add_edge("context_node", "extractor_node")
workflow.add_edge("extractor_node", "critic_node")

# critic routing — all HITL reasons go to hitl_node
workflow.add_conditional_edges(
    "critic_node",
    route_critic,
    {
        "hitl_node": "hitl_node",
        "end": END
    }
)

# hitl_node always ends (resolution happens in main.py on next user message)
workflow.add_edge("hitl_node", END)

# qa_store always ends
workflow.add_edge("qa_store_node", END)

# hitl_reretrieval loops back through critic
workflow.add_conditional_edges(
    "hitl_reretrieval_node",
    route_reretrieval,
    {
        "hitl_node": "hitl_node",
        "end": END
    }
)

# hitl_merge always ends (result handled in main.py)
workflow.add_edge("hitl_merge_node", END)

# Compile
app = workflow.compile()
