"""Terminal-style chat dialog for PixelBeat."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class PixelButton(QPushButton):
    """Pixel-style button with press effect."""

    def __init__(self, text: str, color: str = "#4ecca3", parent=None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: #1a1a2e;
                border: 3px solid #000000;
                padding: 5px 15px;
                font-family: monospace;
                font-size: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: white;
            }}
            QPushButton:pressed {{
                padding-top: 10px;
                padding-left: 18px;
            }}
        """)


class MessageBubble(QFrame):
    """Custom message bubble widget."""

    def __init__(self, text: str, is_user: bool = False) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        bg_color = "#4ecca3" if is_user else "#1a2e4c"
        text_color = "#1a1a2e" if is_user else "#4ecca3"

        self.label = QLabel(text.upper())
        self.label.setWordWrap(True)
        self.label.setStyleSheet(f"""
            color: {text_color};
            font-family: monospace;
            font-size: 14px;
            background: transparent;
        """)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid black;
                padding: 10px;
                border-radius: 0px;
            }}
        """)

        layout.addWidget(self.label)
        self.setMaximumWidth(300)


class TerminalDialog(QDialog):
    """Terminal-style dialog with chat-like interface."""

    command_executed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setFixedSize(450, 600)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._drag_pos = None

        self._init_ui()
        self._add_message("WELCOME TO PIXELBEAT TERMINAL.", is_user=False)
        self._add_message("SYSTEM STATUS: NOMINAL.", is_user=False)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None
        event.accept()

    def _init_ui(self) -> None:
        # Outer container
        self._container = QFrame(self)
        self._container.setGeometry(10, 10, 430, 580)
        self._container.setStyleSheet("""
            QFrame {
                background-color: #0f3460;
                border: 4px solid #1a1a2e;
            }
        """)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(0, 0, 0, 0)

        # 1. Title bar
        title_bar = QFrame()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("background-color: #16213e; border: none; border-bottom: 2px solid black;")
        title_layout = QHBoxLayout(title_bar)

        title_label = QLabel("■ TERMINAL_ACCESS_V2.0")
        title_label.setStyleSheet("color: #4ecca3; font-family: monospace; font-size: 10px; font-weight: bold;")

        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("background: #e94560; color: white; border: 2px solid black; font-weight: bold;")

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        layout.addWidget(title_bar)

        # 2. Chat display area (QScrollArea)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("border: none; background-color: #16213e;")

        self._scroll_content = QWidget()
        self._scroll_content.setStyleSheet("background-color: #16213e;")
        self._chat_layout = QVBoxLayout(self._scroll_content)
        self._chat_layout.setAlignment(Qt.AlignTop)
        self._chat_layout.setSpacing(15)

        self._scroll.setWidget(self._scroll_content)
        layout.addWidget(self._scroll)

        # 3. Input area
        input_area = QFrame()
        input_area.setFixedHeight(100)
        input_area.setStyleSheet("background-color: #1a1a2e; border-top: 2px solid black;")
        input_layout = QVBoxLayout(input_area)

        edit_layout = QHBoxLayout()
        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("WAITING FOR COMMAND...")
        self._input_field.setStyleSheet("""
            QLineEdit {
                background-color: #0f3460;
                color: #4ecca3;
                border: 2px solid #533483;
                padding: 10px;
                font-family: monospace;
            }
            QLineEdit:focus { border-color: #e94560; }
        """)
        self._input_field.returnPressed.connect(self._send_message)

        send_btn = PixelButton("SEND", color="#4ecca3")
        send_btn.clicked.connect(self._send_message)

        edit_layout.addWidget(self._input_field)
        edit_layout.addWidget(send_btn)
        input_layout.addLayout(edit_layout)

        footer = QLabel("ENCRYPTION: AES-256 | NODE: 0x88FF")
        footer.setStyleSheet("color: rgba(78, 204, 163, 0.4); font-size: 8px;")
        input_layout.addWidget(footer)

        layout.addWidget(input_area)

    def _add_message(self, text: str, is_user: bool = False) -> None:
        bubble = MessageBubble(text, is_user)

        row = QHBoxLayout()
        if is_user:
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()

        self._chat_layout.addLayout(row)

        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def _send_message(self) -> None:
        text = self._input_field.text().strip()
        if not text:
            return

        self._add_message(text, is_user=True)
        self._input_field.clear()

        self.command_executed.emit(text)

        QTimer.singleShot(800, lambda: self._add_message("COMMAND RECEIVED. PROCESSING...", is_user=False))
