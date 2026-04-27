from workers.media_extractor.graph.state import AgentState
from workers.media_extractor.core.vision_llm import llm
from shared.schemas import EventExtraction
from langchain_core.messages import HumanMessage


def extract_from_image(state: AgentState) -> AgentState:
    """
    Extract event data from an image using Gemini Vision.
    """
    file_path = state.get("file_path")
    
    if not file_path:
        state["validation_error"] = "No file path provided"
        return state
    
    # Read image file
    with open(file_path, "rb") as f:
        image_data = f.read()
    
    # Create message with image
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": "Extract any task, deadline, or event information from this image. "
                       "Look for dates, action items, meeting times, or anything that requires follow-up."
            },
            {
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{image_data.hex()}"
            }
        ]
    )
    
    # Get structured output
    structured_llm = llm.with_structured_output(EventExtraction)
    result = structured_llm.invoke([message])
    
    state["extracted_data"] = result
    return state
