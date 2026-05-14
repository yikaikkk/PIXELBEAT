"""CRT-like pixel block spectrum visualizer."""

from __future__ import annotations

import random

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


class SpectrumWidget(QWidget):
    """Block-based spectrum with scanline overlay and stepped animation."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._bars = [0] * 20
        self._peaks = [0] * 20
        self._frames: list[list[int]] = []
        self._frame_index = 0
        self._active = False
        self._timer = QTimer(self)
        self._timer.setInterval(90)
        self._timer.timeout.connect(self._tick)
        self.setMinimumHeight(118)

    def start(self) -> None:
        self._active = True
        self._timer.start()

    def stop(self) -> None:
        self._active = False
        self._timer.stop()
        self._bars = [0] * len(self._bars)
        self._peaks = [0] * len(self._peaks)
        self._frame_index = 0
        self._frames = []
        self.update()

    def set_frames(self, frames: list[list[int]]) -> None:
        self._frames = frames
        self._frame_index = 0

    def set_position_ms(self, position_ms: int) -> None:
        if not self._frames:
            return
        self._frame_index = min(position_ms // 100, len(self._frames) - 1)

    def _tick(self) -> None:
        if not self._active:
            return
        if self._frames:
            source = self._frames[self._frame_index]
            self._bars = source[: len(self._bars)] + [0] * max(0, len(self._bars) - len(source))
            self._frame_index = (self._frame_index + 1) % len(self._frames)
        else:
            self._bars = [random.randint(0, 10) for _ in self._bars]

        # Peak-hold with slow mechanical decay.
        for i, value in enumerate(self._bars):
            if value >= self._peaks[i]:
                self._peaks[i] = value
            elif self._peaks[i] > 0:
                self._peaks[i] -= 1
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1A1C1A"))
        painter.setRenderHint(QPainter.Antialiasing, False)

        painter.setPen(QColor("#0D0F0D"))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        painter.setPen(QColor("#2D322D"))
        for x in range(8, self.width(), 12):
            painter.drawLine(x, 2, x, self.height() - 3)

        block_w = max(5, (self.width() - 24) // (len(self._bars) * 2))
        block_h = 7
        gap_x = max(2, block_w // 2)
        gap_y = 2
        usable_steps = max(1, (self.height() - 22) // (block_h + gap_y))

        for i, value in enumerate(self._bars):
            x = 8 + i * (block_w + gap_x)
            height_steps = min(value, usable_steps)
            for y_step in range(height_steps):
                y = self.height() - 8 - (y_step + 1) * (block_h + gap_y)
                if y_step > usable_steps * 0.72:
                    color = QColor("#D8E0A0")
                elif y_step > usable_steps * 0.45:
                    color = QColor("#8BAC0F")
                else:
                    color = QColor("#6D7355")
                painter.fillRect(x + 1, y + 1, block_w, block_h, QColor("#0D0F0D"))
                painter.fillRect(x, y, block_w, block_h, color)

            peak = min(self._peaks[i], usable_steps)
            if peak > 0:
                y_peak = self.height() - 8 - peak * (block_h + gap_y)
                painter.fillRect(x, y_peak, block_w, 2, QColor("#D8E0A0"))

        # CRT scanlines.
        painter.setPen(QColor(13, 15, 13, 120))
        for y in range(0, self.height(), 4):
            painter.drawLine(0, y, self.width(), y)
        painter.setPen(QColor(139, 172, 15, 72))
        painter.drawRect(3, 3, self.width() - 7, self.height() - 7)
