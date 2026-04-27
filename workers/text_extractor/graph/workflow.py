from langgraph.graph import StateGraph, END
from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.nodes.intent_node import classify_intent
from workers.text_extractor.nodes.context_node import fetch_context
from workers.text_extractor.nodes.extractor_node import extract_event_data
from workers.text_extractor.nodes.critic_node import critique_extraction
from workers.text_extractor.nodes.hitl_node import require_human_in_loop

def route_intent(state: AgentState):
    intent = state.get("intent")
    if intent in ["CHITCHAT", "QUERY"]:
        return "end"
    return "context_node"

def route_critic(state: AgentState):
    if state.get("needs_human"):
        return "hitl_node"
    return "end"

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("intent_node", classify_intent)
workflow.add_node("context_node", fetch_context)
workflow.add_node("extractor_node", extract_event_data)
workflow.add_node("critic_node", critique_extraction)
workflow.add_node("hitl_node", require_human_in_loop)

# Set entry point
workflow.set_entry_point("intent_node")

# Add conditional edges
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

# Compile the graph
app = workflow.compile()
