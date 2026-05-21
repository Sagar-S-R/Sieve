from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    RABBITMQ_URL: str
    REDIS_URL: str
    DATABASE_URL: str
    GROQ_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()
