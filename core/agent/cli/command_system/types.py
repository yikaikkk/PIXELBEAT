"""Command type system for PixelBeat agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


class CommandType(Enum):
    PROMPT = "prompt"
    LOCAL = "local"


@dataclass(frozen=True)
class CompactionResult:
    pre_compact_count: int = 0
    post_compact_count: int = 0
    tokens_saved: int = 0
    trigger: str = "manual"
    summary_preview: Optional[str] = None


@dataclass(frozen=True)
class LocalCommandResult:
    type: str = "text"
    value: str = ""
    compaction_result: Optional[CompactionResult] = None
    display_text: Optional[str] = None


@dataclass
class CommandContext:
    workspace_root: Path
    cwd: Path
    conversation: Any
    cost_tracker: Any
    history: Any
    config: dict[str, Any] = field(default_factory=dict)


LocalCommandCall = Callable[[str, CommandContext], LocalCommandResult]


@dataclass(frozen=True)
class CommandBase:
    name: str
    description: str
    aliases: list[str] = field(default_factory=list)
    is_enabled: Callable[[], bool] = field(default=lambda: True)
    is_hidden: bool = False
    argument_hint: Optional[str] = None
    when_to_use: Optional[str] = None
    user_invocable: bool = True
    loaded_from: str = "builtin"

    @property
    def command_type(self) -> CommandType:
        raise NotImplementedError("Subclasses must implement command_type property")

    def user_facing_name(self) -> str:
        return self.name


@dataclass(frozen=True)
class PromptCommand(CommandBase):
    progress_message: str = ""
    content_length: int = 0
    arg_names: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    model: Optional[str] = None
    source: str = "builtin"
    markdown_content: str = ""

    @property
    def command_type(self) -> CommandType:
        return CommandType.PROMPT

    async def get_prompt_for_command(
        self,
        args: str,
        context: CommandContext,
    ) -> list[dict[str, Any]]:
        content = self.markdown_content
        return [{"type": "text", "text": content}]


@dataclass(frozen=True)
class LocalCommand(CommandBase):
    supports_non_interactive: bool = False
    _call_impl: Optional[LocalCommandCall] = field(default=None, repr=False, compare=False)

    @property
    def command_type(self) -> CommandType:
        return CommandType.LOCAL

    def set_call(self, call: LocalCommandCall) -> None:
        object.__setattr__(self, '_call_impl', call)

    async def call(self, args: str, context: CommandContext) -> LocalCommandResult:
        if self._call_impl is not None:
            return self._call_impl(args, context)
        return LocalCommandResult(type="text", value=f"Command {self.name} not implemented")


Command = PromptCommand | LocalCommand


def get_command_name(cmd: CommandBase) -> str:
    return cmd.user_facing_name()


def is_command_enabled(cmd: CommandBase) -> bool:
    return cmd.is_enabled()
