import asyncio
import time
from typing import Any, Type

import tiktoken

from advisor.llm.lite_llm_client import LiteLLMClient
from advisor.llm.llm_output_parser import T
from advisor.llm.metrics_collector import MetricsCollector
from advisor.llm.prompt_manager import PromptManager


# TODO: ! add method to use direct prompt (instead of using prompt manager)
class LLMService:
    """
    Orchestration layer for LLM operations.

    Coordinates: prompt management, LLM execution, output parsing, metrics.
    Single entry point for all LLM interactions.
    """

    def __init__(self, client: LiteLLMClient, prompt_manager: PromptManager, metrics: MetricsCollector | None = None):
        """
        Initialize service with dependencies.

        Args:
            client: LiteLLM client instance
            prompt_manager: Prompt template manager
            metrics: Optional metrics collector
        """
        self._client = client
        self._prompt_manager = prompt_manager
        self._metrics = metrics or MetricsCollector()

    async def invoke_structured(
        self,
        prompt_key: str,
        variables: dict[str, Any],
        response_model: Type[T],
        system_prompt_key: str | None = None,
    ) -> T:
        """
        Primary method for type-safe LLM interactions.

        Full pipeline: validate → render → invoke → parse → metrics.

        Args:
            prompt_key: Registered prompt identifier
            variables: Template variables
            response_model: Pydantic model for output
            system_prompt_key: Optional system prompt key

        Returns:
            Validated Pydantic instance

        Example:
            ```python
            result = await service.invoke_structured(
                prompt_key="categorize_transaction",
                variables={"description": "Coffee", "amount": 5.50},
                response_model=TransactionCategory
            )
            ```
        """
        start_time = time.perf_counter()

        try:
            # Render prompt
            # TODO: ! validation and rendering do the same job
            self._prompt_manager.validate_variables(prompt_key, variables)
            prompt_text = self._prompt_manager.render(prompt_key, variables)

            # Build messages
            messages = []
            if system_prompt_key:
                system_prompt = self._prompt_manager.render(system_prompt_key, {})
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt_text})

            # Invoke with structured output via instructor
            result = await self._client.complete_structured(messages=messages, response_model=response_model)

            # Record success metrics
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_call(
                provider=self._client.config.provider,
                model=self._client.config.model_name,
                latency_ms=latency_ms,
                input_tokens=self._estimate_tokens(prompt_text),
                output_tokens=self._estimate_tokens(str(result)),
                success=True,
            )

            return result

        except Exception as e:
            # Record failure
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_call(
                provider=self._client.config.provider,
                model=self._client.config.model_name,
                latency_ms=latency_ms,
                input_tokens=0,
                output_tokens=0,
                success=False,
                error_type=type(e).__name__,
            )

            raise

    async def invoke_raw(
        self, prompt_key: str, variables: dict[str, Any] = {}, system_message: str | None = None
    ) -> str:
        """
        Invoke LLM and return raw string response.

        Args:
            prompt_key: Prompt identifier
            variables: Template variables
            system_message: Optional system prompt

        Returns:
            Raw string response
        """
        start_time = time.perf_counter()

        try:
            self._prompt_manager.validate_variables(prompt_key, variables)
            prompt_text = self._prompt_manager.render(prompt_key, variables)

            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt_text})

            result = await self._client.complete(messages=messages)

            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_call(
                provider=self._client.config.provider,
                model=self._client.config.model_name,
                latency_ms=latency_ms,
                input_tokens=self._estimate_tokens(prompt_text),
                output_tokens=self._estimate_tokens(result),
                success=True,
            )

            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_call(
                provider=self._client.config.provider,
                model=self._client.config.model_name,
                latency_ms=latency_ms,
                input_tokens=0,
                output_tokens=0,
                success=False,
                error_type=type(e).__name__,
            )
            raise

    async def batch_invoke_structured(
        self, requests: list[dict[str, Any]], response_model: Type[T], max_concurrent: int = 5
    ) -> list[T]:
        """
        Process multiple requests concurrently with rate limiting.

        Uses semaphore for concurrency control to respect API limits.

        Args:
            requests: List of dicts with prompt_key, variables, system_message
            response_model: Expected response type
            max_concurrent: Max parallel requests

        Returns:
            List of results in same order as requests
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _process_one(req: dict[str, Any]) -> T:
            async with semaphore:
                return await self.invoke_structured(
                    prompt_key=req["prompt_key"],
                    variables=req["variables"],
                    response_model=response_model,
                    system_prompt_key=req.get("system_prompt_key"),
                )

        tasks = [_process_one(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=False)

    # TODO: ! update this method to use proper `Strategy` pattern
    def _estimate_tokens(self, text: str, response_object: Any | None = None) -> int:
        """
        Estimate or extract token count from response.

        Priority:
        1. Extract from LiteLLM response object if available
        2. Use tiktoken for accurate counting (OpenAI-compatible)
        3. Fall back to character-based estimation

        Args:
            text: Text to count tokens for
            response_object: Optional LiteLLM response object with usage data

        Returns:
            Token count
        """
        # Strategy 1: Extract from response object (most accurate)
        if response_object and hasattr(response_object, "usage"):
            usage = response_object.usage
            if hasattr(usage, "total_tokens"):
                return usage.total_tokens
            # For prompt vs completion separation
            if hasattr(usage, "prompt_tokens") and hasattr(usage, "completion_tokens"):
                return usage.prompt_tokens + usage.completion_tokens

        # Strategy 2: Use tiktoken for accurate counting
        try:
            # Determine encoding based on model (from config)
            model = self._client.config.model_name.lower()

            # Map models to encodings
            if any(m in model for m in ["gpt-4", "gpt-3.5-turbo", "gpt-35-turbo"]):
                encoding = tiktoken.encoding_for_model(model)
            elif "claude" in model:
                # Claude uses similar tokenization to GPT-4
                encoding = tiktoken.get_encoding("cl100k_base")
            else:
                # Default to cl100k_base (GPT-4 encoding)
                encoding = tiktoken.get_encoding("cl100k_base")

            return len(encoding.encode(text))

        except (ImportError, Exception):
            pass

        # Strategy 3: Character-based estimation (least accurate fallback)
        # Rule of thumb: 1 token ≈ 4 characters for English text
        return max(1, len(text) // 4)

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get aggregated metrics."""
        return self._metrics.get_summary()
