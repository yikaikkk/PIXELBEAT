"""Pixel icon factory for retro control glyphs."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap, QPolygon


def build_icon(icon_kind: str, color: QColor, size: int = 12) -> QPixmap:
    """Build a tiny pixel icon pixmap for controls."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, False)
    p.setBrush(color)
    p.setPen(Qt.NoPen)

    if icon_kind == "PLAY":
        p.drawPolygon(QPolygon([QPoint(2, 1), QPoint(2, size - 1), QPoint(size - 2, size // 2)]))
    elif icon_kind == "PAUSE":
        p.fillRect(2, 1, 3, size - 2, color)
        p.fillRect(size - 5, 1, 3, size - 2, color)
    elif icon_kind == "STOP":
        p.fillRect(2, 2, size - 4, size - 4, color)
    elif icon_kind == "PREV":
        p.fillRect(1, 1, 2, size - 2, color)
        p.drawPolygon(QPolygon([QPoint(size - 1, 1), QPoint(size - 1, size - 1), QPoint(3, size // 2)]))
    elif icon_kind == "NEXT":
        p.fillRect(size - 3, 1, 2, size - 2, color)
        p.drawPolygon(QPolygon([QPoint(1, 1), QPoint(1, size - 1), QPoint(size - 3, size // 2)]))
    elif icon_kind == "CLOSE":
        for i in range(4):
            p.fillRect(2 + i * 2, 2 + i * 2, 2, 2, color)
            p.fillRect(size - 4 - i * 2, 2 + i * 2, 2, 2, color)
    elif icon_kind == "MIN":
        p.fillRect(1, size - 3, size - 2, 2, color)
    elif icon_kind == "SQUARE":
        p.fillRect(2, 2, size - 4, 2, color)
        p.fillRect(2, size - 4, size - 4, 2, color)
        p.fillRect(2, 2, 2, size - 4, color)
        p.fillRect(size - 4, 2, 2, size - 4, color)
    elif icon_kind == "MUSIC":
        p.fillRect(size // 2, 1, 2, size - 5, color)
        p.fillRect(size // 2, 1, size // 3, 2, color)
        p.fillRect(size // 2 + size // 3 - 2, 3, 2, 4, color)
        p.drawEllipse(2, size - 5, 5, 4)
    elif icon_kind == "LIST":
        for y in (2, size // 2 - 1, size - 4):
            p.fillRect(2, y, 2, 2, color)
            p.fillRect(6, y, size - 8, 2, color)
    elif icon_kind == "VOLUME":
        p.fillRect(1, size // 2 - 3, 3, 6, color)
        p.drawPolygon(QPolygon([QPoint(4, size // 2 - 4), QPoint(8, size // 2 - 7), QPoint(8, size // 2 + 7), QPoint(4, size // 2 + 4)]))
        p.fillRect(size - 5, size // 2 - 5, 2, 10, color)
        p.fillRect(size - 2, size // 2 - 3, 2, 6, color)
    elif icon_kind == "SHUFFLE":
        p.fillRect(1, 3, 4, 2, color)
        p.fillRect(5, 5, 3, 2, color)
        p.fillRect(8, 7, 5, 2, color)
        p.fillRect(1, size - 5, 4, 2, color)
        p.fillRect(5, size - 7, 3, 2, color)
        p.fillRect(8, size - 9, 5, 2, color)
        p.fillRect(size - 4, 5, 3, 2, color)
        p.fillRect(size - 4, size - 7, 3, 2, color)
    elif icon_kind == "REPEAT":
        p.fillRect(3, 2, size - 6, 2, color)
        p.fillRect(3, size - 4, size - 6, 2, color)
        p.fillRect(2, 3, 2, 4, color)
        p.fillRect(size - 4, size - 7, 2, 4, color)
        p.drawPolygon(QPolygon([QPoint(size - 4, 0), QPoint(size - 1, 3), QPoint(size - 4, 6)]))
        p.drawPolygon(QPolygon([QPoint(3, size - 1), QPoint(0, size - 4), QPoint(3, size - 7)]))
    elif icon_kind == "MENU":
        for y in (2, size // 2 - 1, size - 4):
            p.fillRect(2, y, size - 4, 2, color)

    p.end()
    return pix
