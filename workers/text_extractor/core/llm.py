from langchain_groq import ChatGroq
from workers.text_extractor.core.config import settings

llm = ChatGroq(
    model="llama-3.3-70b-versatile",  # Fast and accurate
    temperature=0,
    groq_api_key=settings.GROQ_API_KEY
)
