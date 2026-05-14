"""FFT spectrum data preparation for local audio files."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pygame


class SpectrumAnalyzer:
    """
    Precompute normalized spectrum frames from audio files.

    Uses pygame's decoder path so `wav/mp3/ogg` can share one analysis flow
    when SDL_mixer supports the format on the host.
    """

    def __init__(self, bars: int = 24) -> None:
        self._bars = bars
        self._mixer_ready = False

    def _ensure_mixer(self) -> None:
        if self._mixer_ready:
            return
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self._mixer_ready = True

    def build_frames(self, path: Path, frame_ms: int = 90) -> list[list[int]]:
        """Return bar snapshots where each value is in [0, 12]."""
        try:
            self._ensure_mixer()
            sound = pygame.mixer.Sound(str(path))
            samples = pygame.sndarray.array(sound).astype(np.float32)
        except pygame.error:
            return []

        if samples.ndim == 2:
            samples = samples.mean(axis=1)

        sample_rate = 44100
        chunk_size = max(512, int(sample_rate * (frame_ms / 1000.0)))
        frames: list[list[int]] = []

        for start in range(0, len(samples), chunk_size):
            chunk = samples[start : start + chunk_size]
            if len(chunk) < 256:
                break
            window = np.hanning(len(chunk))
            spectrum = np.abs(np.fft.rfft(chunk * window))
            if spectrum.size <= 1:
                continue
            bins = np.array_split(spectrum[1:], self._bars)
            bars = [int(np.clip(np.log1p(float(b.mean())) / 2.2, 0, 12)) for b in bins]
            frames.append(bars)

        return frames

