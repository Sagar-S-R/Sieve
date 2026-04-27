from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    RABBITMQ_URL: str
    REDIS_URL: str
    DATABASE_URL: str
    TELEGRAM_BOT_TOKEN: str
    
    LOG_LEVEL: str = "INFO"
    PROMETHEUS_PORT: int = 8001
    RABBITMQ_MAX_RETRIES: int = 3
    RABBITMQ_INITIAL_RETRY_DELAY: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
