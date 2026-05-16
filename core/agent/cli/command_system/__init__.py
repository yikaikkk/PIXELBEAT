"""Command system for PixelBeat agent."""

from .types import (
    Command,
    CommandBase,
    CommandType,
    CommandContext,
    LocalCommand,
    LocalCommandResult,
    PromptCommand,
    CompactionResult,
)

from .registry import (
    CommandRegistry,
    get_command_registry,
    register_command,
    get_command,
    has_command,
    list_commands,
    find_commands,
)

from .engine import (
    CommandResult,
    CommandEngine,
    create_command_context,
    execute_command_async,
    execute_command_sync,
)

from .builtins import (
    get_builtin_commands,
    register_builtin_commands,
    HELP_COMMAND,
    CLEAR_COMMAND,
    EXIT_COMMAND,
    COST_COMMAND,
    RESUME_COMMAND,
    INIT_COMMAND,
)

__all__ = [
    "Command",
    "CommandBase",
    "CommandType",
    "CommandContext",
    "LocalCommand",
    "LocalCommandResult",
    "PromptCommand",
    "CompactionResult",
    "CommandRegistry",
    "get_command_registry",
    "register_command",
    "get_command",
    "has_command",
    "list_commands",
    "find_commands",
    "CommandResult",
    "CommandEngine",
    "create_command_context",
    "execute_command_async",
    "execute_command_sync",
    "get_builtin_commands",
    "register_builtin_commands",
    "HELP_COMMAND",
    "CLEAR_COMMAND",
    "EXIT_COMMAND",
    "COST_COMMAND",
    "RESUME_COMMAND",
    "INIT_COMMAND",
]
