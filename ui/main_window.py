"""Main window rebuilt to match the Pixeltune reference UI."""

from __future__ import annotations

from pathlib import Path
import random
import re

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QSizeGrip,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.audio_engine import AudioEngine
from models.playlist_model import PlaylistModel
from ui.themes import PIXEL_RETRO
from ui.widgets.pixel_button import PixelButton
from utils.pixel_icons import build_icon
from utils.spectrum_analyzer import SpectrumAnalyzer
from utils.storage import load_state, save_state


class PixelTuneDisplay(QWidget):
    """Square CRT album-art area with block visualizer overlay."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("displayCanvas")
        self.setFixedSize(360, 360)
        self._title = "NO TRACK LOADED"
        self._artist = "LOCAL LIBRARY"
        self._lyrics = ["INSERT AUDIO FILES", "LOAD A TRACK", "PRESS PLAY", "PIXEL SIGNAL READY"]
        self._timed_lyrics: list[tuple[int, str]] = []
        self._lyric_index = 0
        self._show_lyrics = False
        self._bars = [10] * 12
        self._frames: list[list[int]] = []
        self._frame_index = 0
        self._active = False
        self._timer = QTimer(self)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._lyric_timer = QTimer(self)
        self._lyric_timer.setInterval(3000)
        self._lyric_timer.timeout.connect(self._advance_lyric)
        self._lyric_timer.start()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(360, 360)

    def set_track(self, title: str, artist: str = "LOCAL FILE") -> None:
        self._title = title.upper() if title else "NO TRACK LOADED"
        self._artist = artist.upper()
        if title:
            self._lyrics = [
                "NOW PLAYING",
                self._title,
                "LOCAL AUDIO STREAM",
                "CRT SIGNAL LOCKED",
                "PIXEL BEAT ONLINE",
                "THANK YOU FOR LISTENING",
            ]
        else:
            self._lyrics = ["INSERT AUDIO FILES", "LOAD A TRACK", "PRESS PLAY", "PIXEL SIGNAL READY"]
        self._timed_lyrics = []
        self._lyric_index = 0
        self.update()

    def set_lyrics(self, lines: list[str], timed_lines: list[tuple[int, str]] | None = None) -> None:
        self._timed_lyrics = sorted(timed_lines or [], key=lambda item: item[0])
        if self._timed_lyrics:
            self._lyrics = [line for _time_ms, line in self._timed_lyrics]
        else:
            self._lyrics = [line.upper() for line in lines if line.strip()]
        if not self._lyrics:
            self._lyrics = ["NO LYRICS FOUND"]
        self._lyric_index = 0
        self.update()

    def set_show_lyrics(self, enabled: bool) -> None:
        self._show_lyrics = enabled
        self.update()

    def set_frames(self, frames: list[list[int]]) -> None:
        self._frames = frames
        self._frame_index = 0

    def set_position_ms(self, position_ms: int) -> None:
        if self._frames:
            self._frame_index = min(position_ms // 100, len(self._frames) - 1)
        if self._timed_lyrics:
            index = 0
            for candidate, (time_ms, _line) in enumerate(self._timed_lyrics):
                if position_ms >= time_ms:
                    index = candidate
                else:
                    break
            if index != self._lyric_index:
                self._lyric_index = index
                self.update()

    def start(self) -> None:
        self._active = True

    def pause(self) -> None:
        self._active = False

    def stop(self) -> None:
        self._active = False
        self._frames = []
        self._bars = [10] * len(self._bars)
        self.update()

    def _tick(self) -> None:
        if self._active and self._frames:
            source = self._frames[self._frame_index]
            self._bars = [min(100, max(8, value * 10)) for value in source[:12]]
            self._frame_index = (self._frame_index + 1) % len(self._frames)
        elif self._active:
            self._bars = [random.randint(12, 96) for _ in self._bars]
        else:
            self._bars = [10] * len(self._bars)
        self.update()

    def _advance_lyric(self) -> None:
        if self._active and self._lyrics and not self._timed_lyrics:
            self._lyric_index = (self._lyric_index + 1) % len(self._lyrics)
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), QColor("#16213E"))

        screen = self.rect().adjusted(22, 22, -22, -22)
        painter.fillRect(screen.adjusted(6, 6, 6, 6), QColor(0, 0, 0, 130))
        painter.fillRect(screen, QColor("#0F3460"))
        painter.setPen(QColor("#000000"))
        painter.drawRect(screen)

        glow = QColor("#E94560") if self._active else QColor("#4ECCA3")
        painter.fillRect(screen.adjusted(20, 20, -20, -20), QColor(glow.red(), glow.green(), glow.blue(), 28))

        if self._show_lyrics:
            lyric_rect = screen.adjusted(24, 42, -24, -42)
            visible = self._visible_lyric_rows()
            line_h = max(28, lyric_rect.height() // max(1, len(visible)))
            start_y = lyric_rect.top() + max(0, (lyric_rect.height() - line_h * len(visible)) // 2)
            for row_index, (line_index, line) in enumerate(visible):
                active = line_index == self._lyric_index
                painter.setPen(QColor("#4ECCA3" if active else "#95A5A6"))
                row = QRect(lyric_rect.left(), start_y + row_index * line_h, lyric_rect.width(), line_h)
                painter.drawText(row, Qt.AlignHCenter | Qt.AlignVCenter | Qt.TextWordWrap, line)
        else:
            icon = build_icon("MUSIC", QColor(255, 255, 255, 120), size=92)
            painter.drawPixmap(screen.center().x() - 46, screen.top() + 72, icon)

            title_rect = QRect(screen.left() + 28, screen.top() + 185, screen.width() - 56, 92)
            painter.setPen(QColor("#4ECCA3"))
            painter.drawText(title_rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self._title)
            painter.setPen(QColor("#95A5A6"))
            painter.drawText(
                QRect(screen.left() + 28, title_rect.bottom() + 6, screen.width() - 56, 24),
                Qt.AlignHCenter | Qt.AlignTop,
                self._artist,
            )

        if not self._show_lyrics:
            bar_area = QRect(screen.left() + 34, screen.bottom() - 62, screen.width() - 68, 44)
            gap = 5
            bar_w = max(6, (bar_area.width() - gap * (len(self._bars) - 1)) // len(self._bars))
            for index, value in enumerate(self._bars):
                height = max(4, int(bar_area.height() * value / 100))
                x = bar_area.left() + index * (bar_w + gap)
                y = bar_area.bottom() - height
                painter.fillRect(x + 2, y + 2, bar_w, height, QColor(0, 0, 0, 120))
                painter.fillRect(x, y, bar_w, height, QColor("#4ECCA3"))

        painter.setPen(QColor(255, 255, 255, 22))
        for y in range(0, self.height(), 4):
            painter.drawLine(0, y, self.width(), y)
        painter.setPen(QColor(233, 69, 96, 26))
        for x in range(0, self.width(), 6):
            painter.drawLine(x, 0, x, self.height())

    def _visible_lyric_rows(self) -> list[tuple[int, str]]:
        if len(self._lyrics) <= 6:
            return list(enumerate(self._lyrics))
        start = max(0, min(self._lyric_index - 2, len(self._lyrics) - 6))
        return [(index, self._lyrics[index]) for index in range(start, start + 6)]


class PixelTuneTitleBar(QFrame):
    """Reference-style frameless title bar."""

    minimize_requested = Signal()
    close_requested = Signal()
    drag_delta = Signal(QPoint)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self._drag_origin: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        icon_box = QFrame()
        icon_box.setObjectName("appIcon")
        icon_box.setFixedSize(24, 24)
        icon_box.setAttribute(Qt.WA_TransparentForMouseEvents)
        icon_layout = QHBoxLayout(icon_box)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setPixmap(build_icon("MUSIC", QColor("#FFFFFF"), 14))
        icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        icon_layout.addWidget(icon_label, alignment=Qt.AlignCenter)

        brand = QLabel("PIXELTUNE V1.0")
        brand.setObjectName("brand")
        brand.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.btn_min = PixelButton("")
        self.btn_zoom = PixelButton("")
        self.btn_close = PixelButton("")
        for button, kind in ((self.btn_min, "min"), (self.btn_zoom, "square"), (self.btn_close, "close")):
            button.set_icon_kind(kind)
            button.setFixedSize(28, 28)
        self.btn_close.setObjectName("dangerButton")
        self.btn_close.setStyleSheet(self.btn_close.BASE_STYLE)

        layout.addWidget(icon_box)
        layout.addWidget(brand)
        layout.addStretch(1)
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_zoom)
        layout.addWidget(self.btn_close)

        self.btn_min.clicked.connect(self.minimize_requested.emit)
        self.btn_close.clicked.connect(self.close_requested.emit)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.globalPosition().toPoint()
            window = self.window().windowHandle()
            if window is not None and window.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            now = event.globalPosition().toPoint()
            self.drag_delta.emit(now - self._drag_origin)
            self._drag_origin = now
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_origin = None
        super().mouseReleaseEvent(event)


class MainWindow(QMainWindow):
    """Compact Pixeltune-style player."""

    COLLAPSED_HEIGHT = 760
    EXPANDED_HEIGHT = 1000
    BODY_HEIGHT = 640

    def __init__(self, playlist_model: PlaylistModel, audio_engine: AudioEngine) -> None:
        super().__init__()
        self._playlist_model = playlist_model
        self._audio_engine = audio_engine
        self._analyzer = SpectrumAnalyzer(bars=12)
        self._duration_ms = 0
        self._seeking = False
        self._play_mode = "LIST_LOOP"
        self._state = load_state()
        self._recent_dir = self._state.get("recent_dir", str(Path.home()))
        self._drag_origin: QPoint | None = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setWindowTitle("PixelTune")
        self.setFixedSize(500, self.COLLAPSED_HEIGHT)
        self.setStyleSheet(PIXEL_RETRO)

        self._build_ui()
        self._wire_signals()
        self._restore_state()

    def _build_ui(self) -> None:
        canvas = QWidget()
        self.setCentralWidget(canvas)
        outer = QVBoxLayout(canvas)
        outer.setContentsMargins(18, 18, 22, 22)
        outer.setSpacing(0)

        shadow = QFrame()
        shadow.setObjectName("pixelShadow")
        outer.addWidget(shadow)
        shadow_layout = QVBoxLayout(shadow)
        shadow_layout.setContentsMargins(0, 0, 5, 5)
        shadow_layout.setSpacing(0)

        self.shell = QFrame()
        self.shell.setObjectName("appShell")
        shadow_layout.addWidget(self.shell)

        page = QVBoxLayout(self.shell)
        page.setContentsMargins(4, 4, 4, 4)
        page.setSpacing(0)

        self.title_bar = PixelTuneTitleBar()
        page.addWidget(self.title_bar)

        body = QFrame()
        body.setObjectName("body")
        body.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        body.setFixedHeight(self.BODY_HEIGHT)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 16, 16, 16)
        body_layout.setSpacing(14)
        page.addWidget(body)

        display_frame = QFrame()
        display_frame.setObjectName("displayFrame")
        display_frame.setFixedHeight(388)
        display_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        display_layout = QVBoxLayout(display_frame)
        display_layout.setContentsMargins(10, 10, 10, 10)
        self.display = PixelTuneDisplay()
        display_layout.addWidget(self.display, alignment=Qt.AlignCenter)
        body_layout.addWidget(display_frame)

        top_meta = QHBoxLayout()
        top_meta.setSpacing(8)
        self.btn_load = PixelButton("LOAD")
        self.btn_load.setFixedHeight(28)
        self.btn_load_lrc = PixelButton("LOAD LRC")
        self.btn_load_lrc.setFixedHeight(28)
        self.btn_lyrics = PixelButton("VIEW LYRICS")
        self.btn_lyrics.setFixedHeight(28)
        self.time_elapsed = QLabel("00:00")
        self.time_elapsed.setObjectName("timeText")
        self.time_total = QLabel("00:00")
        self.time_total.setObjectName("timeText")
        top_meta.addWidget(self.btn_load)
        top_meta.addWidget(self.btn_load_lrc)
        top_meta.addWidget(self.btn_lyrics)
        top_meta.addStretch(1)
        top_meta.addWidget(self.time_elapsed)
        top_meta.addWidget(self.time_total)
        body_layout.addLayout(top_meta)

        progress_box = QFrame()
        progress_box.setObjectName("progressBox")
        progress_layout = QVBoxLayout(progress_box)
        progress_layout.setContentsMargins(4, 4, 4, 4)
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        progress_layout.addWidget(self.position_slider)
        body_layout.addWidget(progress_box)

        controls = QHBoxLayout()
        controls.setSpacing(14)
        self.btn_shuffle = self._icon_button("shuffle", 34, "Shuffle")
        self.btn_prev = self._icon_button("prev", 48, "Previous track")
        self.btn_play_toggle = self._icon_button("play", 68, "Play / pause")
        self.btn_play_toggle.setObjectName("primaryTransport")
        self.btn_play_toggle.setStyleSheet(self.btn_play_toggle.BASE_STYLE)
        self.btn_play_toggle.set_icon_size(28)
        self.btn_next = self._icon_button("next", 48, "Next track")
        self.btn_repeat = self._icon_button("repeat", 34, "Repeat one")
        controls.addWidget(self.btn_shuffle)
        controls.addStretch(1)
        controls.addWidget(self.btn_prev)
        controls.addWidget(self.btn_play_toggle)
        controls.addWidget(self.btn_next)
        controls.addStretch(1)
        controls.addWidget(self.btn_repeat)
        body_layout.addLayout(controls)

        lower = QHBoxLayout()
        lower.setSpacing(12)
        volume_box = QFrame()
        volume_box.setObjectName("volumeBox")
        volume_layout = QHBoxLayout(volume_box)
        volume_layout.setContentsMargins(10, 8, 10, 8)
        volume_layout.setSpacing(8)
        volume_label = QLabel()
        volume_label.setPixmap(build_icon("VOLUME", QColor("#95A5A6"), 16))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider, 1)
        lower.addWidget(volume_box, 1)

        self.btn_playlist = self._icon_button("list", 44, "Playlist")
        lower.addWidget(self.btn_playlist)
        body_layout.addLayout(lower)

        self.playlist_panel = QFrame()
        self.playlist_panel.setObjectName("playlistPanel")
        self.playlist_panel.setFixedHeight(self.EXPANDED_HEIGHT - self.COLLAPSED_HEIGHT)
        playlist_layout = QVBoxLayout(self.playlist_panel)
        playlist_layout.setContentsMargins(14, 14, 14, 14)
        playlist_layout.setSpacing(10)
        playlist_header = QHBoxLayout()
        self.playlist_title = QLabel("PLAYLIST (0)")
        self.playlist_title.setObjectName("accentText")
        self.btn_delete = PixelButton("DEL")
        self.btn_delete.setFixedHeight(30)
        playlist_header.addWidget(self.playlist_title)
        playlist_header.addStretch(1)
        playlist_header.addWidget(self.btn_delete)
        playlist_layout.addLayout(playlist_header)

        self.playlist_list = QListWidget()
        self.playlist_list.setMaximumHeight(210)
        self.playlist_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        playlist_layout.addWidget(self.playlist_list)
        self.playlist_panel.setVisible(False)
        page.addWidget(self.playlist_panel)

        grip_row = QHBoxLayout()
        grip_row.addStretch(1)
        grip_row.addWidget(QSizeGrip(self.shell))
        page.addLayout(grip_row)

    def _icon_button(self, kind: str, size: int, tooltip: str) -> PixelButton:
        button = PixelButton("")
        button.set_icon_kind(kind)
        button.setFixedSize(size, size)
        button.setToolTip(tooltip)
        button.set_icon_size(20 if size < 60 else 26)
        return button

    def _wire_signals(self) -> None:
        self.title_bar.drag_delta.connect(lambda delta: self.move(self.pos() + delta))
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.close_requested.connect(self.close)

        self.btn_load.clicked.connect(self._on_add_music)
        self.btn_load_lrc.clicked.connect(self._on_load_lrc)
        self.btn_lyrics.clicked.connect(self._toggle_lyrics)
        self.btn_play_toggle.clicked.connect(self._play_or_pause)
        self.btn_next.clicked.connect(self._next_track)
        self.btn_prev.clicked.connect(self._prev_track)
        self.btn_shuffle.clicked.connect(self._toggle_shuffle)
        self.btn_repeat.clicked.connect(self._toggle_repeat)
        self.btn_playlist.clicked.connect(self._toggle_playlist)
        self.btn_delete.clicked.connect(self._delete_selected_track)

        self.volume_slider.valueChanged.connect(lambda v: self._audio_engine.set_volume(v / 100))
        self.position_slider.sliderPressed.connect(self._on_seek_start)
        self.position_slider.sliderReleased.connect(self._on_seek_end)
        self.playlist_list.itemClicked.connect(self._on_playlist_item_clicked)

        for draggable in (self.shell, self.display, self.title_bar):
            draggable.installEventFilter(self)

        self._playlist_model.current_track_changed.connect(self._on_current_track_changed)
        self._playlist_model.playlist_changed.connect(self._refresh_playlist)
        self._audio_engine.state_changed.connect(self._on_audio_state_changed)
        self._audio_engine.playback_finished.connect(self._on_track_finished)
        self._audio_engine.position_changed.connect(self._on_position_changed)
        self._audio_engine.duration_changed.connect(self._on_duration_changed)

        QShortcut(QKeySequence("Space"), self, activated=self._play_or_pause)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._on_add_music)
        QShortcut(QKeySequence("Ctrl+Right"), self, activated=self._next_track)
        QShortcut(QKeySequence("Ctrl+Left"), self, activated=self._prev_track)
        QShortcut(QKeySequence("Delete"), self, activated=self._delete_selected_track)
        QShortcut(QKeySequence("Escape"), self, activated=self.close)

    def _on_add_music(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Music Files",
            self._recent_dir,
            "Audio Files (*.mp3 *.wav *.ogg)",
        )
        if not files:
            return
        self._recent_dir = str(Path(files[0]).parent)
        added = self._playlist_model.add_files(files)
        if added == 0:
            QMessageBox.warning(self, "No Files Added", "No supported audio files were added.")
        self._save_state()

    def _on_load_lrc(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select LRC Lyrics",
            self._recent_dir,
            "Lyrics Files (*.lrc);;Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return
        path = Path(file_path)
        self._recent_dir = str(path.parent)
        try:
            lines, timed_lines = _parse_lrc(path)
        except OSError as exc:
            QMessageBox.critical(self, "Lyrics Error", f"Cannot load lyrics:\n{exc}")
            return
        if not lines and not timed_lines:
            QMessageBox.warning(self, "Lyrics Empty", "No lyrics were found in this file.")
            return
        self.display.set_lyrics(lines, timed_lines)
        self.display.set_show_lyrics(True)
        self.btn_lyrics.setText("VIEW ART")
        self.btn_lyrics.setObjectName("activeToggle")
        self.btn_lyrics.setStyleSheet(self.btn_lyrics.BASE_STYLE)
        self._save_state()

    def _on_playlist_item_clicked(self, item: QListWidgetItem) -> None:
        row = self.playlist_list.row(item)
        if not 0 <= row < len(self._playlist_model.tracks):
            return
        self._playlist_model.set_current_index(row)
        self._play_current()

    def _play_current(self) -> None:
        track = self._playlist_model.current_track
        if track is None:
            QMessageBox.information(self, "Playlist Empty", "Please add local music first.")
            return
        try:
            self._audio_engine.load(track.path)
            self._audio_engine.play()
            self.display.set_frames(self._analyzer.build_frames(track.path))
            self.display.start()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Playback Error", f"Cannot play file:\n{exc}")

    def _play_or_pause(self) -> None:
        if self._audio_engine.is_paused():
            self._audio_engine.play()
            self.display.start()
        elif self._audio_engine.is_playing():
            self._audio_engine.pause()
            self.display.pause()
        else:
            self._play_current()

    def _stop(self) -> None:
        self._audio_engine.stop()
        self.display.stop()
        self.position_slider.setValue(0)
        self._update_time_label(0)

    def _next_track(self) -> None:
        if self._playlist_model.next_track() is not None:
            self._play_current()

    def _prev_track(self) -> None:
        if self._playlist_model.previous_track() is not None:
            self._play_current()

    def _toggle_shuffle(self) -> None:
        self._play_mode = "SHUFFLE" if self._play_mode != "SHUFFLE" else "LIST_LOOP"
        self._sync_mode_buttons()
        self._save_state()

    def _toggle_repeat(self) -> None:
        self._play_mode = "SINGLE_LOOP" if self._play_mode != "SINGLE_LOOP" else "LIST_LOOP"
        self._sync_mode_buttons()
        self._save_state()

    def _toggle_lyrics(self) -> None:
        show_lyrics = self.btn_lyrics.text() == "VIEW LYRICS"
        self.display.set_show_lyrics(show_lyrics)
        self.btn_lyrics.setText("VIEW ART" if show_lyrics else "VIEW LYRICS")
        self.btn_lyrics.setObjectName("activeToggle" if show_lyrics else "")
        self.btn_lyrics.setStyleSheet(self.btn_lyrics.BASE_STYLE)

    def _toggle_playlist(self) -> None:
        visible = not self.playlist_panel.isVisible()
        self.playlist_panel.setVisible(visible)
        self.btn_playlist.setObjectName("activeToggle" if visible else "")
        self.btn_playlist.setStyleSheet(self.btn_playlist.BASE_STYLE)
        self.setFixedSize(500, self.EXPANDED_HEIGHT if visible else self.COLLAPSED_HEIGHT)

    def _delete_selected_track(self) -> None:
        row = self.playlist_list.currentRow()
        if not 0 <= row < len(self._playlist_model.tracks):
            return
        current = self._playlist_model.current_track
        removing_current = current is not None and self._playlist_model.tracks[row].path == current.path
        self._playlist_model.remove_at(row)
        if removing_current:
            self._stop()
        self._save_state()

    def _on_current_track_changed(self, track_obj: object) -> None:
        if track_obj is None:
            self.display.set_track("NO TRACK LOADED", "LOCAL LIBRARY")
            return
        self.display.set_track(track_obj.title, "LOCAL FILE")
        self._sync_playlist_selection()

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._duration_ms = duration_ms
        self.position_slider.setRange(0, max(duration_ms, 0))
        self._update_time_label(0)

    def _on_position_changed(self, position_ms: int) -> None:
        if self._seeking:
            return
        self.position_slider.setValue(position_ms)
        self.display.set_position_ms(position_ms)
        self._update_time_label(position_ms)

    def _on_seek_start(self) -> None:
        self._seeking = True

    def _on_seek_end(self) -> None:
        self._seeking = False
        self._audio_engine.seek_ms(self.position_slider.value())

    def _on_audio_state_changed(self, state: str) -> None:
        if state == "playing":
            self.btn_play_toggle.set_icon_kind("pause")
            self.display.start()
        elif state in {"paused", "stopped", "finished"}:
            self.btn_play_toggle.set_icon_kind("play")
            if state == "paused":
                self.display.pause()
            else:
                self.display.stop()

    def _on_track_finished(self) -> None:
        if self._play_mode == "SINGLE_LOOP":
            self._play_current()
            return
        if self._play_mode == "SHUFFLE" and self._playlist_model.tracks:
            self._playlist_model.set_current_index(random.randint(0, len(self._playlist_model.tracks) - 1))
            self._play_current()
            return
        self._next_track()

    def _refresh_playlist(self) -> None:
        self.playlist_list.clear()
        tracks = self._playlist_model.tracks
        self.playlist_title.setText(f"PLAYLIST ({len(tracks)})")
        if not tracks:
            item = QListWidgetItem("INSERT AUDIO FILES")
            item.setFlags(Qt.NoItemFlags)
            self.playlist_list.addItem(item)
            return
        for index, track in enumerate(tracks, start=1):
            self.playlist_list.addItem(f"{index:02d}  {track.title.upper()}    --:--")
        self._sync_playlist_selection()

    def _sync_playlist_selection(self) -> None:
        current = self._playlist_model.current_track
        if current is None:
            return
        for index, track in enumerate(self._playlist_model.tracks):
            if track.path == current.path:
                self.playlist_list.setCurrentRow(index)
                break

    def _sync_mode_buttons(self) -> None:
        self.btn_shuffle.setObjectName("activeToggle" if self._play_mode == "SHUFFLE" else "")
        self.btn_repeat.setObjectName("activeToggle" if self._play_mode == "SINGLE_LOOP" else "")
        self.btn_shuffle.setStyleSheet(self.btn_shuffle.BASE_STYLE)
        self.btn_repeat.setStyleSheet(self.btn_repeat.BASE_STYLE)

    def _update_time_label(self, position_ms: int) -> None:
        def fmt(ms: int) -> str:
            seconds = max(0, ms // 1000)
            return f"{seconds // 60:02d}:{seconds % 60:02d}"

        self.time_elapsed.setText(fmt(position_ms))
        self.time_total.setText(fmt(self._duration_ms))

    def _restore_state(self) -> None:
        self._playlist_model.replace_files(self._state.get("playlist", []))
        self._play_mode = self._state.get("play_mode", "LIST_LOOP")
        if self._play_mode not in {"LIST_LOOP", "SINGLE_LOOP", "SHUFFLE"}:
            self._play_mode = "LIST_LOOP"
        self._sync_mode_buttons()
        self._refresh_playlist()

    def _save_state(self) -> None:
        save_state(
            {
                "play_mode": self._play_mode,
                "playlist": self._playlist_model.to_path_list(),
                "recent_dir": self._recent_dir,
            }
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        self._save_state()
        super().closeEvent(event)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched in (self.shell, self.display, self.title_bar):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_origin = event.globalPosition().toPoint()
                window = self.windowHandle()
                if window is not None and window.startSystemMove():
                    return True
            if event.type() == QEvent.Type.MouseMove and self._drag_origin is not None and event.buttons() & Qt.LeftButton:
                now = event.globalPosition().toPoint()
                self.move(self.pos() + now - self._drag_origin)
                self._drag_origin = now
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_origin = None
        return super().eventFilter(watched, event)


def _parse_lrc(path: Path) -> tuple[list[str], list[tuple[int, str]]]:
    """Parse LRC timestamp lines and return plain plus timed lyrics."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="gb18030")

    timestamp_pattern = re.compile(r"\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?]")
    plain_lines: list[str] = []
    timed_lines: list[tuple[int, str]] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matches = list(timestamp_pattern.finditer(line))
        lyric = timestamp_pattern.sub("", line).strip()
        if not lyric:
            continue
        lyric = lyric.upper()
        if matches:
            for match in matches:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                fraction = match.group(3) or "0"
                milliseconds = int(fraction.ljust(3, "0")[:3])
                timed_lines.append(((minutes * 60 + seconds) * 1000 + milliseconds, lyric))
        else:
            if not (line.startswith("[") and line.endswith("]")):
                plain_lines.append(lyric)

    if timed_lines:
        timed_lines.sort(key=lambda item: item[0])
        plain_lines = [line for _time_ms, line in timed_lines]
    return plain_lines, timed_lines
