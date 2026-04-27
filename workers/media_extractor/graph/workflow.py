from langgraph.graph import StateGraph, END
from workers.media_extractor.graph.state import AgentState
from workers.media_extractor.nodes.classifier_node import classify_media
from workers.media_extractor.nodes.vision_node import extract_from_image
from workers.media_extractor.nodes.ocr_chunk_node import extract_from_pdf
from workers.media_extractor.nodes.critic_node import critique_extraction
from workers.media_extractor.nodes.hitl_node import require_human_in_loop


def route_media_type(state: AgentState):
    """Route based on media type classification."""
    media_type = state.get("media_type")
    if media_type == "image":
        return "vision_node"
    elif media_type == "pdf":
        return "ocr_chunk_node"
    else:
        return "end"


def route_critic(state: AgentState):
    """Route based on validation result."""
    if state.get("needs_human"):
        return "hitl_node"
    return "end"


# Build the workflow graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("classifier_node", classify_media)
workflow.add_node("vision_node", extract_from_image)
workflow.add_node("ocr_chunk_node", extract_from_pdf)
workflow.add_node("critic_node", critique_extraction)
workflow.add_node("hitl_node", require_human_in_loop)

# Set entry point
workflow.set_entry_point("classifier_node")

# Add conditional edges from classifier
workflow.add_conditional_edges(
    "classifier_node",
    route_media_type,
    {
        "vision_node": "vision_node",
        "ocr_chunk_node": "ocr_chunk_node",
        "end": END
    }
)

# Both vision and OCR nodes go to critic
workflow.add_edge("vision_node", "critic_node")
workflow.add_edge("ocr_chunk_node", "critic_node")

# Conditional routing from critic
workflow.add_conditional_edges(
    "critic_node",
    route_critic,
    {
        "hitl_node": "hitl_node",
        "end": END
    }
)

# HITL node goes to END
workflow.add_edge("hitl_node", END)

# Compile the graph
app = workflow.compile()
