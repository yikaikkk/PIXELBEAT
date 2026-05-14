"""Storage helpers for app settings and playlist persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _state_path() -> Path:
    """Return a writable JSON path under project-local assets directory."""
    return Path(__file__).resolve().parent.parent / "assets" / "app_state.json"


def load_state() -> dict[str, Any]:
    """Load state JSON; return empty dict on first run or malformed file."""
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict[str, Any]) -> None:
    """Persist state JSON atomically enough for this desktop project."""
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

