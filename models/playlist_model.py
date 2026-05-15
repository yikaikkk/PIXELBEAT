"""Playlist model for storing and navigating tracks."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QObject, Signal

from models.track import Track


class PlaylistModel(QObject):
    """
    A lightweight playlist model (Model in MVC).

    This class intentionally has no UI logic and no audio backend coupling.
    It only stores track data and emits events for observers.
    """

    playlist_changed = Signal()
    current_track_changed = Signal(object)

    SUPPORTED_SUFFIXES = {".mp3", ".wav", ".ogg"}

    def __init__(self) -> None:
        super().__init__()
        self._tracks: list[Track] = []
        self._current_index: int = -1

    @property
    def tracks(self) -> list[Track]:
        """Return all tracks in insertion order."""
        return self._tracks

    @property
    def current_track(self) -> Track | None:
        """Return currently selected track, or None when playlist is empty."""
        if 0 <= self._current_index < len(self._tracks):
            return self._tracks[self._current_index]
        return None

    def add_files(self, file_paths: Iterable[str], set_current: bool = True) -> int:
        """
        Add local music files to playlist.

        Args:
            file_paths: Paths to audio files.
            set_current: If True and playlist was empty, set first added track as current.

        Returns the count of files accepted.
        """
        added = 0
        for file_path in file_paths:
            path = Path(file_path)
            if path.suffix.lower() in self.SUPPORTED_SUFFIXES and path.exists():
                self._tracks.append(Track(path=path))
                added += 1

        if added > 0:
            if set_current and self._current_index < 0:
                self._current_index = 0
                self.current_track_changed.emit(self.current_track)
            self.playlist_changed.emit()
        return added

    def replace_files(self, file_paths: Iterable[str]) -> int:
        """Replace current playlist with validated files."""
        self._tracks = []
        self._current_index = -1
        added = self.add_files(file_paths)
        self.playlist_changed.emit()
        return added

    def set_current_index(self, index: int) -> None:
        """Set active track index if valid, and notify observers."""
        if 0 <= index < len(self._tracks):
            self._current_index = index
            self.current_track_changed.emit(self.current_track)

    def remove_at(self, index: int) -> Track | None:
        """Remove a track by index and keep the active selection valid."""
        if not 0 <= index < len(self._tracks):
            return None

        removed = self._tracks.pop(index)
        if not self._tracks:
            self._current_index = -1
        elif index < self._current_index:
            self._current_index -= 1
        elif index <= self._current_index:
            self._current_index = min(index, len(self._tracks) - 1)

        self.playlist_changed.emit()
        self.current_track_changed.emit(self.current_track)
        return removed

    def next_track(self) -> Track | None:
        """Move to next track with wrap-around behavior."""
        if not self._tracks:
            return None
        self._current_index = (self._current_index + 1) % len(self._tracks)
        self.current_track_changed.emit(self.current_track)
        return self.current_track

    def previous_track(self) -> Track | None:
        """Move to previous track with wrap-around behavior."""
        if not self._tracks:
            return None
        self._current_index = (self._current_index - 1) % len(self._tracks)
        self.current_track_changed.emit(self.current_track)
        return self.current_track

    def to_path_list(self) -> list[str]:
        """Serialize tracks as absolute path strings."""
        return [str(track.path) for track in self._tracks]
