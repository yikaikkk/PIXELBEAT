"""Agent module for PixelBeat - LLM-powered agent with tool calling."""

__version__ = "0.1.0"

from .conversation import Conversation, Message, TextContentBlock, ToolUseContentBlock, ToolResultContentBlock
from .providers import (
    BaseProvider,
    OpenAICompatibleProvider,
    OpenAIProvider,
    AnthropicProvider,
    DeepSeekProvider,
    GLMProvider,
    QwenProvider,
    ChatResponse,
    ChatMessage,
    MessageInput,
    TextChunkCallback,
)
from .tool_registry import ToolRegistry, ToolSpec, Tool, ToolCall, ToolResult
from .tool_context import ToolContext
from .agent_loop import run_agent_loop, AgentLoopResult

__all__ = [
    "Conversation",
    "Message",
    "TextContentBlock",
    "ToolUseContentBlock",
    "ToolResultContentBlock",
    "BaseProvider",
    "OpenAICompatibleProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "DeepSeekProvider",
    "GLMProvider",
    "QwenProvider",
    "ChatResponse",
    "ChatMessage",
    "MessageInput",
    "TextChunkCallback",
    "ToolRegistry",
    "ToolSpec",
    "Tool",
    "ToolCall",
    "ToolResult",
    "ToolContext",
    "run_agent_loop",
    "AgentLoopResult",
]
