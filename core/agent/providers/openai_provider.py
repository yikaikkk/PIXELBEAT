"""OpenAI provider implementation."""

from __future__ import annotations

from typing import Any, Optional

try:
    from openai import OpenAI
except ModuleNotFoundError:
    OpenAI = None

from .openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI provider using OpenAI SDK."""

    def __init__(
        self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None
    ):
        super().__init__(
            api_key,
            base_url or "https://api.openai.com/v1",
            model or "gpt-4o",
        )

    def _create_client(self) -> Any:
        if OpenAI is None:
            raise ModuleNotFoundError(
                "openai package is not installed. Install optional dependencies to use OpenAIProvider."
            )
        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_available_models(self) -> list[str]:
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ]
