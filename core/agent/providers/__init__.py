"""Agent provider implementations."""

from typing import Any, Type
from .base import BaseProvider, ChatResponse, ChatMessage, MessageInput, TextChunkCallback
from .openai_compatible import OpenAICompatibleProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .deepseek_provider import DeepSeekProvider
from .glm_provider import GLMProvider
from .qwen_provider import QwenProvider

PROVIDER_INFO: dict[str, dict[str, Any]] = {
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4o",
        "default_base_url": "https://api.openai.com/v1",
        "available_models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "anthropic": {
        "label": "Anthropic",
        "default_model": "claude-sonnet-4-6",
        "default_base_url": "https://api.anthropic.com",
        "available_models": ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-6"],
    },
    "deepseek": {
        "label": "DeepSeek",
        "default_model": "deepseek-v4-pro",
        "default_base_url": "https://api.deepseek.com",
        "available_models": ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-coder"],
    },
    "glm": {
        "label": "Zhipu GLM",
        "default_model": "zai/glm-5.1",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "available_models": ["zai/glm-5.1", "glm-4-plus", "glm-4"],
    },
    "qwen": {
        "label": "Qwen",
        "default_model": "qwen3.6-plus",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "available_models": ["qwen3.6-plus", "qwen3.6-turbo", "qwen-max"],
    },
}

PROVIDER_CLASSES: dict[str, Type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "deepseek": DeepSeekProvider,
    "glm": GLMProvider,
    "qwen": QwenProvider,
}


def get_provider_class(provider_name: str) -> Type[BaseProvider]:
    """Get the provider class by name.
    
    Args:
        provider_name: Provider name (openai, anthropic, deepseek, glm, qwen)
        
    Returns:
        Provider class
        
    Raises:
        ValueError: If provider name is not recognized
    """
    if provider_name not in PROVIDER_CLASSES:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(PROVIDER_CLASSES.keys())}")
    return PROVIDER_CLASSES[provider_name]


__all__ = [
    "BaseProvider",
    "ChatResponse",
    "ChatMessage",
    "MessageInput",
    "TextChunkCallback",
    "OpenAICompatibleProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "DeepSeekProvider",
    "GLMProvider",
    "QwenProvider",
    "PROVIDER_INFO",
    "PROVIDER_CLASSES",
    "get_provider_class",
]
