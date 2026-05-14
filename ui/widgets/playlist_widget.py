"""RPG-style playlist widget."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyle, QListWidget, QListWidgetItem, QStyledItemDelegate, QVBoxLayout, QWidget

from models.playlist_model import PlaylistModel


class _PlaylistDelegate(QStyledItemDelegate):
    """Custom delegate to draw retro menu rows with blink arrow."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._blink_on = True
        self._arrow_phase = 0

    def set_blink(self, enabled: bool) -> None:
        self._blink_on = enabled

    def toggle_blink(self) -> None:
        self._blink_on = not self._blink_on
        self._arrow_phase = (self._arrow_phase + 1) % 3

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        try:
            rect = option.rect
            selected = bool(option.state & QStyle.State_Selected)
            if selected:
                painter.fillRect(rect, QColor("#8BAC0F" if self._blink_on else "#718e0c"))
                painter.setPen(QColor("#1A1C1A"))
            else:
                painter.fillRect(rect, QColor("#2D322D"))
                painter.setPen(QColor("#D8E0A0"))

            text = index.data(Qt.DisplayRole) or ""
            if selected:
                arrow_offset = 6 + self._arrow_phase
                painter.drawText(rect.adjusted(arrow_offset, 0, 0, 0), Qt.AlignVCenter, ">")
                painter.drawText(rect.adjusted(24, 0, -8, 0), Qt.AlignVCenter, text)
            else:
                painter.drawText(rect.adjusted(24, 0, -8, 0), Qt.AlignVCenter, text)

            painter.setPen(QColor("#0D0F0D"))
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        finally:
            painter.restore()

    def sizeHint(self, option, index):  # noqa: N802
        size = super().sizeHint(option, index)
        size.setHeight(28)
        return size


class PlaylistWidget(QWidget):
    """Retro game menu playlist with custom selection visuals."""

    track_selected = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, playlist_model: PlaylistModel, parent=None) -> None:
        super().__init__(parent)
        self._playlist_model = playlist_model
        self._list = QListWidget()
        self._list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self._list.setFrameShape(QListWidget.NoFrame)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setFocusPolicy(Qt.StrongFocus)
        self._list.installEventFilter(self)
        self._list.setStyleSheet(
            "QListWidget{background:#2D322D;border:1px solid #0D0F0D;outline:none;padding:4px;} "
            "QListWidget::item{border:0px;} "
            "QScrollBar:vertical{background:#1A1C1A;width:10px;border-left:1px solid #0D0F0D;} "
            "QScrollBar::handle:vertical{background:#8BAC0F;min-height:16px;border:1px solid #0D0F0D;}"
        )
        self._list.currentRowChanged.connect(self.track_selected.emit)

        self._delegate = _PlaylistDelegate(self._list)
        self._list.setItemDelegate(self._delegate)

        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(220)
        self._blink_timer.timeout.connect(self._tick_blink)
        self._blink_timer.start()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

        self._playlist_model.playlist_changed.connect(self.refresh)
        self._playlist_model.current_track_changed.connect(self._sync_current_row)

    def selected_index(self) -> int:
        """Return selected playlist index, or -1 when the placeholder is visible."""
        row = self._list.currentRow()
        if 0 <= row < len(self._playlist_model.tracks):
            return row
        return -1

    def refresh(self) -> None:
        self._list.clear()
        if not self._playlist_model.tracks:
            item = QListWidgetItem("> INSERT TRACKS")
            item.setFlags(Qt.NoItemFlags)
            self._list.addItem(item)
            return
        for track in self._playlist_model.tracks:
            item = QListWidgetItem(track.title.upper())
            item.setToolTip(str(track.path))
            self._list.addItem(item)
        self._sync_current_row(self._playlist_model.current_track)

    def _sync_current_row(self, _track_obj: object) -> None:
        tracks = self._playlist_model.tracks
        current = self._playlist_model.current_track
        if not current or not tracks:
            return
        for index, track in enumerate(tracks):
            if track.path == current.path:
                self._list.blockSignals(True)
                self._list.setCurrentRow(index)
                self._list.blockSignals(False)
                break

    def _tick_blink(self) -> None:
        self._delegate.toggle_blink()
        self._list.viewport().update()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self._list and event.type() == QEvent.Type.KeyPress and event.key() in (
            Qt.Key_Delete,
            Qt.Key_Backspace,
        ):
            index = self.selected_index()
            if index >= 0:
                self.delete_requested.emit(index)
                return True
        return super().eventFilter(watched, event)
