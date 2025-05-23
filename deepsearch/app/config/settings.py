from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API settings
    API_PREFIX: str = "/api"
    DEBUG: bool = True
    PROJECT_NAME: str = "DeepSearch"

    # LLM settings
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = None
    OPENAI_MODEL_NAME: str = "gpt-3.5-turbo"

    # Search engine settings
    TAVILY_API_KEY: str

    # Streaming settings
    STREAMING: bool = True  # Enable streaming by default

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
