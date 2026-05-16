"""Track entity for playlist and playback metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Track:
    """Represents a single local audio file."""

    path: Path

    @property
    def title(self) -> str:
        """Human-readable track title based on file name."""
        return self.path.stem

