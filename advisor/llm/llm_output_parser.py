import json
from typing import Any, Callable, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


# TODO: ! re-consider usage
class OutputParser:
    """
    Robust parser for LLM outputs with fallback strategies.

    Handles common LLM output issues:
    - Markdown code fences (```json)
    - Text preambles before JSON
    - Malformed JSON
    - Schema validation errors
    """

    def parse(self, llm_output: str, expected_type: Type[T]) -> T:
        """
        Parse LLM output into validated Pydantic model.

        Args:
            llm_output: Raw string from LLM
            expected_type: Target Pydantic model

        Returns:
            Validated model instance

        Raises:
            ValueError: If parsing or validation fails
        """
        cleaned = self._clean_json(llm_output)

        try:
            data = json.loads(cleaned)
            return expected_type(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in LLM output: {str(e)}\nOutput: {llm_output[:200]}")
        except ValidationError as e:
            raise ValueError(f"Output doesn't match {expected_type.__name__} schema: {str(e)}")

    def parse_with_fallback(
        self, llm_output: str, expected_type: Type[T], default_factory: Optional[Callable[[], T]] = None
    ) -> T:
        """
        Parse with graceful fallback to default instance.

        Implements resilience for production: try parsing, then extract JSON,
        then return sensible defaults rather than crashing.

        Args:
            llm_output: Raw LLM output
            expected_type: Target type
            default_factory: Optional callable returning default instance

        Returns:
            Parsed instance or default
        """
        # Strategy 1: Standard parsing
        try:
            return self.parse(llm_output, expected_type)
        except ValueError:
            pass

        # Strategy 2: Aggressive JSON extraction
        try:
            extracted = self._extract_json_anywhere(llm_output)
            if extracted:
                data = json.loads(extracted)
                return expected_type(**data)
        except (json.JSONDecodeError, ValidationError):
            pass

        # Strategy 3: Default instance
        if default_factory is not None:
            return default_factory()

        return self._create_minimal_instance(expected_type)

    def _clean_json(self, text: str) -> str:
        """
        Remove common LLM artifacts around JSON.

        Handles:
        - Markdown fences: ```json ... ```
        - Leading/trailing whitespace
        - Text before first { or [
        """
        text = text.strip()

        # Remove markdown code fences
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        # Find actual JSON boundaries
        start = min(text.find("{") if "{" in text else len(text), text.find("[") if "[" in text else len(text))

        end = max(text.rfind("}"), text.rfind("]"))

        if start < len(text) and end >= 0:
            text = text[start : end + 1]

        return text

    def _extract_json_anywhere(self, text: str) -> Optional[str]:
        """
        Extract JSON from mixed text using regex.

        Finds patterns like {...} or [...] embedded in text.
        """
        import re

        # Match nested JSON objects
        pattern = r"\{(?:[^{}]|(?:\{[^{}]*\}))*\}"
        matches = re.findall(pattern, text, re.DOTALL)

        return matches[0] if matches else None

    def _create_minimal_instance(self, expected_type: Type[T]) -> T:
        """
        Create instance with minimal valid data as last resort.

        Uses field defaults or sensible type-based defaults.
        """
        default_values: dict[str, Any] = {}

        for field_name, field_info in expected_type.model_fields.items():
            # Use field default if available
            if field_info.default is not None:
                continue

            # Skip optional fields
            if not field_info.is_required():
                continue

            # Provide type-based defaults
            annotation = field_info.annotation
            if annotation is str:
                default_values[field_name] = "unknown"
            elif annotation is float:
                default_values[field_name] = 0.0
            elif annotation is int:
                default_values[field_name] = 0
            elif annotation is bool:
                default_values[field_name] = False
            elif annotation is list:
                default_values[field_name] = []

        return expected_type(**default_values)
