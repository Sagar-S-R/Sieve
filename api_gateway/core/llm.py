"""LLM service for API Gateway."""
import httpx
from api_gateway.core.config import settings


async def call_llm(prompt: str, model: str = "llama-3.1-70b-versatile") -> str:
    """
    Call Groq LLM API.
    
    Args:
        prompt: The prompt to send
        model: Model name (default: llama-3.1-70b-versatile)
        
    Returns:
        LLM response text
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 500
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
