"""Reusable pixel-art button component."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QPushButton

from utils.pixel_icons import build_icon


class PixelButton(QPushButton):
    """
    Hard-edged button with pixel-style pressed feedback.

    The style avoids rounded corners and uses hard shadow offsets.
    """

    ICON_MAP = {
        "play": "PLAY",
        "pause": "PAUSE",
        "stop": "STOP",
        "prev": "PREV",
        "next": "NEXT",
        "close": "CLOSE",
        "min": "MIN",
        "square": "SQUARE",
        "music": "MUSIC",
        "list": "LIST",
        "volume": "VOLUME",
        "shuffle": "SHUFFLE",
        "repeat": "REPEAT",
    }

    BASE_STYLE = """
    QPushButton {
        background-color: #1A1A2E;
        color: #FFFFFF;
        border: 4px solid #000000;
        padding: 7px 11px 9px 11px;
        min-height: 26px;
    }
    QPushButton:hover {
        color: #4ECCA3;
    }
    QPushButton:pressed {
        background-color: #16213E;
        padding-left: 13px;
        padding-top: 10px;
        padding-right: 9px;
        padding-bottom: 6px;
    }
    QPushButton:disabled {
        background-color: #16213E;
        color: #95A5A6;
    }
    QPushButton#primaryTransport {
        background-color: #E94560;
        color: #FFFFFF;
    }
    QPushButton#activeToggle {
        background-color: #4ECCA3;
        color: #1A1A2E;
    }
    QPushButton#dangerButton {
        background-color: #E94560;
        color: #FFFFFF;
    }
    """

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self._icon_kind: str | None = None
        self._icon_size = 12
        self.setStyleSheet(self.BASE_STYLE)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_icon_kind(self, icon_kind: str | None) -> None:
        self._icon_kind = self.ICON_MAP.get(icon_kind or "")
        self.update()

    def set_icon_size(self, size: int) -> None:
        self._icon_size = max(8, size)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        if not self.isDown():
            painter.fillRect(3, self.height() - 3, self.width() - 3, 3, QColor("#0D0F0D"))
            painter.fillRect(self.width() - 3, 3, 3, self.height() - 3, QColor("#0D0F0D"))
        painter.end()

        if not self._icon_kind:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        if self.objectName() == "activeToggle":
            color = QColor("#1A1A2E")
        else:
            color = QColor("#4ECCA3") if self.underMouse() else QColor("#FFFFFF")
        pix = build_icon(self._icon_kind, color=color, size=self._icon_size)
        pressed_offset = 2 if self.isDown() else 0
        if self.text().strip():
            x = 8 + pressed_offset
        else:
            x = self.width() // 2 - pix.width() // 2 + pressed_offset
        y = self.height() // 2 - pix.height() // 2
        painter.drawPixmap(x, y, pix)
