from workers.media_extractor.graph.state import AgentState
from workers.media_extractor.core.vision_llm import llm
from shared.schemas import EventExtraction
import fitz  # PyMuPDF


def extract_from_pdf(state: AgentState) -> AgentState:
    """
    Extract text from PDF, then use LLM to extract event data.
    """
    file_path = state.get("file_path")
    
    if not file_path:
        state["validation_error"] = "No file path provided"
        return state
    
    # Extract text from PDF
    try:
        doc = fitz.open(file_path)
        text_parts = []
        
        for page in doc:
            text_parts.append(page.get_text())
        
        raw_text = "\n".join(text_parts)
        state["raw_text"] = raw_text
        doc.close()
        
    except Exception as e:
        state["validation_error"] = f"PDF extraction failed: {e}"
        return state
    
    # If no text extracted, return early
    if not raw_text.strip():
        state["validation_error"] = "No text found in PDF"
        return state
    
    # Use LLM to extract structured data from text
    prompt = f"""
    Extract any task, deadline, or event information from the following text.
    Look for dates, action items, meeting times, or anything that requires follow-up.
    
    Text:
    {raw_text[:4000]}  # Limit to first 4000 chars to avoid token limits
    """
    
    structured_llm = llm.with_structured_output(EventExtraction)
    result = structured_llm.invoke(prompt)
    
    state["extracted_data"] = result
    return state
