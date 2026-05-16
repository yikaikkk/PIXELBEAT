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


class DownloadBilibiliVideo:
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="DownloadBilibiliVideo",
            description="Download video or audio from Bilibili using you-get. Supports downloading full video (auto-merge audio/video), audio-only mode, and getting video info before download.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "url": {"type": "string"},
                    "mode": {
                        "type": "string",
                        "enum": ["video", "audio", "info"],
                        "description": "Download mode: 'video' for full video with auto-merge, 'audio' for audio only, 'info' to get video metadata without downloading"
                    },
                    "output_dir": {"type": "string"},
                    "filename": {"type": "string"},
                },
                "required": ["url", "mode"],
            },
            is_destructive=True,
            max_result_size_chars=50_000,
        )

    @staticmethod
    def _is_ffmpeg_available() -> bool:
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def _is_audio_only(file_path: str) -> bool:
        if not DownloadBilibiliVideo._is_ffmpeg_available():
            return False
        try:
            result = subprocess.run(
                ["ffmpeg", "-i", file_path],
                capture_output=True,
                text=True,
                stderr=subprocess.STDOUT,
                timeout=10,
            )
            has_video = "Video:" in result.stdout
            has_audio = "Audio:" in result.stdout
            return has_audio and not has_video
        except Exception:
            return False

    @staticmethod
    def _find_video_audio_files(download_dir: Path, title: str) -> tuple[str | None, str | None]:
        video_file = None
        audio_file = None
        mp4_files = []

        for file in download_dir.iterdir():
            filename_lower = file.name.lower()
            title_lower = title.lower()
            if (title_lower.replace(" ", "") in filename_lower.replace(" ", "")
                    or title_lower[:20] in filename_lower[:20]):
                if file.suffix in [".m4a", ".mp3", ".aac"]:
                    audio_file = str(file)
                elif file.suffix in [".mp4", ".flv", ".webm"]:
                    mp4_files.append((str(file), file.stat().st_size))

        if len(mp4_files) >= 2:
            if DownloadBilibiliVideo._is_ffmpeg_available():
                for file_path, _ in mp4_files:
                    if DownloadBilibiliVideo._is_audio_only(file_path):
                        audio_file = file_path
                    else:
                        video_file = file_path
            else:
                mp4_files.sort(key=lambda x: x[1])
                video_file = mp4_files[0][0]
                audio_file = mp4_files[-1][0]
        elif len(mp4_files) == 1:
            video_file = mp4_files[0][0]

        return video_file, audio_file

    @staticmethod
    def _parse_you_get_output(stdout: str) -> dict[str, Any]:
        """Parse you-get output to extract video info."""
        info = {}
        for line in stdout.split('\n'):
            line = line.strip()
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip().lower()
                value = value.strip()
                if key in ('title', 'type', 'size', 'duration', 'stream type', 'note'):
                    info[key] = value
        return info

    @staticmethod
    def _run_you_get(args: list[str], cwd: str) -> tuple[int, str, str]:
        """Run you-get command and return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                ["you-get"] + args,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=600,
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            return -1, "", "you-get not found. Install with: pip install you-get"
        except subprocess.TimeoutExpired:
            return -1, "", "Download timed out (600s limit)"

    def run(self, tool_input: dict[str, Any], context: ToolContext) -> ToolResult:
        url = tool_input.get("url", "")
        mode = tool_input.get("mode", "video")
        output_dir_str = tool_input.get("output_dir", "./downloads")
        filename = tool_input.get("filename")

        if not isinstance(url, str) or not url:
            return ToolResult(
                name="DownloadBilibiliVideo",
                output={"error": "url must be a non-empty string"},
                is_error=True,
            )
        if mode not in ("video", "audio", "info"):
            return ToolResult(
                name="DownloadBilibiliVideo",
                output={"error": f"invalid mode: {mode}. Must be 'video', 'audio', or 'info'"},
                is_error=True,
            )

        download_dir = Path(output_dir_str).expanduser().resolve()

        # --- mode: info ---
        if mode == "info":
            rc, stdout, stderr = self._run_you_get(["-i", url], str(download_dir))
            if rc != 0:
                return ToolResult(
                    name="DownloadBilibiliVideo",
                    output={"error": f"Failed to get video info: {stderr or stdout}"},
                    is_error=True,
                )
            info = self._parse_you_get_output(stdout)
            # Extract stream info lines
            stream_lines = []
            in_streams = False
            for line in stdout.split('\n'):
                s = line.strip()
                if 'streams available' in s.lower():
                    in_streams = True
                if in_streams and s.startswith('stream ID'):
                    stream_lines.append(s)
                elif in_streams and (s.startswith('[') or (s and not s[0].isspace())):
                    if s.startswith('stream') or s.startswith('[DEFAULT]') or s.startswith('#'):
                        stream_lines.append(s)
            return ToolResult(
                name="DownloadBilibiliVideo",
                output={
                    "mode": "info",
                    "url": url,
                    "info": info,
                    "streams": stream_lines,
                },
            )

        # --- mode: video / audio ---
        ffmpeg_available = self._is_ffmpeg_available()
        cmd = ["-o", str(download_dir), url]
        if filename:
            cmd.extend(["-O", filename])

        rc, stdout, stderr = self._run_you_get(cmd, str(download_dir))
        if rc != 0:
            return ToolResult(
                name="DownloadBilibiliVideo",
                output={"error": f"Download failed: {stderr or stdout}", "stdout": stdout},
                is_error=True,
            )

        files = sorted(
            [(f.name, f.stat().st_size) for f in download_dir.iterdir()],
            key=lambda x: x[1],
            reverse=True,
        )

        # Determine what was downloaded and cleaned up temp files
        merged_path = None
        kept_file = None
        cleanup_title = filename or ""

        if mode == "video":
            # Try to find merged video; fall back to best single file
            if ffmpeg_available:
                # Look for *_merged.mp4 files
                for f in download_dir.iterdir():
                    if f.name.endswith("_merged.mp4"):
                        merged_path = str(f)
                        break
            # Fallback: pick largest .mp4 that isn't too small (likely has audio)
            if not merged_path:
                for fname, size in files:
                    if fname.endswith(".mp4") and size > 100_000:
                        merged_path = str(download_dir / fname)
                        break

            if not merged_path and files:
                merged_path = str(download_dir / files[0][0])
            kept_file = merged_path

        elif mode == "audio":
            # Find audio file or extract from video
            if ffmpeg_available:
                video_file, audio_file = self._find_video_audio_files(
                    download_dir, cleanup_title or (files[0][0].replace(".mp4", "").replace(".flv", "").replace(".webm", "") if files else "")
                )
                if audio_file:
                    kept_file = audio_file
                elif video_file:
                    # Extract audio from video
                    audio_out = download_dir / f"{cleanup_title or 'audio'}.mp3"
                    ex = subprocess.run(
                        ["ffmpeg", "-i", video_file, "-q:a", "0", "-map", "a", "-y", str(audio_out)],
                        capture_output=True, text=True, timeout=120,
                    )
                    if ex.returncode == 0 and audio_out.exists():
                        kept_file = str(audio_out)

            # If we have a kept file, clean everything else matching the title
            if kept_file:
                for f in list(download_dir.iterdir()):
                    if str(f) != kept_file:
                        try:
                            f.unlink()
                        except Exception:
                            pass
            elif files:
                kept_file = str(download_dir / files[0][0])

        final_path = merged_path or kept_file or (str(download_dir / files[0][0]) if files else str(download_dir))

        return ToolResult(
            name="DownloadBilibiliVideo",
            output={
                "mode": mode,
                "url": url,
                "success": True,
                "final_path": final_path,
                "download_dir": str(download_dir),
                "all_files": [{"name": n, "size_bytes": s} for n, s in files],
                "ffmpeg_available": ffmpeg_available,
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
        DownloadBilibiliVideo(),
    ]
