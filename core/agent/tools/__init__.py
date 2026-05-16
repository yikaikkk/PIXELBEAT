"""Default tool implementations for PixelBeat agent."""

from __future__ import annotations

import base64
import difflib
import fnmatch
import glob as globlib
import mimetypes
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Iterator

from ..tool_context import ToolContext
from ..tool_protocol import ToolResult
from ..tool_registry import ToolSpec, Tool

_VCS_DIRS = {".git", ".svn", ".hg", ".bzr", ".jj", ".sl"}

_DANGEROUS_PATTERNS = [
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\breboot\b", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\b\s+if=", re.IGNORECASE),
    re.compile(r"\brm\b.*\s+-rf\s+/\s*$", re.IGNORECASE),
    re.compile(r"\brm\b.*\s+-rf\s+/\s+"),
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.IGNORECASE),
]


def _truncate(s: str, limit: int = 20000) -> str:
    if len(s) <= limit:
        return s
    return s[:limit] + "\n\n... [truncated] ..."


def _iter_files(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _VCS_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


class ReadTool:
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="Read",
            description="Read a file from the local filesystem.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "file_path": {"type": "string"},
                    "offset": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
                "required": ["file_path"],
            },
            is_read_only=True,
            max_result_size_chars=1_000_000,
        )

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        file_path = tool_input["file_path"]
        if not isinstance(file_path, str):
            raise ValueError("file_path must be a string")

        if file_path.startswith(("http://", "https://")):
            return ToolResult(
                name="Read",
                output={"error": f"The 'Read' tool is for local files only. Use 'WebFetch' to access URLs: {file_path}"},
                is_error=True
            )

        limit = tool_input.get("limit", 2000)
        offset = tool_input.get("offset", 1)
        if not isinstance(limit, int) or limit < 1 or limit > 2000:
            raise ValueError("limit must be an integer between 1 and 2000")
        if not isinstance(offset, int) or offset < 1:
            raise ValueError("offset must be an integer >= 1")

        path = context.ensure_allowed_path(file_path)
        if not path.exists():
            return ToolResult(name="Read", output={"error": f"file not found: {path}"}, is_error=True)
        if path.is_dir():
            return ToolResult(name="Read", output={"error": f"path is a directory: {path}"}, is_error=True)

        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            return self._read_image(path, context)

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise ValueError(str(e)) from e

        lines = text.splitlines()
        start = offset - 1
        end = start + limit
        sliced = lines[start:end]
        numbered = "\n".join(f"{i + offset}\t{line}" for i, line in enumerate(sliced))
        context.mark_file_read(path)
        return ToolResult(
            name="Read",
            output={
                "type": "text",
                "file": {
                    "filePath": str(path),
                    "content": numbered,
                    "numLines": len(sliced),
                    "startLine": offset,
                    "totalLines": len(lines),
                },
            },
        )

    def _read_image(self, path: Path, context: ToolContext) -> ToolResult:
        mime, _ = mimetypes.guess_type(str(path))
        if not mime or not mime.startswith("image/"):
            mime = "image/png"
        data = path.read_bytes()
        if len(data) > 5 * 1024 * 1024:
            return ToolResult(
                name="Read",
                output={"error": f"image too large to inline: {path} ({len(data)} bytes)"},
                is_error=True,
            )
        encoded = base64.b64encode(data).decode("ascii")
        context.mark_file_read(path)
        return ToolResult(
            name="Read",
            output={
                "type": "image",
                "file": {
                    "base64": encoded,
                    "type": mime,
                    "originalSize": len(data),
                    "filePath": str(path),
                },
            },
        )


class WriteTool:
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="Write",
            description="Write a file to the local filesystem.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["file_path", "content"],
            },
            is_destructive=True,
            max_result_size_chars=100_000,
            strict=True,
        )

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        file_path = tool_input["file_path"]
        content = tool_input["content"]
        if not isinstance(file_path, str):
            raise ValueError("file_path must be a string")
        if not isinstance(content, str):
            raise ValueError("content must be a string")

        path = context.ensure_allowed_path(file_path)

        original_file: str | None = None
        if path.exists():
            if not context.was_file_read_and_unchanged(path):
                raise ValueError("refusing to overwrite: file must be read first and unchanged since last read")
            original_file = path.read_text(encoding="utf-8", errors="replace")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        context.mark_file_read(path)
        before_lines = (original_file or "").splitlines(keepends=True)
        after_lines = content.splitlines(keepends=True)
        diff_lines = list(
            difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=str(path),
                tofile=str(path),
                n=3,
                lineterm="",
            )
        )
        return ToolResult(
            name="Write",
            output={
                "type": "update" if original_file is not None else "create",
                "filePath": str(path),
                "content": content,
                "diff": "".join(diff_lines),
                "originalFile": original_file,
            },
        )


class EditTool:
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="Edit",
            description="Performs exact strings replacements in files.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "file_path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                    "replace_all": {"type": "boolean"},
                },
                "required": ["file_path", "old_string", "new_string"],
            },
            is_destructive=True,
            max_result_size_chars=100_000,
            strict=True,
        )

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        file_path = tool_input["file_path"]
        old = tool_input["old_string"]
        new = tool_input["new_string"]
        replace_all = bool(tool_input.get("replace_all", False))

        if not isinstance(file_path, str):
            raise ValueError("file_path must be a string")
        if not isinstance(old, str) or not isinstance(new, str):
            raise ValueError("old_string/new_string must be strings")

        path = context.ensure_allowed_path(file_path)

        if not path.exists():
            raise ValueError(f"file does not exist: {path}")
        if not context.was_file_read_and_unchanged(path):
            raise ValueError("refusing to edit: file must be read first and unchanged since last read")

        original_file = path.read_text(encoding="utf-8", errors="replace")
        count = original_file.count(old)
        if count == 0:
            raise ValueError("old_string not found in file")
        if count > 1 and not replace_all:
            raise ValueError("old_string is not unique; provide a larger old_string or set replace_all=true")

        if replace_all:
            updated = original_file.replace(old, new)
        else:
            updated = original_file.replace(old, new, 1)

        path.write_text(updated, encoding="utf-8")
        context.mark_file_read(path)
        before_lines = original_file.splitlines(keepends=True)
        after_lines = updated.splitlines(keepends=True)
        diff_lines = list(
            difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=str(path),
                tofile=str(path),
                n=3,
                lineterm="",
            )
        )
        return ToolResult(
            name="Edit",
            output={
                "filePath": str(path),
                "oldString": old,
                "newString": new,
                "originalFile": original_file,
                "diff": "".join(diff_lines),
                "userModified": False,
                "replaceAll": bool(replace_all),
            },
        )


class BashTool:
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="Bash",
            description="Execute a shell command.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "command": {"type": "string"},
                    "cwd": {"type": "string"},
                    "timeout_s": {"type": "integer"},
                },
                "required": ["command"],
            },
            is_destructive=True,
            max_result_size_chars=50_000,
        )

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        command = tool_input["command"]
        if not isinstance(command, str) or not command.strip():
            raise ValueError("command must be a non-empty string")
        if "\x00" in command:
            raise ValueError("command contains NUL byte")

        for pat in _DANGEROUS_PATTERNS:
            if pat.search(command):
                raise PermissionError("refusing to run potentially dangerous command")

        explicit_cwd = tool_input.get("cwd")
        if explicit_cwd is not None:
            if not isinstance(explicit_cwd, str) or not explicit_cwd.startswith("/"):
                raise ValueError("cwd must be an absolute path when provided")
            cwd = context.ensure_allowed_path(explicit_cwd)
        else:
            cwd = context.cwd or context.workspace_root

        cd_target = self._try_extract_cd(command)
        if cd_target is not None and command.strip().startswith("cd ") and len(command.strip().splitlines()) == 1:
            next_dir = (cwd / cd_target).expanduser().resolve() if not cd_target.is_absolute() else cd_target.expanduser().resolve()
            next_dir = context.ensure_allowed_path(next_dir)
            if not next_dir.exists() or not next_dir.is_dir():
                return ToolResult(name="Bash", output={"error": f"directory does not exist: {next_dir}"}, is_error=True)
            context.cwd = next_dir
            return ToolResult(name="Bash", output={"cwd": str(context.cwd), "stdout": "", "stderr": ""})

        timeout_s = tool_input.get("timeout_s", 60)
        if not isinstance(timeout_s, int) or timeout_s < 1 or timeout_s > 600:
            raise ValueError("timeout_s must be an integer between 1 and 600")

        completed = subprocess.run(
            ["bash", "-lc", command],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )

        stdout = _truncate(completed.stdout or "")
        stderr = _truncate(completed.stderr or "")
        output: dict[str, Any] = {
            "cwd": str(cwd),
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
        return ToolResult(name="Bash", output=output, is_error=completed.returncode != 0)

    def _try_extract_cd(self, command: str) -> Path | None:
        stripped = command.strip()
        if not stripped.startswith("cd "):
            return None
        try:
            parts = shlex.split(stripped, posix=True)
        except ValueError:
            return None
        if len(parts) >= 2 and parts[0] == "cd":
            return Path(parts[1])
        return None


class GrepTool:
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="Grep",
            description="A powerful search tool built on regex search.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "glob": {"type": "string"},
                    "output_mode": {
                        "type": "string",
                        "enum": ["content", "files_with_matches", "count"],
                    },
                    "-B": {"type": "integer"},
                    "-A": {"type": "integer"},
                    "-C": {"type": "integer"},
                    "context": {"type": "integer"},
                    "-n": {"type": "boolean"},
                    "-i": {"type": "boolean"},
                    "type": {"type": "string"},
                    "head_limit": {"type": "integer"},
                    "offset": {"type": "integer"},
                    "multiline": {"type": "boolean"},
                },
                "required": ["pattern"],
            },
            is_read_only=True,
            strict=True,
            max_result_size_chars=20_000,
        )

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        pattern = tool_input["pattern"]
        if not isinstance(pattern, str) or pattern == "":
            raise ValueError("pattern must be a non-empty string")

        base = tool_input.get("path")
        glob_pattern = tool_input.get("glob")
        type_name = tool_input.get("type")
        output_mode = tool_input.get("output_mode", "files_with_matches")
        if output_mode not in {"content", "files_with_matches", "count"}:
            raise ValueError("invalid output_mode")

        head_limit = tool_input.get("head_limit")
        offset = tool_input.get("offset", 0)
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be >= 0")

        flags = 0
        if tool_input.get("-i", False):
            flags |= re.IGNORECASE
        if tool_input.get("multiline", False):
            flags |= re.MULTILINE

        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            raise ValueError(f"invalid regex: {e}") from e

        base_dir = context.cwd if base is None else context.ensure_allowed_path(base)
        if not base_dir.exists():
            raise ValueError(f"path does not exist: {base_dir}")

        matches = []
        for file_path in _iter_files(base_dir):
            if glob_pattern and not _matches_glob(file_path, glob_pattern):
                continue
            if type_name and not _matches_type(file_path, type_name):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            lines = content.splitlines()
            file_matches = []
            for i, line in enumerate(lines):
                if compiled.search(line):
                    file_matches.append((i + 1, line))

            if file_matches:
                if output_mode == "files_with_matches":
                    matches.append({"file": str(file_path), "count": len(file_matches)})
                elif output_mode == "count":
                    matches.append({"file": str(file_path), "count": len(file_matches)})
                elif output_mode == "content":
                    for line_num, line_text in file_matches:
                        matches.append({
                            "file": str(file_path),
                            "line": line_num,
                            "content": line_text,
                        })

        if head_limit is not None:
            matches = matches[offset:offset + head_limit]
        elif offset > 0:
            matches = matches[offset:]

        return ToolResult(
            name="Grep",
            output={"matches": matches, "total": len(matches), "output_mode": output_mode},
        )


def _matches_glob(path: Path, pattern: str) -> bool:
    return fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(str(path), pattern)


def _matches_type(path: Path, type_name: str) -> bool:
    ext = path.suffix.lower().lstrip(".")
    if not ext:
        return False
    return ext == type_name.lower()


class GlobTool:
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="Glob",
            description="Fast file pattern matching tool that works with any codebase size.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["pattern"],
            },
            is_read_only=True,
            max_result_size_chars=100_000,
        )

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        pattern = tool_input["pattern"]
        base = tool_input.get("path")
        limit = tool_input.get("limit", 100)
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("pattern must be a non-empty string")
        if base is not None and (not isinstance(base, str) or not base):
            raise ValueError("path must be a non-empty string when provided")
        if not isinstance(limit, int) or limit < 1 or limit > 10_000:
            raise ValueError("limit must be an integer between 1 and 10000")

        base_dir = context.cwd if base is None else context.ensure_allowed_path(base)
        if not base_dir.exists():
            raise ValueError(f"path does not exist: {base_dir}")
        if not base_dir.is_dir():
            raise ValueError(f"path is not a directory: {base_dir}")

        full_pattern = str(base_dir / pattern)
        matches = [Path(p) for p in globlib.glob(full_pattern, recursive=True)]
        files = [p for p in matches if p.is_file()]

        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        truncated = len(files) > limit
        files = files[:limit]
        return ToolResult(
            name="Glob",
            output={
                "filenames": [str(p) for p in files],
                "numFiles": len(files),
                "truncated": truncated,
            },
        )


def build_default_tools() -> list[Tool]:
    return [
        ReadTool(),
        WriteTool(),
        EditTool(),
        BashTool(),
        GrepTool(),
        GlobTool(),
    ]
