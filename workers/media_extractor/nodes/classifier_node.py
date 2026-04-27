from pathlib import Path
from workers.media_extractor.graph.state import AgentState


def classify_media(state: AgentState) -> AgentState:
    """
    Classify the media type based on file extension.
    Sets media_type to 'image' or 'pdf'.
    """
    file_path = state.get("file_path", "")
    
    if not file_path:
        state["media_type"] = "unknown"
        return state
    
    extension = Path(file_path).suffix.lower()
    
    if extension in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        state["media_type"] = "image"
    elif extension == ".pdf":
        state["media_type"] = "pdf"
    else:
        state["media_type"] = "unknown"
    
    return state
