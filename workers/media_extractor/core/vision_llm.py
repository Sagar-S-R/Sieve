from langchain_google_genai import ChatGoogleGenerativeAI
from workers.media_extractor.core.config import settings

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    temperature=0,
    google_api_key=settings.GOOGLE_API_KEY
)
