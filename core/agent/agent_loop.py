"""Agent loop for multi-turn tool calling."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from .conversation import Conversation, TextContentBlock, ToolUseContentBlock
from .providers.base import BaseProvider, ChatResponse
from .tool_registry import ToolRegistry
from .tool_context import ToolContext


def _is_anthropic_provider(provider: BaseProvider) -> bool:
    return False


def _build_openai_tool_result_content(result_output: Any) -> str:
    if isinstance(result_output, str):
        return result_output
    return json.dumps(result_output, ensure_ascii=False)


def summarize_tool_result(name: str, output: Any) -> str:
    if not isinstance(output, dict):
        return str(output)
    if name.lower() == "write":
        path = output.get("filePath") or output.get("file_path")
        op = output.get("type")
        return f"{name} · {path} · {op}"
    if name.lower() == "edit":
        path = output.get("filePath") or output.get("file_path")
        replace_all = output.get("replaceAll")
        return f"{name} · {path} · replaceAll={replace_all}"
    if name.lower() == "read":
        if output.get("type") == "text" and isinstance(output.get("file"), dict):
            f = output["file"]
            path = f.get("filePath")
            num = f.get("numLines")
            total = f.get("totalLines")
            start = f.get("startLine")
            return f"{name} · {path} · lines={start}-{(start or 1) + (num or 0) - 1}/{total}"
        if output.get("type") == "file_unchanged" and isinstance(output.get("file"), dict):
            return f"{name} · {output['file'].get('filePath')} · unchanged"
        return f"{name}"
    if name.lower() == "bash":
        code = output.get("exit_code")
        return f"{name} · exit={code}"
    keys = ", ".join(list(output.keys())[:3])
    return f"{name} · {keys}"


@dataclass(frozen=True)
class ToolEvent:
    kind: str
    tool_name: str
    tool_input: dict[str, Any] | None = None
    tool_output: Any | None = None
    tool_use_id: str | None = None
    is_error: bool = False
    error: str | None = None


@dataclass(frozen=True)
class AgentLoopResult:
    response_text: str
    usage: dict[str, Any] | None = None
    num_turns: int = 0


ToolEventHandler = Callable[[ToolEvent], None]
TextChunkHandler = Callable[[str], None]


def _safe_call_handler(handler: ToolEventHandler | None, event: ToolEvent) -> None:
    if handler is None:
        return
    try:
        handler(event)
    except Exception:
        return


def _emit_text_chunks(handler: TextChunkHandler | None, text: str, *, chunk_size: int = 12) -> None:
    if handler is None or not text:
        return
    if chunk_size <= 0:
        chunk_size = len(text)
    for idx in range(0, len(text), chunk_size):
        try:
            handler(text[idx: idx + chunk_size])
        except Exception:
            return


def _call_provider_for_turn(
    *,
    provider: BaseProvider,
    api_messages: list[dict[str, Any]],
    call_kwargs: dict[str, Any],
    stream: bool,
    on_text_chunk: TextChunkHandler | None,
) -> tuple[Any, bool]:
    if stream:
        try:
            response = provider.chat_stream_response(
                api_messages,
                on_text_chunk=on_text_chunk,
                **call_kwargs,
            )
            if not isinstance(response, ChatResponse):
                raise TypeError("Structured streaming must return ChatResponse")
            return response, True
        except NotImplementedError:
            pass
        except Exception:
            pass

    response = provider.chat(api_messages, **call_kwargs)
    return response, False


def summarize_tool_use(name: str, tool_input: dict[str, Any]) -> str:
    lowered = name.lower()
    if lowered == "bash":
        cmd = tool_input.get("command")
        if isinstance(cmd, str):
            s = cmd.strip().replace("\n", " ")
            return s if len(s) <= 80 else s[:77] + "..."
        return ""
    if lowered in {"read", "write", "edit"}:
        p = tool_input.get("file_path") or tool_input.get("filePath") or tool_input.get("path")
        if isinstance(p, str):
            extra = ""
            if lowered == "read":
                off = tool_input.get("offset")
                lim = tool_input.get("limit")
                if isinstance(off, int) or isinstance(lim, int):
                    start = off if isinstance(off, int) else 1
                    if isinstance(lim, int):
                        extra = f" · lines {start}-{start + lim - 1}"
            return f"{p}{extra}"
        return ""
    if lowered == "webfetch":
        url = tool_input.get("url")
        return url if isinstance(url, str) else ""
    if lowered == "websearch":
        q = tool_input.get("query")
        return q if isinstance(q, str) else ""
    if lowered == "askuserquestion":
        qs = tool_input.get("questions")
        if isinstance(qs, list):
            return f"{len(qs)} question(s)"
        return ""
    return ""


def run_agent_loop(
    conversation: Conversation,
    provider: BaseProvider,
    tool_registry: ToolRegistry,
    tool_context: ToolContext,
    system_prompt: str = "",
    max_turns: int = 20,
    stream: bool = False,
    verbose: bool = False,
    on_event: ToolEventHandler | None = None,
    on_text_chunk: TextChunkHandler | None = None,
) -> AgentLoopResult:
    """Run agent loop: LLM -> tools -> LLM until no more tools or max turns.

    Args:
        conversation: Conversation with initial user message
        provider: LLM provider
        tool_registry: Tool registry to use
        tool_context: Tool context
        system_prompt: System prompt for the agent
        max_turns: Maximum tool turns before stopping
        stream: Whether to stream responses
        verbose: Whether to print tool calls/results
        on_event: Optional callback for tool events
        on_text_chunk: Optional callback for incremental user-visible text chunks

    Returns:
        AgentLoopResult with final text response, usage info, and turn count
    """
    tool_schemas = []
    for spec in tool_registry.list_specs():
        tool_schemas.append({
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_schema,
        })

    openai_messages: list[dict[str, Any]] = []
    last_user_visible_message: str | None = None

    for msg in conversation.messages:
        if isinstance(msg.content, str):
            openai_messages.append({"role": msg.role, "content": msg.content})

    total_usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
    turn_count = 0

    for turn in range(max_turns):
        api_messages = openai_messages

        call_kwargs: dict[str, Any] = {"tools": tool_schemas}
        if turn == 0 and system_prompt:
            api_messages = [{"role": "system", "content": system_prompt}, *api_messages]

        response, streamed_live_text = _call_provider_for_turn(
            provider=provider,
            api_messages=api_messages,
            call_kwargs=call_kwargs,
            stream=stream,
            on_text_chunk=on_text_chunk,
        )
        turn_count += 1

        if response.usage:
            total_usage["input_tokens"] += response.usage.get("input_tokens", 0)
            total_usage["output_tokens"] += response.usage.get("output_tokens", 0)

        final_assistant_content = response.content or ""

        conversation.add_assistant_message(final_assistant_content)
        openai_assistant_msg: dict[str, Any] = {"role": "assistant", "content": final_assistant_content}
        if response.tool_uses:
            tool_calls = []
            for tu in response.tool_uses:
                tool_calls.append({
                    "id": tu["id"],
                    "type": "function",
                    "function": {
                        "name": tu["name"],
                        "arguments": json.dumps(tu["input"], ensure_ascii=False),
                    },
                })
            openai_assistant_msg["tool_calls"] = tool_calls
        openai_messages.append(openai_assistant_msg)

        tool_uses = response.tool_uses or []

        if not tool_uses:
            if stream and final_assistant_content and not streamed_live_text:
                _emit_text_chunks(on_text_chunk, final_assistant_content)
            if (final_assistant_content or "").strip() == "" and last_user_visible_message is not None:
                return AgentLoopResult(
                    response_text=last_user_visible_message,
                    usage=total_usage if total_usage["input_tokens"] > 0 or total_usage["output_tokens"] > 0 else None,
                    num_turns=turn_count,
                )
            return AgentLoopResult(
                response_text=final_assistant_content,
                usage=total_usage if total_usage["input_tokens"] > 0 or total_usage["output_tokens"] > 0 else None,
                num_turns=turn_count,
            )

        for tool_use in tool_uses:
            tool_id = tool_use["id"]
            tool_name = tool_use["name"]
            tool_input = tool_use["input"]

            try:
                _safe_call_handler(
                    on_event,
                    ToolEvent(
                        kind="tool_use",
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_use_id=tool_id,
                    ),
                )
                from .tool_protocol import ToolCall
                call = ToolCall(name=tool_name, input=tool_input, tool_use_id=tool_id)
                result = tool_registry.dispatch(call, tool_context)
                result_output = result.output
                if tool_name.lower() == "sendusermessage" and isinstance(result_output, dict):
                    msg = result_output.get("message")
                    if isinstance(msg, str):
                        last_user_visible_message = msg

                if verbose:
                    use_summary = summarize_tool_use(tool_name, tool_input)
                    if use_summary:
                        print(f"{tool_name} · {use_summary}")
                    summary = summarize_tool_result(tool_name, result_output)
                    print(f"{summary}")

                _safe_call_handler(
                    on_event,
                    ToolEvent(
                        kind="tool_result",
                        tool_name=tool_name,
                        tool_output=result_output,
                        tool_use_id=tool_id,
                        is_error=result.is_error,
                    ),
                )
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": _build_openai_tool_result_content(result_output),
                })
            except Exception as e:
                error_str = f"Error: {e}"
                if verbose:
                    print(f"[Tool Error] {error_str}")
                _safe_call_handler(
                    on_event,
                    ToolEvent(
                        kind="tool_error",
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_use_id=tool_id,
                        is_error=True,
                        error=error_str,
                    ),
                )
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": error_str,
                })

    return AgentLoopResult(
        response_text="[Max tool turns reached]",
        usage=total_usage if total_usage["input_tokens"] > 0 or total_usage["output_tokens"] > 0 else None,
        num_turns=turn_count,
    )
