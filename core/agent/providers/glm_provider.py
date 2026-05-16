"""GLM (Zhipu AI) provider implementation."""

from __future__ import annotations

from typing import Any, Optional

try:
    from zhipuai import ZhipuAI
except ModuleNotFoundError:
    ZhipuAI = None

from .openai_compatible import OpenAICompatibleProvider


class GLMProvider(OpenAICompatibleProvider):
    """GLM (Zhipu AI) provider using Zhipu SDK.

    GLM models on z.ai require the 'zai/' prefix in model names.
    """

    def __init__(
        self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None
    ):
        super().__init__(api_key, base_url, model or "zai/glm-5.1")

    def _create_client(self) -> Any:
        if ZhipuAI is None:
            raise ModuleNotFoundError(
                "zhipuai package is not installed. Install optional dependencies to use GLMProvider."
            )
        return ZhipuAI(api_key=self.api_key)

    def get_available_models(self) -> list[str]:
        return [
            "zai/glm-5.1",
            "zai/glm-5",
            "zai/glm-5-turbo",
            "zai/glm-4",
            "zai/glm-4-plus",
            "zai/glm-4-air",
            "zai/glm-4-flash",
            "zai/glm-4.5",
            "zai/glm-4.6",
            "zai/glm-4.7",
            "zai/glm-3-turbo",
        ]
