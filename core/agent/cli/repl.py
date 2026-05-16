"""Interactive REPL for PixelBeat agent."""

from __future__ import annotations

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.styles import Style
    from prompt_toolkit.completion import WordCompleter
    try:
        from prompt_toolkit.completion import FuzzyCompleter
    except Exception:
        FuzzyCompleter = None
    from prompt_toolkit.key_binding import KeyBindings
except ModuleNotFoundError:
    class FileHistory:
        def __init__(self, *args, **kwargs):
            pass

    class AutoSuggestFromHistory:
        def __init__(self, *args, **kwargs):
            pass

    class Style:
        @staticmethod
        def from_dict(*args, **kwargs):
            return None

    class WordCompleter:
        def __init__(self, *args, **kwargs):
            pass
    FuzzyCompleter = None

    class KeyBindings:
        def __init__(self, *args, **kwargs):
            pass

    class PromptSession:
        def __init__(self, *args, **kwargs):
            pass

        def prompt(self, *args, **kwargs):
            raise EOFError()

try:
    from rich.console import Console, Group
    from rich.align import Align
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.columns import Columns
except ModuleNotFoundError:
    class Console:
        def print(self, *args, **kwargs):
            return None

    Group = None
    Align = None
    Panel = None
    Table = None
    Text = None
    Columns = None

    class Markdown:
        def __init__(self, text: str):
            self.text = text

from pathlib import Path
import asyncio
import sys
import json
from typing import Any

from core.agent.session import Session
from core.agent.cli.config import get_provider_config, load_env_config
from core.agent.providers import get_provider_class
from core.agent.providers.anthropic_provider import AnthropicProvider
from core.agent.providers.base import ChatMessage
from core.agent.tool_context import ToolContext
from core.agent.tool_registry import ToolRegistry
from core.agent.tools import build_default_tools
from core.agent.tool_protocol import ToolCall
from core.agent.agent_loop import ToolEvent, run_agent_loop, summarize_tool_result, summarize_tool_use

from core.agent.cli.command_system import (
    CommandRegistry,
    CommandResult,
    create_command_context,
    execute_command_async,
    execute_command_sync,
    register_builtin_commands,
)
from core.agent.cost_tracker import CostTracker
from core.agent.history import HistoryLog


class PixelBeatREPL:
    def __init__(self, provider_name: str = "openai", stream: bool = False):
        self.console = Console()
        self.provider_name = provider_name
        self.stream = stream
        self.multiline_mode = False

        app_config = load_env_config()
        config = app_config.get("providers", {}).get(provider_name)
        
        if config is None or not config.get("api_key"):
            available_providers = app_config.get("providers", {})
            if available_providers:
                first_provider = list(available_providers.keys())[0]
                self.console.print(f"[yellow]Warning: {provider_name} not configured, using {first_provider}[/yellow]")
                provider_name = first_provider
                config = available_providers[first_provider]
            else:
                self.console.print("[red]Error: No API key configured.[/red]")
                self.console.print("Run [bold]pixelbeat login[/bold] to configure.")
                sys.exit(1)

        provider_class = get_provider_class(provider_name)
        self.provider = provider_class(
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
        self.tool_context.ask_user = self._ask_user_questions
        self._current_status = None
        self.tool_context.permission_handler = self._handle_permission_request

        self._original_built_ins = [
            "/",
            "/help",
            "/exit",
            "/quit",
            "/q",
            "/clear",
            "/save",
            "/load",
            "/multiline",
            "/stream",
            "/tools",
            "/tool",
            "/cost",
            "/resume",
            "/init",
        ]
        self._built_in_commands = list(self._original_built_ins)

        self._init_command_system()

        history_file = Path.home() / ".pixelbeat" / "history"
        history_file.parent.mkdir(parents=True, exist_ok=True)

        self.completer = WordCompleter(self._get_slash_command_words(), ignore_case=True)

        self.bindings = KeyBindings()
        if hasattr(self.bindings, "add"):
            @self.bindings.add("/")
            def _show_slash_completions(event):
                buf = event.current_buffer
                if buf.text == "":
                    buf.insert_text("/")
                    buf.start_completion(select_first=False)

        self.prompt_session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.completer,
            style=Style.from_dict({
                'prompt': 'bold blue',
            }),
            key_bindings=self.bindings,
            complete_while_typing=True,
        )

    def _ask_user_questions(self, questions: list[dict]) -> dict[str, str]:
        if self._current_status is not None:
            try:
                self._current_status.stop()
            except Exception:
                pass

        answers: dict[str, str] = {}
        for q in questions:
            question_text = str(q.get("question", "")).strip()
            options = q.get("options") or []
            multi = bool(q.get("multiSelect", False))
            if not question_text or not isinstance(options, list) or len(options) < 2:
                continue

            self.console.print(f"\n[bold]{question_text}[/bold]")
            labels: list[str] = []
            for i, opt in enumerate(options, start=1):
                label = str((opt or {}).get("label", "")).strip()
                desc = str((opt or {}).get("description", "")).strip()
                labels.append(label)
                self.console.print(f"  {i}. {label}  [dim]{desc}[/dim]")
            other_idx = len(labels) + 1
            self.console.print(f"  {other_idx}. Other  [dim]Provide custom text[/dim]")

            prompt = "Select (comma-separated) > " if multi else "Select > "
            raw = input(prompt).strip()
            if not raw:
                choice_str = "1"
            else:
                choice_str = raw

            selected: list[str] = []
            parts = [p.strip() for p in choice_str.split(",") if p.strip()]
            if not parts:
                parts = ["1"]
            for part in parts:
                try:
                    idx = int(part)
                except ValueError:
                    idx = -1
                if idx == other_idx:
                    free = input("Other > ").strip()
                    if free:
                        selected.append(free)
                    continue
                if 1 <= idx <= len(labels):
                    selected.append(labels[idx - 1])
            if not selected:
                selected = [labels[0]]
            answers[question_text] = ", ".join(selected) if multi else selected[0]

        if self._current_status is not None:
            try:
                self._current_status.start()
            except Exception:
                pass

        return answers

    def _handle_permission_request(
        self,
        tool_name: str,
        message: str,
        suggestion: str | None,
    ) -> tuple[bool, bool]:
        if self._current_status is not None:
            try:
                self._current_status.stop()
            except Exception:
                pass

        self.console.print("")
        self.console.print("[bold yellow]⚠ Permission Required[/bold yellow]")
        self.console.print(f"  {message}")
        self.console.print("")

        options: list[tuple[str, str]] = [
            ("y", "Yes, allow this action"),
            ("n", "No, deny this action"),
        ]

        self.console.print("[bold]Options:[/bold]")
        for i, (key, desc) in enumerate(options, start=1):
            self.console.print(f"  {i}. [{key}] {desc}")
        self.console.print("")

        choice = input("Select option> ").strip().lower()

        if choice in ("1", "y", "yes", ""):
            return True, False
        elif choice in ("2", "n", "no"):
            return False, False

        self.console.print("[dim]Invalid choice, defaulting to deny.[/dim]")
        return False, False

    def _init_command_system(self):
        register_builtin_commands(None)

        self.command_registry = CommandRegistry()
        register_builtin_commands(self.command_registry)

        self.cost_tracker = CostTracker()
        self.history_log = HistoryLog()

        self.command_context = create_command_context(
            workspace_root=Path.cwd(),
            conversation=self.session.conversation,
            cost_tracker=self.cost_tracker,
            history=self.history_log,
        )

        self._update_built_in_commands_with_command_system()

    def _update_built_in_commands_with_command_system(self):
        self._built_in_commands = list(self._original_built_ins)

        try:
            for cmd in self.command_registry.list_commands():
                cmd_name = f"/{cmd.name}"
                if cmd_name not in self._built_in_commands:
                    self._built_in_commands.append(cmd_name)
                for alias in cmd.aliases:
                    alias_name = f"/{alias}"
                    if alias_name not in self._built_in_commands:
                        self._built_in_commands.append(alias_name)
        except Exception:
            pass

    def _try_execute_new_command(self, command: str, args: str) -> tuple[bool, str | None]:
        try:
            success, result_text, error = execute_command_sync(
                command, args, self.command_context
            )
            if success:
                return True, result_text
            else:
                return False, error
        except Exception as e:
            return False, str(e)

    async def _try_execute_command_async(self, command: str, args: str) -> CommandResult:
        try:
            return await execute_command_async(command, args, self.command_context)
        except Exception as e:
            return CommandResult.error(command, str(e))

    def _handle_command_result(self, result: CommandResult) -> bool:
        if not result.success:
            if result.error:
                self.console.print(f"[red]{result.error}[/red]")
            return True

        if result.result_type == "text":
            if result.text:
                self.console.print("\n" + result.text)
                self.console.print()
            return True

        elif result.result_type == "prompt":
            prompt_text = ""
            for item in result.prompt_content:
                if item.get("type") == "text":
                    prompt_text = item.get("text", "")
                    break

            if prompt_text:
                self.console.print("[dim]Initializing workspace setup...[/dim]")
                self.chat(prompt_text, max_turns=100)
            return True

        elif result.result_type == "skip":
            return True

        return False

    def _get_slash_command_words(self) -> list[str]:
        words = list(self._built_in_commands)
        return words

    def _refresh_completer(self) -> None:
        try:
            words = self._get_slash_command_words()
            try:
                base = WordCompleter(words, ignore_case=True, match_middle=True)
            except TypeError:
                base = WordCompleter(words, ignore_case=True)
            self.completer = FuzzyCompleter(base) if FuzzyCompleter is not None else base
            if hasattr(self, "prompt_session") and getattr(self.prompt_session, "completer", None) is not None:
                self.prompt_session.completer = self.completer
        except Exception:
            return

    def _show_slash_palette(self, query: str | None = None) -> None:
        q = (query or "").strip().lower()
        self.console.print("\n[bold]Available commands:[/bold]")

        all_commands: list[tuple[str, str]] = []
        seen: set[str] = set()

        def add_command(name: str, desc: str) -> None:
            if name in seen:
                return
            seen.add(name)
            if q and q not in name.lower() and q not in desc.lower():
                return
            all_commands.append((name, desc))

        for cmd in self._original_built_ins:
            if cmd == "/":
                continue
            add_command(cmd, "")

        try:
            for cmd in self.command_registry.list_commands():
                cmd_name = f"/{cmd.name}"
                if cmd_name in self._original_built_ins:
                    continue
                alias_str = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                add_command(f"{cmd_name}{alias_str}", cmd.description)
        except Exception:
            pass

        all_commands.sort(key=lambda x: x[0].lower())
        for name, desc in all_commands:
            if desc:
                self.console.print(f"  {name}  [dim]- {desc}[/dim]")
            else:
                self.console.print(f"  {name}")

        self.console.print()

    def _display_cwd(self) -> str:
        cwd = str(Path.cwd())
        home = str(Path.home())
        if cwd.startswith(home):
            return cwd.replace(home, "~", 1)
        return cwd

    def _truncate_middle(self, text: str, limit: int) -> str:
        if limit <= 0 or len(text) <= limit:
            return text
        if limit <= 3:
            return text[:limit]
        head = max(1, (limit - 1) // 2)
        tail = max(1, limit - head - 1)
        return f"{text[:head]}…{text[-tail:]}"

    def _print_startup_header(self):
        from core.agent import __version__

        display_path = self._display_cwd()
        provider_label = f"{self.provider_name.upper()} Provider"
        model_label = self.provider.model or "Unknown model"

        mascot_ascii = "\n".join([
            "  /\\__/\\",
            " / o  o \\",
            "(  __  )",
            " \\/__/  ",
        ])

        if Panel is None or Group is None or Align is None or Table is None or Text is None or Columns is None:
            print(mascot_ascii)
            print(f"PixelBeat Agent v{__version__}")
            print(f"{model_label} · {provider_label}")
            print(f"{display_path}\n")
            return

        width = getattr(self.console, "width", 80)
        content_width = max(28, min(width - 12, 72))
        table = Table.grid(padding=(0, 1))
        table.add_column(style="bright_black", justify="right", no_wrap=True)
        table.add_column(style="white", ratio=1)
        table.add_row("Version", Text.assemble(("PixelBeat Agent", "bold white"), ("  ", ""), (f"v{__version__}", "bold cyan")))
        table.add_row("Model", Text(model_label, style="bold magenta"))
        table.add_row("Provider", Text(provider_label, style="bold green"))
        table.add_row("Workspace", Text(self._truncate_middle(display_path, content_width - 12), style="bold blue"))

        footer = Text("/help  •  /tools  •  /stream  •  /exit", style="dim")
        mascot_block = Text(mascot_ascii, style="bold orange3", no_wrap=True)
        body = Group(
            Columns([mascot_block, table], align="center", expand=False),
            Text(""),
            Align.center(footer),
        )
        header = Panel(
            body,
            border_style="bright_black",
            title="[bold bright_cyan] PIXELBEAT AGENT [/bold bright_cyan]",
            subtitle="[dim]interactive terminal[/dim]",
            padding=(1, 2),
        )
        self.console.print(header)
        self.console.print()

    def run(self):
        self._print_startup_header()

        while True:
            try:
                self._refresh_completer()
                prompt_text = '... ' if self.multiline_mode else '❯ '
                user_input = self.prompt_session.prompt(
                    prompt_text,
                    multiline=self.multiline_mode
                )

                if not user_input.strip():
                    self.multiline_mode = False
                    continue

                if user_input.startswith('/'):
                    self.handle_command(user_input)
                    continue

                self.chat(user_input)
                self.multiline_mode = False

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
                self.multiline_mode = False
                continue
            except EOFError:
                if self.session.conversation and self.session.conversation.messages:
                    self.session.save()
                    self.console.print(f"\n[green]Session saved: {self.session.session_id}[/green]")
                self.console.print("[blue]Goodbye![/blue]")
                break

    def handle_command(self, command: str):
        raw = command.strip()
        if raw == "/":
            self._show_slash_palette()
            return
        if raw.startswith("/") and " " not in raw and raw.lower() not in (c.lower() for c in self._built_in_commands):
            query = raw[1:]
            if query:
                self._show_slash_palette(query=query)
                return

        if raw.startswith("/"):
            parts = raw[1:].split(maxsplit=1)
            cmd_name = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            special_commands = {
                'exit', 'quit', 'q',
                'help', 'tools', 'tool',
                'save', 'load', 'multiline', 'stream',
                'cost', 'resume',
                ''
            }

            if cmd_name == 'init':
                try:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self._try_execute_command_async(cmd_name, args)
                        )
                        result = future.result()

                    if result.success:
                        self._handle_command_result(result)
                    elif result.error:
                        self.console.print(f"[red]{result.error}[/red]")
                except Exception as e:
                    self.console.print(f"[red]Error executing /init: {e}[/red]")
                return

            if cmd_name not in special_commands:
                try:
                    handled, result_text = self._try_execute_new_command(cmd_name, args)
                    if handled:
                        if result_text:
                            self.console.print("\n" + result_text)
                        self.console.print()
                        return
                except Exception:
                    pass

                try:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self._try_execute_command_async(cmd_name, args)
                        )
                        result = future.result()

                    if result.success:
                        if self._handle_command_result(result):
                            return
                except Exception:
                    pass

        cmd = raw.lower()

        if cmd in ['/exit', '/quit', '/q']:
            if self.session.conversation and self.session.conversation.messages:
                self.session.save()
                self.console.print(f"[green]Session saved: {self.session.session_id}[/green]")
            self.console.print("[blue]Goodbye![/blue]")
            sys.exit(0)

        elif cmd == '/help':
            self.show_help()

        elif cmd == '/tools':
            names = [spec.name for spec in self.tool_registry.list_specs()]
            names.sort(key=str.lower)
            self.console.print("\n[bold]Available tools:[/bold]")
            for name in names:
                self.console.print(f"  - {name}")
            self.console.print()

        elif cmd.startswith('/tool'):
            parts = command.strip().split(maxsplit=2)
            if len(parts) < 2:
                self.console.print("[red]Usage: /tool <name> <json-input>[/red]")
                return
            name = parts[1]
            payload = {}
            if len(parts) == 3:
                try:
                    payload = json.loads(parts[2])
                except json.JSONDecodeError as e:
                    self.console.print(f"[red]Invalid JSON input: {e}[/red]")
                    return
            try:
                result = self.tool_registry.dispatch(ToolCall(name=name, input=payload), self.tool_context)
            except Exception as e:
                self.console.print(f"[red]Tool error: {e}[/red]")
                return
            self.console.print("\n[bold]Tool result:[/bold]")
            self.console.print(json.dumps(result.output, indent=2, ensure_ascii=False))
            self.console.print()

        elif cmd == '/clear':
            try:
                handled, result_text = self._try_execute_new_command('clear', '')
                if handled and result_text:
                    self.console.print("\n[green]" + result_text + "[/green]")
                    return
            except Exception:
                pass
            self.session.conversation.clear()
            self.console.print("[green]Conversation cleared.[/green]")

        elif cmd == '/save':
            self.save_session()

        elif cmd == '/multiline':
            self.multiline_mode = not self.multiline_mode
            status = "enabled" if self.multiline_mode else "disabled"
            self.console.print(f"[green]Multiline mode {status}.[/green]")
            if self.multiline_mode:
                self.console.print("[dim]Press Meta+Enter or Esc+Enter to submit.[/dim]")

        elif cmd == '/stream' or cmd.startswith('/stream '):
            parts = raw.split(maxsplit=1)
            if len(parts) == 1:
                status = "enabled" if self.stream else "disabled"
                self.console.print(f"[green]Stream mode {status}.[/green]")
                return

            action = parts[1].strip().lower()
            if action in {"on", "true", "1", "enable", "enabled"}:
                self.stream = True
            elif action in {"off", "false", "0", "disable", "disabled"}:
                self.stream = False
            elif action == "toggle":
                self.stream = not self.stream
            else:
                self.console.print("[red]Usage: /stream [on|off|toggle][/red]")
                return

            status = "enabled" if self.stream else "disabled"
            self.console.print(f"[green]Stream mode {status}.[/green]")

        elif cmd.startswith('/load'):
            parts = command.strip().split(maxsplit=1)
            if len(parts) < 2:
                self.console.print("[red]Usage: /load <session-id>[/red]")
            else:
                session_id = parts[1]
                self.load_session(session_id)

        elif cmd == '/cost':
            try:
                handled, result_text = self._try_execute_new_command('cost', '')
                if handled and result_text:
                    self.console.print("\n" + result_text)
                    return
            except Exception:
                pass

        elif cmd == '/resume':
            try:
                handled, result_text = self._try_execute_new_command('resume', '')
                if handled and result_text:
                    self.console.print("\n" + result_text)
                    return
            except Exception:
                pass

        else:
            if raw.startswith("/"):
                self.console.print(f"[red]Unknown command: {command}[/red]")

    def show_help(self):
        help_text = """
**Available Commands:**

- `/` - Show all commands
- `/help` - Show this help message
- `/exit`, `/quit`, `/q` - Exit the REPL
- `/clear`, `/reset`, `/new` - Clear conversation history
- `/save` - Save current session
- `/load <session-id>` - Load a previous session
- `/multiline` - Toggle multiline input mode
- `/stream [on|off|toggle]` - Toggle live response rendering
- `/tools` - List available built-in tools
- `/tool <name> <json>` - Run a tool directly
- `/cost` - Show session cost and usage
- `/resume` - List saved sessions with message previews
- `/init` - Create CLAUDE.md file for the project

**Usage:**
- Type your message and press Enter to chat
- Use Tab for command completion
- Press Ctrl+C to interrupt current operation
- Press Ctrl+D to exit
- Use `/multiline` for multi-paragraph inputs
"""
        self.console.print(Markdown(help_text))

    def chat(self, user_input: str, max_turns: int = 20):
        self.session.conversation.add_user_message(user_input)

        try:
            self.console.print("\n[bold]Assistant[/bold]")

            stream_started = False

            def _stop_status_once() -> None:
                nonlocal stream_started
                if self._current_status is not None and not stream_started:
                    try:
                        self._current_status.stop()
                    except Exception:
                        pass
                stream_started = True

            def on_event(ev: ToolEvent) -> None:
                if ev.kind == "tool_use":
                    summary = summarize_tool_use(ev.tool_name, ev.tool_input or {})
                    if isinstance(summary, str) and summary:
                        summary = self._shorten_path_text(summary)
                    suffix = f" [dim]({summary})[/dim]" if summary else ""
                    self.console.print(f"[dim]•[/dim] [cyan]{ev.tool_name}[/cyan]{suffix} [dim]running...[/dim]")
                    return
                if ev.kind == "tool_result":
                    if ev.is_error:
                        msg = ""
                        if isinstance(ev.tool_output, dict) and isinstance(ev.tool_output.get("error"), str):
                            msg = ev.tool_output["error"]
                        self.console.print(f"[red]  ↳ {msg or 'Error'}[/red]")
                        return
                    msg = summarize_tool_result(ev.tool_name, ev.tool_output)
                    if isinstance(msg, str):
                        prefix = f"{ev.tool_name} · "
                        if msg.startswith(prefix):
                            msg = msg[len(prefix):]
                        msg = self._shorten_path_text(msg)
                    self.console.print(f"[dim]  ↳ {msg}[/dim]")
                    return
                if ev.kind == "tool_error":
                    msg = ev.error or "Error"
                    self.console.print(f"[red]  ↳ {msg}[/red]")

            def on_text_chunk(chunk: str) -> None:
                if not chunk:
                    return
                _stop_status_once()
                self.console.print(chunk, end="", markup=False, highlight=False, soft_wrap=True)

            self._current_status = self.console.status("[dim]Thinking...[/dim]", spinner="dots")
            with self._current_status:
                result = run_agent_loop(
                    conversation=self.session.conversation,
                    provider=self.provider,
                    tool_registry=self.tool_registry,
                    tool_context=self.tool_context,
                    max_turns=max_turns,
                    stream=self.stream,
                    verbose=False,
                    on_event=on_event,
                    on_text_chunk=on_text_chunk if self.stream else None,
                )
            self._current_status = None

            if result.usage:
                input_tokens = result.usage.get("input_tokens", 0)
                output_tokens = result.usage.get("output_tokens", 0)
                if input_tokens > 0 or output_tokens > 0:
                    self.cost_tracker.record(
                        f"turn_{result.num_turns}_tokens",
                        input_tokens + output_tokens
                    )
                    if hasattr(self, 'command_context') and self.command_context:
                        self.command_context.cost_tracker = self.cost_tracker

            if self.stream and stream_started:
                self.console.print()
                self.console.print()
            else:
                self.console.print(Markdown(result.response_text))
                self.console.print("\n")

        except Exception as e:
            error_str = str(e)

            if "401" in error_str or "authentication" in error_str.lower() or "令牌" in error_str:
                self.console.print(f"\n[red]❌ Authentication Error: {e}[/red]")
                self.console.print("\n[yellow]Your API key appears to be invalid or expired.[/yellow]")

                from rich.prompt import Prompt
                choice = Prompt.ask(
                    "\nWould you like to reconfigure your API key now?",
                    choices=["y", "n"],
                    default="y"
                )

                if choice == "y":
                    self._handle_relogin()
                else:
                    self.console.print("\n[dim]You can run [bold]pixelbeat login[/bold] later to update your API key.[/dim]")
            else:
                self.console.print(f"\n[red]Error: {e}[/red]")
                import traceback
                traceback.print_exc()

    def _handle_relogin(self):
        from rich.prompt import Prompt
        from core.agent.providers import PROVIDER_INFO

        self.console.print("\n[bold blue]🔑 Reconfigure API Key[/bold blue]\n")

        provider_names = list(PROVIDER_INFO.keys())
        self.console.print("[bold]Available providers:[/bold]")
        for name, info in PROVIDER_INFO.items():
            self.console.print(f"  [cyan]{name}[/cyan] - {info['label']} (default model: {info['default_model']})")
        self.console.print()

        provider = Prompt.ask(
            "Select LLM provider",
            choices=provider_names,
            default=self.provider_name if self.provider_name in provider_names else "openai"
        )

        info = PROVIDER_INFO[provider]

        api_key = Prompt.ask(
            f"Enter {provider.upper()} API Key",
            password=True
        )

        if not api_key:
            self.console.print("\n[red]Error: API Key cannot be empty[/red]")
            return

        self.console.print(f"\n[dim]Default:[/dim] {info['default_base_url']}")
        base_url = Prompt.ask(
            f"{provider.upper()} Base URL",
            default=info["default_base_url"]
        )

        self.console.print(f"\n[dim]Available models:[/dim] {', '.join(info['available_models'])}")
        self.console.print(f"[dim]Default:[/dim] [bold]{info['default_model']}[/bold]")
        default_model = Prompt.ask(
            f"{provider.upper()} Default Model",
            default=info["default_model"]
        )

        env_path = Path.cwd() / ".env"
        env_content = ""
        if env_path.exists():
            env_content = env_path.read_text()

        lines = []
        updated = False
        for line in env_content.split("\n"):
            if line.startswith(f"{provider.upper()}_API_KEY="):
                lines.append(f"{provider.upper()}_API_KEY={api_key}")
                updated = True
            elif line.startswith(f"{provider.upper()}_BASE_URL="):
                lines.append(f"{provider.upper()}_BASE_URL={base_url}")
                updated = True
            elif line.startswith(f"{provider.upper()}_DEFAULT_MODEL="):
                lines.append(f"{provider.upper()}_DEFAULT_MODEL={default_model}")
                updated = True
            else:
                lines.append(line)

        if not updated:
            lines.append(f"{provider.upper()}_API_KEY={api_key}")
            lines.append(f"{provider.upper()}_BASE_URL={base_url}")
            lines.append(f"{provider.upper()}_DEFAULT_MODEL={default_model}")

        env_path.write_text("\n".join(lines))

        self.console.print(f"\n[green]✓ {provider.upper()} API Key updated successfully![/green]\n")

        config = {
            "api_key": api_key,
            "base_url": base_url,
            "default_model": default_model
        }

        provider_class = get_provider_class(provider)

        self.provider = provider_class(
            api_key=config["api_key"],
            base_url=config.get("base_url"),
            model=config.get("default_model")
        )
        self.provider_name = provider

        self.console.print("[green]✓ Provider reinitialized. You can continue chatting![/green]\n")

    def _shorten_path_text(self, text: str) -> str:
        root = str(self.tool_context.workspace_root)
        cwd = str(self.tool_context.cwd or self.tool_context.workspace_root)
        for base in (cwd, root):
            prefix = base.rstrip("/") + "/"
            if text.startswith(prefix):
                return "./" + text[len(prefix):]
            text = text.replace(prefix, "")
        return text

    def save_session(self):
        self.session.save()
        self.console.print(f"[green]Session saved: {self.session.session_id}[/green]")

    def load_session(self, session_id: str):
        loaded_session = Session.load(session_id)
        if loaded_session is None:
            self.console.print(f"[red]Session not found: {session_id}[/red]")
            return

        self.session = loaded_session
        self.console.print(f"[green]Session loaded: {session_id}[/green]")
        self.console.print(f"[dim]Provider: {loaded_session.provider}, Model: {loaded_session.model}[/dim]")
        self.console.print(f"[dim]Messages: {len(loaded_session.conversation.messages)}[/dim]")

        if loaded_session.conversation.messages:
            self.console.print("\n[bold]Conversation History:[/bold]")
            for msg in loaded_session.conversation.messages[-5:]:
                role_color = "blue" if msg.role == "user" else "green"
                content = msg.content if hasattr(msg, 'content') else str(msg)
                self.console.print(f"[{role_color}]{msg.role}[/{role_color}]: {content[:100]}...")
