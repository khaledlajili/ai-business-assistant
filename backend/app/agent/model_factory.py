from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from app.core.config import settings


ENDPOINTS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "ollama": ("http://localhost:11434/v1", None),
}


def build_model(provider: str, model_id: str) -> OpenAIChatModel:
    base_url, key_env = ENDPOINTS[provider]

    if key_env is None:
        api_key = "ollama"
    elif key_env == "GROQ_API_KEY":
        api_key = settings.GROQ_API_KEY
    elif key_env == "OPENROUTER_API_KEY":
        api_key = settings.OPENROUTER_API_KEY
    else:
        api_key = ""

    if key_env and not api_key:
        raise RuntimeError(f"Missing API key for {provider} (check .env)")

    return OpenAIChatModel(
        model_id,
        provider=OpenAIProvider(base_url=base_url, api_key=api_key),
    )


def get_primary_model() -> OpenAIChatModel:
    return build_model(settings.LLM_PROVIDER, settings.LLM_MODEL)


def get_fallback_model() -> OpenAIChatModel | None:
    if not settings.LLM_FALLBACK_MODEL:
        return None
    try:
        return build_model(settings.LLM_FALLBACK_PROVIDER, settings.LLM_FALLBACK_MODEL)
    except Exception:
        return None
