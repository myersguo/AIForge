from langchain_openai import ChatOpenAI

from app.config.settings import settings


def get_llm():
    """
    Configure and return an OpenAI compatible LLM.
    """
    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None,
        model_name=settings.OPENAI_MODEL_NAME,
        temperature=0.7,
    )
