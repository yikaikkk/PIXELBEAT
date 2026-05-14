"""Audio playback engine powered by pygame.mixer."""

from __future__ import annotations

from pathlib import Path

import pygame
from PySide6.QtCore import QObject, QTimer, Signal


class AudioEngine(QObject):
    """
    Playback backend abstraction (Core service in MVC).

    This class isolates pygame usage from UI and models.
    It can be replaced later without affecting upper layers.
    """

    state_changed = Signal(str)
    playback_finished = Signal()
    position_changed = Signal(int)
    duration_changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._initialized = False
        self._paused = False
        self._playing = False
        self._current_path: Path | None = None
        self._duration_ms = 0
        self._position_base_ms = 0
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(180)
        self._poll_timer.timeout.connect(self._poll_state)
        self._init_mixer()

    def _init_mixer(self) -> None:
        """Initialize pygame mixer once."""
        if self._initialized:
            return
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self._initialized = True

    def load(self, path: Path) -> None:
        """Load an audio file into the player."""
        if not path.exists():
            raise FileNotFoundError(path)
        pygame.mixer.music.load(str(path))
        self._duration_ms = int(pygame.mixer.Sound(str(path)).get_length() * 1000)
        self._current_path = path
        self._position_base_ms = 0
        self.duration_changed.emit(self._duration_ms)
        self.state_changed.emit("loaded")

    def play(self) -> None:
        """Start or resume playback."""
        if self._paused:
            pygame.mixer.music.unpause()
            self._paused = False
            self._playing = True
        else:
            pygame.mixer.music.play()
            self._position_base_ms = 0
            self._playing = True
        self._poll_timer.start()
        self.state_changed.emit("playing")

    def pause(self) -> None:
        """Pause playback."""
        pygame.mixer.music.pause()
        self._paused = True
        self._playing = False
        self.state_changed.emit("paused")

    def stop(self) -> None:
        """Stop playback and reset state."""
        pygame.mixer.music.stop()
        self._paused = False
        self._playing = False
        self._poll_timer.stop()
        self._position_base_ms = 0
        self.state_changed.emit("stopped")

    def set_volume(self, value: float) -> None:
        """Set output volume within [0.0, 1.0]."""
        safe_value = max(0.0, min(1.0, value))
        pygame.mixer.music.set_volume(safe_value)

    def seek_ms(self, position_ms: int) -> None:
        """
        Seek by milliseconds using pygame's second-based API.

        For some codecs pygame may seek with coarse precision.
        """
        second = max(0.0, position_ms / 1000.0)
        pygame.mixer.music.play(start=second)
        self._position_base_ms = int(position_ms)
        if self._paused:
            pygame.mixer.music.pause()

    def is_paused(self) -> bool:
        """Return paused state for UI/controller shortcuts."""
        return self._paused

    def is_playing(self) -> bool:
        """Return best-effort playing state."""
        return self._playing and pygame.mixer.music.get_busy()

    def _poll_state(self) -> None:
        """
        Emit position and end-of-track events.

        pygame reports elapsed milliseconds via get_pos().
        """
        position = pygame.mixer.music.get_pos()
        if position >= 0:
            self.position_changed.emit(self._position_base_ms + position)
        if not pygame.mixer.music.get_busy() and not self._paused and self._current_path:
            self._playing = False
            self._poll_timer.stop()
            self.playback_finished.emit()
            self.state_changed.emit("finished")
