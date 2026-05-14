"""Frameless window title bar with pixel status details."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPoint, QTimer, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from ui.widgets.pixel_button import PixelButton


class PixelTitleBar(QFrame):
    """Custom title/status bar for a frameless pixel window."""

    minimize_requested = Signal()
    close_requested = Signal()
    drag_delta = Signal(QPoint)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self._drag_origin: QPoint | None = None
        self._battery_phase = 0
        self._signal_phase = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(6)

        self.app_label = QLabel("PIXELBEAT OS")
        self.app_label.setObjectName("caption")
        self.clock_label = QLabel("--:--")
        self.battery_label = QLabel("PWR [####]")
        self.signal_label = QLabel("SIG <ON>")
        self.btn_min = PixelButton("MIN")
        self.btn_close = PixelButton("CLOSE")
        self.btn_min.setFixedWidth(34)
        self.btn_close.setFixedWidth(46)
        self.btn_min.set_icon_kind("min")
        self.btn_close.set_icon_kind("close")

        layout.addWidget(self.app_label)
        layout.addStretch(1)
        layout.addWidget(self.battery_label)
        layout.addWidget(self.clock_label)
        layout.addWidget(self.signal_label)
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_close)

        self.btn_min.clicked.connect(self.minimize_requested.emit)
        self.btn_close.clicked.connect(self.close_requested.emit)

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start()
        self._tick_clock()

        self._ambient_timer = QTimer(self)
        self._ambient_timer.setInterval(360)
        self._ambient_timer.timeout.connect(self._tick_ambient)
        self._ambient_timer.start()

    def _tick_clock(self) -> None:
        self.clock_label.setText(datetime.now().strftime("%H:%M"))

    def _tick_ambient(self) -> None:
        battery_frames = ["PWR [####]", "PWR [### ]", "PWR [####]", "PWR [##  ]"]
        signal_frames = ["SIG <ON>", "SIG <..>", "SIG <ON>", "SIG <::>"]
        self._battery_phase = (self._battery_phase + 1) % len(battery_frames)
        self._signal_phase = (self._signal_phase + 1) % len(signal_frames)
        self.battery_label.setText(battery_frames[self._battery_phase])
        self.signal_label.setText(signal_frames[self._signal_phase])

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            now = event.globalPosition().toPoint()
            delta = now - self._drag_origin
            self._drag_origin = now
            self.drag_delta.emit(delta)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_origin = None
        super().mouseReleaseEvent(event)
