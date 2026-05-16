"""Command execution engine for PixelBeat agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .registry import CommandRegistry, get_command_registry
from .types import (
    Command,
    CommandContext,
    CommandType,
    LocalCommand,
    LocalCommandResult,
    PromptCommand,
)


@dataclass
class CommandResult:
    success: bool
    command_name: str
    result_type: str = "text"
    text: str = ""
    prompt_content: list[dict[str, Any]] = field(default_factory=list)
    should_query: bool = False
    display: str = "system"
    meta_messages: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @classmethod
    def success_text(cls, command_name: str, text: str) -> "CommandResult":
        return cls(
            success=True,
            command_name=command_name,
            result_type="text",
            text=text,
            display="system",
        )

    @classmethod
    def success_prompt(
        cls,
        command_name: str,
        prompt_content: list[dict[str, Any]],
        should_query: bool = True,
    ) -> "CommandResult":
        return cls(
            success=True,
            command_name=command_name,
            result_type="prompt",
            prompt_content=prompt_content,
            should_query=should_query,
            display="user",
        )

    @classmethod
    def error(cls, command_name: str, error: str) -> "CommandResult":
        return cls(
            success=False,
            command_name=command_name,
            result_type="text",
            text=f"Error: {error}",
            error=error,
            display="system",
        )

    @classmethod
    def skip(cls, command_name: str) -> "CommandResult":
        return cls(
            success=True,
            command_name=command_name,
            result_type="skip",
            display="skip",
        )


@dataclass
class CommandEngine:
    registry: CommandRegistry
    workspace_root: Path
    context: CommandContext
    _command_hooks: list[Callable[[str, CommandResult], None]] = field(
        default_factory=list
    )

    async def execute(
        self,
        command_input: str,
    ) -> CommandResult:
        if not command_input.startswith("/"):
            return CommandResult.error(
                "",
                "Commands must start with '/'",
            )

        parts = command_input[1:].split(maxsplit=1)
        command_name = parts[0].strip()
        args = parts[1].strip() if len(parts) > 1 else ""

        command = self.registry.get(command_name)
        if command is None:
            return CommandResult.error(
                command_name,
                f"Unknown command: {command_name}",
            )

        if not command.is_enabled():
            return CommandResult.error(
                command_name,
                f"Command {command_name} is disabled",
            )

        result: CommandResult
        if command.command_type == CommandType.LOCAL:
            result = await self._execute_local(command, args)
        elif command.command_type == CommandType.PROMPT:
            result = await self._execute_prompt(command, args)
        else:
            result = CommandResult.error(
                command_name,
                f"Unknown command type: {command.command_type}",
            )

        for hook in self._command_hooks:
            try:
                hook(command_name, result)
            except Exception:
                pass

        return result

    async def _execute_local(
        self,
        command: LocalCommand,
        args: str,
    ) -> CommandResult:
        try:
            local_result = await command.call(args, self.context)

            if local_result.type == "skip":
                return CommandResult.skip(command.name)

            display_text = local_result.display_text or local_result.value
            return CommandResult.success_text(
                command.name,
                display_text,
            )
        except Exception as e:
            return CommandResult.error(
                command.name,
                str(e),
            )

    async def _execute_prompt(
        self,
        command: PromptCommand,
        args: str,
    ) -> CommandResult:
        try:
            prompt_content = await command.get_prompt_for_command(args, self.context)
            return CommandResult.success_prompt(
                command.name,
                prompt_content,
                should_query=True,
            )
        except Exception as e:
            return CommandResult.error(
                command.name,
                str(e),
            )

    def add_command_hook(
        self,
        hook: Callable[[str, CommandResult], None],
    ) -> None:
        self._command_hooks.append(hook)

    def remove_command_hook(
        self,
        hook: Callable[[str, CommandResult], None],
    ) -> None:
        if hook in self._command_hooks:
            self._command_hooks.remove(hook)


def create_command_context(
    workspace_root: str | Path,
    conversation: Any = None,
    cost_tracker: Any = None,
    history: Any = None,
    cwd: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> CommandContext:
    root = Path(workspace_root).expanduser().resolve()
    current = Path(cwd).expanduser().resolve() if cwd is not None else root

    return CommandContext(
        workspace_root=root,
        cwd=current,
        conversation=conversation,
        cost_tracker=cost_tracker,
        history=history,
        config=config or {},
    )


async def execute_command_async(
    cmd_name: str,
    args: str,
    context: CommandContext,
) -> CommandResult:
    from .engine import CommandEngine

    registry = get_command_registry()
    cmd = registry.get(cmd_name)

    if cmd is None:
        return CommandResult.error(cmd_name, f"Unknown command: {cmd_name}")

    if not cmd.is_enabled():
        return CommandResult.error(cmd_name, f"Command {cmd_name} is disabled")

    engine = CommandEngine(
        registry=registry,
        workspace_root=context.workspace_root,
        context=context,
    )

    command_input = f"/{cmd_name}"
    if args:
        command_input += f" {args}"

    return await engine.execute(command_input)


def execute_command_sync(cmd_name: str, args: str, context: CommandContext) -> tuple[bool, str | None, str | None]:
    from .builtins import get_builtin_commands

    cmd = None
    for builtin_cmd in get_builtin_commands():
        if builtin_cmd.name.lower() == cmd_name.lower() or cmd_name.lower() in [a.lower() for a in builtin_cmd.aliases]:
            cmd = builtin_cmd
            break

    if cmd is None:
        return False, None, f"Unknown command: {cmd_name}"

    try:
        if cmd.command_type == CommandType.LOCAL and cmd._call_impl is not None:
            result = cmd._call_impl(args, context)
            return True, result.value, None
        else:
            return False, None, f"Command not implemented for sync execution: {cmd_name}"
    except Exception as e:
        return False, None, str(e)
