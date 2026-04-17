from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql://wfm:wfm@localhost:5432/wfmintel"
    auth_username: str = "admin"
    auth_password: str = "changeme"
    llm_provider: str = "claude"
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5-20251001"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    discovery_depth: int = 1


settings = Settings()
