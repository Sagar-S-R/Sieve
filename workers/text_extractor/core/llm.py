from langchain_google_genai import ChatGoogleGenerativeAI
from workers.text_extractor.core.config import settings

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=settings.GOOGLE_API_KEY
)
