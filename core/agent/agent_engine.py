"""Agent engine for UI integration - bridges REPL logic with Qt dialogs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from core.agent.session import Session
from core.agent.cli.config import load_env_config
from core.agent.providers import get_provider_class
from core.agent.providers.base import BaseProvider
from core.agent.tool_context import ToolContext
from core.agent.tool_registry import ToolRegistry
from core.agent.tools import build_default_tools
from core.agent.agent_loop import run_agent_loop, AgentLoopResult, ToolEvent
from core.agent.cost_tracker import CostTracker
from core.agent.history import HistoryLog
from core.agent.cli.command_system import (
    CommandRegistry,
    create_command_context,
    execute_command_sync,
    register_builtin_commands,
)


class AgentEngine:
    """Agent engine that can be used with UI dialogs instead of terminal REPL."""

    def __init__(
        self,
        provider_name: str = "qwen",
        stream: bool = False,
        on_message: Optional[Callable[[str, bool], None]] = None,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
    ):
        self.provider_name = provider_name
        self.stream = stream
        self.on_message = on_message or (lambda msg, is_user: None)
        self.on_tool_call = on_tool_call or (lambda name, args: None)

        app_config = load_env_config()
        config = app_config.get("providers", {}).get(provider_name)

        if config is None or not config.get("api_key"):
            available_providers = app_config.get("providers", {})
            if available_providers:
                first_provider = list(available_providers.keys())[0]
                provider_name = first_provider
                config = available_providers[first_provider]
            else:
                raise ValueError("No API key configured")

        provider_class = get_provider_class(provider_name)
        self.provider: BaseProvider = provider_class(
            api_key=config["api_key"],
            base_url=config.get("base_url"),
            model=config.get("default_model")
        )

        self.session = Session.create(
            provider_name,
            self.provider.model
        )

        self.tool_registry = ToolRegistry(build_default_tools())
        self.tool_context = ToolContext(workspace_root=Path.cwd())

        self.cost_tracker = CostTracker()
        self.history_log = HistoryLog()

        self.command_registry = CommandRegistry()
        register_builtin_commands(self.command_registry)

        self.command_context = create_command_context(
            workspace_root=Path.cwd(),
            conversation=self.session.conversation,
            cost_tracker=self.cost_tracker,
            history=self.history_log,
        )

    def process_message(self, message: str) -> str:
        """Process a user message and return the agent response."""
        if message.startswith("/"):
            return self._handle_command(message)

        return self._chat(message)

    def _handle_command(self, command: str) -> str:
        raw = command.strip()
        if raw in ("/exit", "/quit", "/q"):
            return "[SYSTEM] Session ended."

        if raw == "/help":
            return (
                "Available commands:\n"
                "/help - Show this help\n"
                "/exit - End session\n"
                "/tools - List available tools\n"
                "/cost - Show cost tracking\n"
                "/clear - Clear conversation\n"
                "/save - Save session"
            )

        if raw == "/tools":
            tools = self.tool_registry.list_specs()
            lines = [f"Available tools ({len(tools)}):"]
            for spec in tools:
                lines.append(f"  - {spec.name}: {spec.description}")
            return "\n".join(lines)

        if raw == "/cost":
            return f"Total cost units: {self.cost_tracker.total_units}"

        if raw == "/clear":
            self.session.conversation.messages.clear()
            return "Conversation cleared."

        if raw == "/save":
            self.session.save()
            return f"Session saved: {self.session.session_id}"

        parts = raw[1:].split(maxsplit=1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        try:
            success, result_text, error = execute_command_sync(
                cmd_name, args, self.command_context
            )
            if success:
                return result_text or "Command executed successfully."
            else:
                return f"Error: {error}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _chat(self, message: str, max_turns: int = 20) -> str:
        self.session.conversation.add_user_message(message)
        self.on_message(message, is_user=True)

        response_text = ""
        try:
            result: AgentLoopResult = run_agent_loop(
                conversation=self.session.conversation,
                provider=self.provider,
                tool_registry=self.tool_registry,
                tool_context=self.tool_context,
                max_turns=max_turns,
                stream=self.stream,
                on_event=self._on_tool_event,
            )
            response_text = result.response_text
        except Exception as e:
            response_text = f"Error: {str(e)}"

        if response_text:
            self.on_message(response_text, is_user=False)
            self.session.save()

        return response_text

    def _on_tool_event(self, event: ToolEvent) -> None:
        if event.kind == "tool_use":
            self.on_tool_call(event.tool_name, event.tool_input or {})

    def close(self):
        """Clean up resources."""
        if self.session.conversation and self.session.conversation.messages:
            self.session.save()
