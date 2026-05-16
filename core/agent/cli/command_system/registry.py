"""Command registry for PixelBeat agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .types import Command, CommandBase


@dataclass
class CommandRegistry:
    _commands: dict[str, Command] = field(default_factory=dict)
    _aliases: dict[str, str] = field(default_factory=dict)

    def register(self, command: Command) -> None:
        name = command.name.lower()
        self._commands[name] = command

        for alias in command.aliases:
            alias_lower = alias.lower()
            if alias_lower not in self._commands and alias_lower not in self._aliases:
                self._aliases[alias_lower] = name

    def unregister(self, name: str) -> None:
        name_lower = name.lower()
        if name_lower in self._commands:
            del self._commands[name_lower]

        aliases_to_remove = [
            alias for alias, target in self._aliases.items()
            if target == name_lower
        ]
        for alias in aliases_to_remove:
            del self._aliases[alias]

    def get(self, name: str) -> Optional[Command]:
        name_lower = name.lower()

        if name_lower in self._commands:
            return self._commands[name_lower]

        if name_lower in self._aliases:
            return self._commands.get(self._aliases[name_lower])

        return None

    def has(self, name: str) -> bool:
        return self.get(name) is not None

    def list_commands(
        self,
        include_hidden: bool = False,
        include_disabled: bool = False,
    ) -> list[Command]:
        commands = list(self._commands.values())

        if not include_hidden:
            commands = [cmd for cmd in commands if not cmd.is_hidden]

        if not include_disabled:
            commands = [cmd for cmd in commands if cmd.is_enabled()]

        return sorted(commands, key=lambda c: c.name.lower())

    def find_commands(self, query: str, limit: int = 20) -> list[Command]:
        query_lower = query.lower()
        matches: list[tuple[int, str, Command]] = []

        for command in self._commands.values():
            score = 0

            if query_lower == command.name.lower():
                score = 1000
            elif command.name.lower().startswith(query_lower):
                score = 100
            elif query_lower in command.name.lower():
                score = 50
            elif query_lower in command.description.lower():
                score = 25
            elif any(query_lower in alias.lower() for alias in command.aliases):
                score = 30

            if score > 0:
                matches.append((-score, command.name, command))

        matches.sort()
        return [cmd for _, _, cmd in matches[:limit]]

    def clear(self) -> None:
        self._commands.clear()
        self._aliases.clear()


_REGISTRY = CommandRegistry()


def get_command_registry() -> CommandRegistry:
    return _REGISTRY


def register_command(command: Command) -> None:
    _REGISTRY.register(command)


def get_command(name: str) -> Optional[Command]:
    return _REGISTRY.get(name)


def has_command(name: str) -> bool:
    return _REGISTRY.has(name)


def list_commands(
    include_hidden: bool = False,
    include_disabled: bool = False,
) -> list[Command]:
    return _REGISTRY.list_commands(include_hidden, include_disabled)


def find_commands(query: str, limit: int = 20) -> list[Command]:
    return _REGISTRY.find_commands(query, limit)
