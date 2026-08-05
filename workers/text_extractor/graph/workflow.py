from langgraph.graph import StateGraph, END
from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.nodes.intent_node import classify_intent
from workers.text_extractor.nodes.context_node import fetch_context_agentic
from workers.text_extractor.nodes.extractor_node import extract_event_data
from workers.text_extractor.nodes.critic_node import critique_extraction
from workers.text_extractor.nodes.hitl_node import require_human_in_loop
from workers.text_extractor.nodes.hitl_merge_node import merge_hitl_clarification
from workers.text_extractor.nodes.hitl_reretrieval_node import hitl_update_confirmation

def route_intent(state: AgentState) -> str:
    intent = state.get("intent")
    if intent == "CHITCHAT":
        return "end"
    return "context_node"

def route_critic(state: AgentState) -> str:
    if not state.get("needs_human"):
        return "end"
    if state.get("hitl_reason") == "max_rounds_exceeded":
        return "end"
    return "hitl_node"

def route_reretrieval(state: AgentState) -> str:
    if not state.get("needs_human"):
        return "end"
    return "hitl_node"

workflow = StateGraph(AgentState)

workflow.add_node("intent_node", classify_intent)
workflow.add_node("context_node", fetch_context_agentic)
workflow.add_node("extractor_node", extract_event_data)
workflow.add_node("critic_node", critique_extraction)
workflow.add_node("hitl_node", require_human_in_loop)
workflow.add_node("hitl_merge_node", merge_hitl_clarification)
workflow.add_node("hitl_reretrieval_node", hitl_update_confirmation)

workflow.set_entry_point("intent_node")

workflow.add_conditional_edges(
    "intent_node",
    route_intent,
    {
        "context_node": "context_node",
        "end": END
    }
)

workflow.add_edge("context_node", "extractor_node")
workflow.add_edge("extractor_node", "critic_node")

workflow.add_conditional_edges(
    "critic_node",
    route_critic,
    {
        "hitl_node": "hitl_node",
        "end": END
    }
)

workflow.add_edge("hitl_node", END)
workflow.add_edge("hitl_merge_node", END)

workflow.add_conditional_edges(
    "hitl_reretrieval_node",
    route_reretrieval,
    {
        "hitl_node": "hitl_node",
        "end": END
    }
)

app = workflow.compile()
