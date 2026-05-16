"""Built-in commands for PixelBeat agent."""

from __future__ import annotations

import json
from pathlib import Path

from .engine import CommandContext, CommandResult, LocalCommandResult
from .registry import CommandRegistry, get_command_registry
from .types import Command, CommandType, LocalCommand, PromptCommand


INIT_PROMPT = """Set up a CLAUDE.md file for this repo. CLAUDE.md is loaded into every Claude Code session, so it must be concise — only include what Claude would get wrong without it.

## Step 1: Ask what to set up

Use AskUserQuestion to ask the user:
- "Which CLAUDE.md files should /init set up?" with options: "Project CLAUDE.md" | "Personal CLAUDE.local.md" | "Both project + personal"

## Step 2: Explore the codebase

Use tools to understand the project:
- Read key files: README, package.json, pyproject.toml, Cargo.toml, Makefile, existing CLAUDE.md
- Detect: build/test/lint commands, languages, frameworks, project structure
- Detect: code style rules, required env vars, gotchas
- Check for formatter config (ruff, black, prettier, etc.)

## Step 3: Write CLAUDE.md

Write a minimal CLAUDE.md at the project root.

Include:
- Build/test/lint commands that aren't standard
- Code style rules that DIFFER from defaults
- Required env vars or setup steps
- Non-obvious gotchas

Exclude:
- File structure (Claude can discover this)
- Standard conventions Claude already knows
- Generic advice

Prefix with:
```
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
```"""


def clear_command_call(args: str, context: CommandContext) -> LocalCommandResult:
    if hasattr(context.conversation, "clear"):
        context.conversation.clear()

    if hasattr(context.history, "events"):
        context.history.events.clear()

    return LocalCommandResult(
        type="text",
        value="Conversation cleared.",
    )


def help_command_call(args: str, context: CommandContext) -> LocalCommandResult:
    registry = get_command_registry()
    query = args.strip()

    if query:
        commands = registry.find_commands(query, limit=50)
        header = f"Commands matching '{query}':"
    else:
        commands = registry.list_commands(include_hidden=False)
        header = "Available commands:"

    lines = [header, ""]

    for cmd in commands:
        alias_str = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
        lines.append(f"  /{cmd.name}{alias_str}")
        lines.append(f"      {cmd.description}")
        if cmd.argument_hint:
            lines.append(f"      Usage: /{cmd.name} {cmd.argument_hint}")
        lines.append("")

    return LocalCommandResult(
        type="text",
        value="\n".join(lines),
    )


def exit_command_call(args: str, context: CommandContext) -> LocalCommandResult:
    return LocalCommandResult(
        type="text",
        value="Goodbye!",
    )


def cost_command_call(args: str, context: CommandContext) -> LocalCommandResult:
    tracker = context.cost_tracker
    if tracker is None:
        return LocalCommandResult(
            type="text",
            value="Cost tracking not available.",
        )

    lines = ["Session Cost:", ""]
    lines.append(f"  Total units: {tracker.total_units}")

    if tracker.events:
        lines.append("")
        lines.append("  Recent events:")
        for event in tracker.events[-10:]:
            lines.append(f"    - {event}")

    return LocalCommandResult(
        type="text",
        value="\n".join(lines),
    )


def resume_command_call(args: str, context: CommandContext) -> LocalCommandResult:
    sessions_dir = Path.home() / ".pixelbeat" / "sessions"
    
    if not sessions_dir.exists():
        return LocalCommandResult(type="text", value="No saved sessions found.")
    
    session_files = sorted(sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not session_files:
        return LocalCommandResult(type="text", value="No saved sessions found.")
    
    results = []
    for session_file in session_files[:20]:
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
            
            session_id = data.get("session_id", "")
            provider = data.get("provider", "unknown")
            model = data.get("model", "unknown")
            created_at = data.get("created_at", "")
            
            preview = ""
            conversation = data.get("conversation", {})
            messages = conversation.get("messages", [])
            
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    preview = content[:100]
                    if len(content) > 100:
                        preview += "..."
                    break
            
            results.append({
                "session_id": session_id,
                "provider": provider,
                "model": model,
                "created_at": created_at,
                "preview": preview
            })
        except Exception as e:
            results.append({
                "session_id": session_file.stem,
                "provider": "error",
                "model": str(e),
                "created_at": "",
                "preview": ""
            })
    
    if not results:
        return LocalCommandResult(type="text", value="No valid sessions found.")
    
    output_lines = ["Saved Sessions:"]
    for i, sess in enumerate(results, 1):
        created_str = sess["created_at"].replace("T", " ")[:19] if sess["created_at"] else ""
        output_lines.append(f"\n{i}. [bold]{sess['session_id']}[/bold]")
        output_lines.append(f"   Provider: {sess['provider']}")
        output_lines.append(f"   Model: {sess['model']}")
        if created_str:
            output_lines.append(f"   Created: {created_str}")
        if sess["preview"]:
            output_lines.append(f"   Preview: {sess['preview']}")
    
    return LocalCommandResult(type="text", value="\n".join(output_lines))


HELP_COMMAND = LocalCommand(
    name="help",
    description="Show available commands",
    aliases=["?"],
    argument_hint="[search_query]",
    supports_non_interactive=True,
)

CLEAR_COMMAND = LocalCommand(
    name="clear",
    description="Clear conversation history",
    aliases=["reset", "new"],
    supports_non_interactive=False,
)

EXIT_COMMAND = LocalCommand(
    name="exit",
    description="Exit the application",
    aliases=["quit", "q"],
    supports_non_interactive=True,
)

COST_COMMAND = LocalCommand(
    name="cost",
    description="Show session cost and usage",
    argument_hint="",
    supports_non_interactive=True,
)

RESUME_COMMAND = LocalCommand(
    name="resume",
    description="List saved sessions with message previews",
    argument_hint="",
    supports_non_interactive=True,
)

INIT_COMMAND = PromptCommand(
    name="init",
    description="Initialize CLAUDE.md file for the project",
    markdown_content=INIT_PROMPT,
    progress_message="analyzing your codebase",
    content_length=0,
    source="builtin",
)

HELP_COMMAND.set_call(help_command_call)
CLEAR_COMMAND.set_call(clear_command_call)
EXIT_COMMAND.set_call(exit_command_call)
COST_COMMAND.set_call(cost_command_call)
RESUME_COMMAND.set_call(resume_command_call)


def get_builtin_commands() -> list[Command]:
    return [
        HELP_COMMAND,
        CLEAR_COMMAND,
        EXIT_COMMAND,
        COST_COMMAND,
        RESUME_COMMAND,
        INIT_COMMAND,
    ]


def register_builtin_commands(registry: CommandRegistry | None = None) -> None:
    reg = registry or get_command_registry()
    for cmd in get_builtin_commands():
        reg.register(cmd)
