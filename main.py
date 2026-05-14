"""
Application entry point for PixelBeat.

This module wires together the MVC pieces:
- Model: PlaylistModel
- Core service: AudioEngine
- View/Controller host: MainWindow
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from core.audio_engine import AudioEngine
from models.playlist_model import PlaylistModel
from ui.main_window import MainWindow


def _load_pixel_font() -> None:
    """
    Try loading a bundled pixel font if available.

    The app still works without it. In that case, the theme's fallback
    monospaced font stack is used.
    """
    font_path = Path(__file__).parent / "assets" / "fonts" / "PressStart2P-Regular.ttf"
    if font_path.exists():
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id >= 0:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                QApplication.setFont(QFont(families[0], 9))


def main() -> int:
    """Bootstrap and run the desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("PixelBeat")
    _load_pixel_font()

    playlist_model = PlaylistModel()
    audio_engine = AudioEngine()
    window = MainWindow(playlist_model=playlist_model, audio_engine=audio_engine)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
