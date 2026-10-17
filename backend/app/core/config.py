from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://assistant:assistant@localhost:5433/assistant"
    JWT_SECRET: str = "change-me-to-a-random-32-byte-string"
    CORS_ORIGINS: str = "http://localhost:4200"
    ADMIN_TOKEN: str = "change-me"
    DEMO_MODE: bool = True

    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = ""
    LLM_FALLBACK_PROVIDER: str = "openrouter"
    LLM_FALLBACK_MODEL: str = ""
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_REQUESTS_PER_TURN: int = 6

settings = Settings()
