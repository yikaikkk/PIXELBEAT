"""Configuration management for PixelBeat agent using .env files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv


def get_env_path() -> Path:
    """Get the path to the .env file."""
    return Path.cwd() / ".env"


def load_env_config() -> dict[str, Any]:
    """Load configuration from .env file.
    
    Returns:
        Configuration dictionary
    """
    env_path = get_env_path()
    
    if env_path.exists():
        load_dotenv(env_path)
    
    config: dict[str, Any] = {
        "default_provider": os.getenv("DEFAULT_PROVIDER", "openai"),
        "providers": {},
        "session": {
            "auto_save": os.getenv("SESSION_AUTO_SAVE", "true").lower() == "true",
            "max_history": int(os.getenv("SESSION_MAX_HISTORY", "100"))
        }
    }
    
    # Parse provider configurations
    # Expected format: PROVIDER_NAME_API_KEY, PROVIDER_NAME_BASE_URL, etc.
    providers = ["openai", "anthropic", "deepseek", "glm", "qwen"]
    
    for provider in providers:
        api_key = os.getenv(f"{provider.upper()}_API_KEY")
        base_url = os.getenv(f"{provider.upper()}_BASE_URL")
        default_model = os.getenv(f"{provider.upper()}_DEFAULT_MODEL")
        
        if api_key:
            provider_config: dict[str, str] = {"api_key": api_key}
            if base_url:
                provider_config["base_url"] = base_url
            if default_model:
                provider_config["default_model"] = default_model
            
            config["providers"][provider] = provider_config
    
    return config


def get_provider_config(provider: str) -> dict[str, Any]:
    """Get configuration for a specific provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Provider configuration dictionary
    """
    config = load_env_config()
    providers = config.get("providers", {})
    
    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}")
    
    return providers[provider]


def get_default_provider() -> str:
    """Get the default provider.
    
    Returns:
        Default provider name
    """
    config = load_env_config()
    return config.get("default_provider", "openai")
