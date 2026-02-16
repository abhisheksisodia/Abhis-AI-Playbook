"""LLM client abstractions for scoring and summarization prompts."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from .logger import get_logger

logger = get_logger("utils.llm")


class MissingDependencyError(RuntimeError):
    """Raised when an optional SDK dependency is missing."""


class MissingAPIKeyError(RuntimeError):
    """Raised when an API key is not set in the environment."""


@dataclass
class LLMResponse:
    content: str
    raw: Any


def _load_api_key(env_var: str) -> str:
    api_key = os.getenv(env_var)
    if not api_key:
        raise MissingAPIKeyError(
            f"LLM API key not found. Set {env_var} in your environment."
        )
    return api_key


class LLMClient:
    def __init__(self, provider: str, model: str, api_key_env: str) -> None:
        self.provider = provider.lower()
        self.model = model
        self.api_key = _load_api_key(api_key_env)

        if self.provider == "anthropic":
            try:
                from anthropic import Anthropic
            except ImportError as exc:  # pragma: no cover - optional deps
                raise MissingDependencyError(
                    "anthropic SDK is required for provider=anthropic. "
                    "Install with `pip install anthropic`."
                ) from exc
            self._client = Anthropic(api_key=self.api_key)
        elif self.provider in {"openai", "azure-openai"}:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - optional deps
                raise MissingDependencyError(
                    "openai SDK is required for provider=openai. "
                    "Install with `pip install openai`."
                ) from exc
            kwargs: Dict[str, Any] = {"api_key": self.api_key}
            if self.provider == "azure-openai":
                kwargs["azure_endpoint"] = os.getenv("AZURE_OPENAI_ENDPOINT")
                kwargs["api_version"] = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
            self._client = OpenAI(**kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @retry(wait=wait_exponential(min=2, max=20), stop=stop_after_attempt(3))
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if self.provider == "anthropic":
            response = self._client.messages.create(
                system=system_prompt,
                model=self.model,
                max_output_tokens=max_output_tokens or 1024,
                temperature=temperature,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt,
                    }
                ],
            )
            text = "".join(block.text for block in response.content if hasattr(block, "text"))
            return LLMResponse(content=text, raw=response)

        if self.provider in {"openai", "azure-openai"}:
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                max_tokens=max_output_tokens or 1024,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = response.choices[0].message.content or ""
            return LLMResponse(content=text, raw=response)

        raise ValueError(f"Unsupported provider: {self.provider}")

    def safe_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
    ) -> LLMResponse:
        try:
            return self.complete(
                system_prompt,
                user_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        except (RetryError, MissingAPIKeyError) as exc:
            logger.error("LLM completion failed: %s", exc)
            raise
