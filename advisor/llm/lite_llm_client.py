import os
from typing import Any, Callable, List, Type

import instructor
import litellm
from litellm import acompletion
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from advisor.constants import LLMProvider
from advisor.llm.llm_output_parser import T
from advisor.settings import LLMSettings


class LiteLLMClient:
    """
    Thin wrapper around LiteLLM providing retry logic and structured outputs.

    This is NOT an abstraction layer - LiteLLM already abstracts providers.
    This adds: retry logic, structured output support, and consistent error handling.
    """

    def __init__(self, settings: LLMSettings):
        """
        Initialize client with configuration.

        Args:
            settings: LLM configuration
        """
        self.config = settings
        self._setup_litellm()
        self._instructor_client = instructor.from_litellm(acompletion)

    def _setup_litellm(self) -> None:
        """Configure LiteLLM global settings and API keys."""
        # Set API keys in environment for LiteLLM
        if self.config.api_key:
            if self.config.provider == LLMProvider.OPENAI:
                os.environ["OPENAI_API_KEY"] = self.config.api_key
            elif self.config.provider == LLMProvider.ANTHROPIC:
                os.environ["ANTHROPIC_API_KEY"] = self.config.api_key

        # Configure LiteLLM behavior
        litellm.drop_params = True  # Ignore unsupported params gracefully
        litellm.set_verbose = False  # Disable verbose logging

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
    )
    async def complete(self, messages: List[dict[str, str]], **kwargs) -> str:
        """
        Execute completion and return text response.

        Includes automatic retry with exponential backoff using tenacity.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Override configuration parameters

        Returns:
            String response from LLM
        """
        params = self._build_params(messages, **kwargs)
        response = await acompletion(**params)
        return response.choices[0].message.content

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def complete_structured(self, messages: List[dict[str, str]], response_model: Type[T], **kwargs) -> T:
        """
        Execute completion with structured output using instructor.

        Instructor handles JSON schema generation, validation, and retries.

        Args:
            messages: Conversation messages
            response_model: Pydantic model for structured output
            **kwargs: Override configuration parameters

        Returns:
            Validated Pydantic model instance
        """
        params = self._build_params(messages, **kwargs)
        params["response_model"] = response_model

        return await self._instructor_client.chat.completions.create(**params)

    async def complete_streaming(self, messages: List[dict[str, str]], callback: Callable, **kwargs) -> None:
        """
        Execute streaming completion with token-by-token callback.

        Args:
            messages: Conversation messages
            callback: Async function called with each token
            **kwargs: Override configuration parameters
        """
        params = self._build_params(messages, **kwargs)
        params["stream"] = True

        response = await acompletion(**params)

        async for chunk in response:
            if chunk.choices[0].delta.content:
                await callback(chunk.choices[0].delta.content)

    def _build_params(self, messages: List[dict[str, str]], **kwargs) -> dict[str, Any]:
        """
        Build LiteLLM parameters from config and overrides.

        Args:
            messages: Message list
            **kwargs: Parameter overrides

        Returns:
            Complete parameter dict for LiteLLM
        """
        params = {
            "model": self.config.to_litellm_model(),
            "messages": messages,
            "temperature": self.config.temperature,
            "timeout": self.config.timeout,
            **self.config.additional_kwargs,
            **kwargs,
        }

        if self.config.max_tokens:
            params["max_tokens"] = self.config.max_tokens

        if self.config.base_url:
            params["api_base"] = self.config.base_url

        return params

    def validate_connection(self) -> bool:
        """
        Test provider connectivity with minimal request.

        Returns:
            True if successful

        Raises:
            ConnectionError: If validation fails
        """
        try:
            response = litellm.completion(
                model=self.config.to_litellm_model(),
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                timeout=5,
                api_base=self.config.base_url if self.config.base_url else None,
            )
            return response is not None
        except Exception as e:
            raise ConnectionError(f"Failed to validate connection to {self.config.provider.value}: {str(e)}")

    def get_metadata(self) -> dict[str, Any]:
        """
        Returns client metadata for observability.

        Returns:
            Dict with provider, model, and configuration info
        """
        return {
            "provider": self.config.provider.value,
            "model": self.config.model_name,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "base_url": self.config.base_url,
        }
