from pydantic_settings import BaseSettings

from advisor.constants import LLMProvider


class DBEngineSettings(BaseSettings):
    pool_size: int = 3
    max_overflow: int = 10
    pool_recycle: int = 270


class LLMSettings(BaseSettings):
    provider: LLMProvider | None = None
    model_name: str
    temperature: float | None = None
    api_key: str | None = None
    base_url: str | None = None

    def to_litellm_model_name(self) -> str:
        """
        Converts provider and model to LiteLLM's expected format.

        LiteLLM uses format: "provider/model" (e.g., "ollama/llama2", "gpt-4")
        """
        if self.provider == LLMProvider.OLLAMA:
            return f"ollama/{self.model_name}"
        elif self.provider == LLMProvider.OPENAI:
            return self.model_name  # OpenAI models don't need prefix
        elif self.provider == LLMProvider.ANTHROPIC:
            return self.model_name  # Anthropic models don't need prefix
        return self.model_name

    class Config:
        env_file = ".env"


class ProjectSettings(BaseSettings):
    sql_connection_url: str | None = None

    llm_integration_settings: LLMSettings

    class Config:
        env_file = ".env"
