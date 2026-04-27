from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.llm import llm
from workers.text_extractor.core.logger import logger
from workers.text_extractor.core.metrics import messages_processed
from pydantic import BaseModel, Field

class IntentClassification(BaseModel):
    intent: str = Field(description="One of: 'NEW', 'UPDATE', 'QUERY', 'CHITCHAT'")

def classify_intent(state: AgentState) -> AgentState:
    logger.info("Intent Node started", extra={
        "node": "intent_node",
        "message_text": state.get("message_text", "")[:100]  # Log first 100 chars
    })
    
    message_text = state.get("message_text", "")
    
    prompt = f"Classify the intent of the following message as NEW, UPDATE, QUERY, or CHITCHAT:\n\nMessage: {message_text}"
    
    structured_llm = llm.with_structured_output(IntentClassification)
    result = structured_llm.invoke(prompt)
    
    state["intent"] = result.intent
    
    # Track metrics
    messages_processed.labels(intent=result.intent).inc()
    
    logger.info("Intent Node completed", extra={
        "node": "intent_node",
        "intent": result.intent
    })
    
    return state
