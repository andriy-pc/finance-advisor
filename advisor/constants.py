from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers for the application."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
