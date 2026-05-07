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
    opencode_api_key: str = ""
    opencode_base_url: str = "https://opencode.ai/zen/go/v1"
    opencode_model: str = "qwen3.6-plus"
    discovery_depth: int = 1
    js_rendering_enabled: bool = True
    tavily_api_key: str = ""
    search_relevance_threshold: float = 0.5
    search_queries_per_company: int = 8
    assessment_threshold: float = 0.4
    crawl_concurrency: int = 4
    discovery_concurrency: int = 3
    analysis_concurrency: int = 3


settings = Settings()
