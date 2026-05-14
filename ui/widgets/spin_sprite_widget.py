"""Pixel sprite animation widget for vinyl/cassette visual styles."""

from __future__ import annotations

import math

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QLabel


class SpinSpriteWidget(QLabel):
    """Low-FPS stepped sprite animation with hard-edged pixel rendering."""

    MODES = ("VINYL", "CASSETTE")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(320, 300)
        self.setAlignment(Qt.AlignCenter)
        self._mode = "VINYL"
        self._frames: list[QPixmap] = []
        self._frame_pos = 0.0
        self._frame_speed = 1.0
        self._target_speed = 0.0
        self._led_on = False
        self._timer = QTimer(self)
        self._timer.setInterval(110)
        self._timer.timeout.connect(self._tick)
        self._rebuild_frames()

    def set_mode(self, mode: str) -> None:
        if mode not in self.MODES:
            return
        self._mode = mode
        self._rebuild_frames()

    def start(self) -> None:
        self._target_speed = 1.0
        self._led_on = True
        self._rebuild_frames()
        self._timer.start()

    def stop(self) -> None:
        # Decelerate instead of hard stop for mechanical feel.
        self._target_speed = 0.0
        self._led_on = False
        self._rebuild_frames()

    def _tick(self) -> None:
        if not self._frames:
            return
        if self._frame_speed < self._target_speed:
            self._frame_speed = min(self._target_speed, self._frame_speed + 0.2)
        elif self._frame_speed > self._target_speed:
            self._frame_speed = max(self._target_speed, self._frame_speed - 0.08)

        if self._frame_speed <= 0.01 and self._target_speed == 0.0:
            self._frame_speed = 0.0
            self._frame_pos = 0.0
            self._timer.stop()
            self.setPixmap(self._frames[0])
            return

        self._frame_pos = (self._frame_pos + self._frame_speed) % len(self._frames)
        self.setPixmap(self._frames[int(self._frame_pos)])

    def _rebuild_frames(self) -> None:
        if self._mode == "CASSETTE":
            self._frames = self._build_cassette_frames()
        else:
            self._frames = self._build_vinyl_frames()
        self._frame_pos = 0.0
        if self._frames:
            self.setPixmap(self._frames[0])

    def _build_vinyl_frames(self) -> list[QPixmap]:
        frames: list[QPixmap] = []
        for step in range(12):
            p = QPixmap(320, 300)
            p.fill(Qt.transparent)
            painter = QPainter(p)
            painter.setRenderHint(QPainter.Antialiasing, False)

            painter.fillRect(28, 28, 264, 226, QColor("#0D0F0D"))
            painter.fillRect(20, 20, 264, 226, QColor("#2D322D"))
            painter.setPen(QColor("#0D0F0D"))
            painter.drawRect(20, 20, 264, 226)
            painter.fillRect(34, 34, 160, 160, QColor("#1A1C1A"))

            painter.setBrush(QColor("#081820"))
            painter.setPen(QColor("#8BAC0F"))
            painter.drawEllipse(42, 38, 144, 144)
            painter.setPen(QColor("#3C443C"))
            painter.drawEllipse(60, 56, 108, 108)
            painter.drawEllipse(78, 74, 72, 72)
            painter.setBrush(QColor("#306230"))
            painter.setPen(QColor("#8BAC0F"))
            painter.drawEllipse(86, 82, 56, 56)
            painter.setBrush(QColor("#D8E0A0"))
            painter.drawEllipse(106, 102, 16, 16)

            led_color = QColor("#8BAC0F" if self._led_on and step % 2 == 0 else "#182018")
            painter.fillRect(246, 42, 12, 12, led_color)
            painter.setPen(QColor("#0D0F0D"))
            painter.drawRect(245, 41, 13, 13)

            painter.fillRect(224, 76, 14, 86, QColor("#0D0F0D"))
            painter.fillRect(218, 70, 14, 86, QColor("#D8E0A0"))
            painter.fillRect(204, 150, 48, 10, QColor("#D8E0A0"))
            painter.fillRect(198, 154, 18, 8, QColor("#8BAC0F"))
            painter.setPen(QColor("#0D0F0D"))
            painter.drawRect(217, 69, 14, 86)
            painter.drawRect(203, 149, 48, 10)

            painter.fillRect(48, 210, 62, 10, QColor("#1A1C1A"))
            painter.fillRect(120, 210, 84, 10, QColor("#1A1C1A"))
            painter.fillRect(218, 210, 42, 10, QColor("#1A1C1A"))
            painter.setPen(QColor("#8BAC0F"))
            painter.drawText(40, 235, "VINYL DRIVE")

            # Tick marks that visually rotate in stepped frames.
            for i in range(8):
                angle = (step * 30 + i * 45) % 360
                x = 114 + int(58 * _cos_deg(angle))
                y = 110 + int(58 * _sin_deg(angle))
                painter.fillRect(x - 2, y - 2, 4, 4, QColor("#9bbc0f"))

            for x in range(26, 282, 12):
                painter.fillRect(x, 24, 4, 4, QColor("#3C443C"))
                painter.fillRect(x, 238, 4, 4, QColor("#3C443C"))
            painter.end()
            frames.append(p)
        return frames

    def _build_cassette_frames(self) -> list[QPixmap]:
        frames: list[QPixmap] = []
        for step in range(12):
            p = QPixmap(320, 300)
            p.fill(Qt.transparent)
            painter = QPainter(p)
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.fillRect(28, 42, 264, 178, QColor("#0D0F0D"))
            painter.fillRect(20, 34, 264, 178, QColor("#2D322D"))
            painter.setPen(QColor("#0D0F0D"))
            painter.drawRect(20, 34, 264, 178)

            painter.fillRect(40, 58, 224, 52, QColor("#1A1C1A"))
            painter.setPen(QColor("#8BAC0F"))
            painter.drawRect(40, 58, 224, 52)
            painter.fillRect(54, 72, 196, 22, QColor("#306230"))
            painter.setPen(QColor("#D8E0A0"))
            painter.drawText(60, 90, "PIXEL TAPE 90")

            led_color = QColor("#8BAC0F" if self._led_on and step % 2 == 0 else "#182018")
            painter.fillRect(246, 124, 12, 12, led_color)
            painter.setPen(QColor("#0D0F0D"))
            painter.drawRect(245, 123, 13, 13)

            # Two reels with phase-shifted spokes.
            self._draw_reel(painter, 96, 146, step * 30)
            self._draw_reel(painter, 206, 146, (step * 30 + 45) % 360)
            painter.fillRect(96, 144, 110, 5, QColor("#D8E0A0"))
            painter.fillRect(74, 184, 154, 10, QColor("#1A1C1A"))
            painter.fillRect(92, 186, 20, 6, QColor("#8BAC0F"))
            painter.fillRect(190, 186, 20, 6, QColor("#8BAC0F"))

            for x in range(32, 272, 12):
                painter.fillRect(x, 38, 4, 4, QColor("#3C443C"))
                painter.fillRect(x, 202, 4, 4, QColor("#3C443C"))
            painter.setPen(QColor("#8BAC0F"))
            painter.drawText(40, 240, "CASSETTE DECK")
            painter.end()
            frames.append(p)
        return frames

    def _draw_reel(self, painter: QPainter, cx: int, cy: int, phase: int) -> None:
        painter.setBrush(QColor("#081820"))
        painter.setPen(QColor("#8BAC0F"))
        painter.drawEllipse(cx - 32, cy - 32, 64, 64)
        painter.setBrush(QColor("#1f4e1f"))
        painter.drawEllipse(cx - 22, cy - 22, 44, 44)
        painter.setBrush(QColor("#9bbc0f"))
        painter.drawEllipse(cx - 5, cy - 5, 10, 10)
        for i in range(4):
            angle = (phase + i * 90) % 360
            x = cx + int(14 * _cos_deg(angle))
            y = cy + int(14 * _sin_deg(angle))
            painter.fillRect(x - 2, y - 2, 4, 4, QColor("#9bbc0f"))


def _cos_deg(deg: int) -> float:
    rad = deg * 3.1415926 / 180.0
    return math.cos(rad)


def _sin_deg(deg: int) -> float:
    rad = deg * 3.1415926 / 180.0
    return math.sin(rad)
