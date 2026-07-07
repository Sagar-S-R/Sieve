"""
QA Store Node - Handles qa_pair message type.

When a message is a Q&A exchange (someone asks, someone answers),
we store it as a searchable knowledge base entry for future reference.
"""

from workers.text_extractor.graph.state import AgentState
from workers.text_extractor.core.logger import logger


async def store_qa_pair(state: AgentState) -> AgentState:
    """
    Store Q&A pair in database for future retrieval.
    
    Currently just logs - can be expanded to store in a separate QA table.
    """
    extracted_data = state.get("extracted_data")
    group_id = state.get("group_id")
    user_id = state.get("user_id")
    
    logger.info("QA Store Node started", extra={
        "node": "qa_store",
        "group_id": group_id,
        "user_id": user_id
    })
    
    if not extracted_data or extracted_data.message_type != "qa_pair":
        logger.warning("QA store node called but message_type is not qa_pair", extra={
            "node": "qa_store"
        })
        return state
    
    question = extracted_data.question_text
    answer = extracted_data.answer_text
    
    if question and answer:
        logger.info(f"Storing Q&A: Q='{question}' A='{answer}'", extra={
            "node": "qa_store",
            "group_id": group_id
        })
        
        # TODO: Store in dedicated QA table for semantic search
        # For now, just log - can be added later with vector embeddings
        # await store_qa_in_vector_db(group_id, question, answer)
    else:
        logger.warning("Q&A extraction incomplete", extra={
            "node": "qa_store",
            "has_question": bool(question),
            "has_answer": bool(answer)
        })
    
    logger.info("QA Store Node completed", extra={"node": "qa_store"})
    return state
