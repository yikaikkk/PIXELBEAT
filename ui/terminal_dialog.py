"""Terminal-style chat dialog for PixelBeat with agent integration."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFontDatabase, QMouseEvent
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

PIXEL_FONT_FAMILY = "Press Start 2P"

def _load_pixel_font() -> str:
    """Load pixel font and return family name."""
    font_paths = [
        Path(__file__).parent.parent / "assets" / "fonts" / "PressStart2P-Regular.ttf",
        Path(__file__).parent.parent.parent / "assets" / "fonts" / "PressStart2P-Regular.ttf",
    ]
    for font_path in font_paths:
        if font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id >= 0:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    return families[0]
    return "Courier New"


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


# class MessageBubble(QFrame):
#     """Custom message bubble widget with scrollable markdown text."""

#     MAX_TEXT_HEIGHT = 500

#     def __init__(self, text: str, is_user: bool = False, pixel_font: str = "Courier New") -> None:
#         super().__init__()
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)

#         bg_color = "#4ecca3" if is_user else "#1a2e4c"
#         text_color = "#1a1a2e" if is_user else "#4ecca3"

#         self.text_edit = QTextEdit()
#         self.text_edit.setReadOnly(True)
#         self.text_edit.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextBrowserInteraction)
#         self.text_edit.setMarkdown(text)
#         # self.text_edit.setMaximumHeight(self.MAX_TEXT_HEIGHT)
#         self.text_edit.setFixedWidth(300)
#         font_size = 8 if pixel_font != "Courier New" else 14
#         self.text_edit.setStyleSheet(f"""
#             QTextEdit {{
#                 color: {text_color};
#                 font-family: "{pixel_font}", monospace;
#                 font-size: {font_size}px;
#                 background: transparent;
#                 border: none;
#             }}
#         """)

#         self.setStyleSheet(f"""
#             QFrame {{
#                 background-color: {bg_color};
#                 border: 2px solid black;
#                 padding: 10px;
#                 border-radius: 0px;
#             }}
#         """)

#         layout.addWidget(self.text_edit)
#         self.setMaximumWidth(380)
#         self.setMinimumWidth(200)

# class MessageBubble(QFrame):

#     MAX_WIDTH = 320
#     MAX_HEIGHT = 900

#     def __init__(
#         self,
#         text: str,
#         is_user: bool = False,
#         pixel_font: str = "Courier New"
#     ) -> None:

#         super().__init__()

#         bg_color = "#4ecca3" if is_user else "#1f2937"
#         text_color = "#111827" if is_user else "#f3f4f6"

#         self.setStyleSheet(f"""
#             QFrame {{
#                 background-color: {bg_color};
#                 border-radius: 12px;
#             }}
#         """)

#         outer_layout = QVBoxLayout(self)

#         outer_layout.setContentsMargins(12, 10, 12, 10)

#         from PySide6.QtWidgets import QTextBrowser

#         self.text = QTextBrowser()

#         self.text.setMarkdown(text)

#         self.text.setFrameShape(QFrame.NoFrame)

#         self.text.setOpenExternalLinks(True)

#         self.text.setVerticalScrollBarPolicy(
#             Qt.ScrollBarAlwaysOff
#         )

#         self.text.setHorizontalScrollBarPolicy(
#             Qt.ScrollBarAlwaysOff
#         )

#         self.text.document().setDocumentMargin(0)

#         font_size = 8 if pixel_font != "Courier New" else 13

#         self.text.setStyleSheet(f"""
#             QTextBrowser {{
#                 background: transparent;
#                 color: {text_color};

#                 border: none;

#                 font-family: "{pixel_font}";
#                 font-size: {font_size}px;
#             }}
#         """)

#         # =========================
#         # VERY IMPORTANT
#         # =========================

#         self.text.setFixedWidth(self.MAX_WIDTH)

#         # 让 document 知道换行宽度
#         self.text.document().setTextWidth(
#             self.MAX_WIDTH - 20
#         )

#         # 强制 layout 更新
#         self.text.document().adjustSize()

#         # 重新计算高度
#         doc_height = int(
#             self.text.document().size().height()
#         )

#         final_height = min(
#             max(doc_height + 10, 40),
#             self.MAX_HEIGHT
#         )

#         self.text.setFixedHeight(final_height)

#         outer_layout.addWidget(self.text)

# class MessageBubble(QFrame):

#     MAX_WIDTH = 300
#     MAX_HEIGHT = 2000

#     def __init__(
#         self,
#         text: str,
#         is_user: bool = False,
#         pixel_font: str = "Courier New"
#     ) -> None:

#         super().__init__()

#         # =========================
#         # COLORS
#         # =========================
#         bg_color = "#4ecca3" if is_user else "#1f2937"
#         text_color = "#111827" if is_user else "#f3f4f6"

#         # =========================
#         # BUBBLE STYLE
#         # =========================
#         self.setStyleSheet(f"""
#             QFrame {{
#                 background-color: {bg_color};
#                 border-radius: 14px;
#             }}
#         """)

#         # =========================
#         # LAYOUT
#         # =========================
#         outer_layout = QVBoxLayout(self)

#         outer_layout.setContentsMargins(
#             14,
#             10,
#             14,
#             10
#         )

#         outer_layout.setSpacing(0)

#         # =========================
#         # TEXT
#         # =========================
#         from PySide6.QtWidgets import QTextBrowser

#         self.text = QTextBrowser()

#         self.text.setMarkdown(text)

#         self.text.setOpenExternalLinks(True)

#         self.text.setFrameShape(QFrame.NoFrame)

#         self.text.setVerticalScrollBarPolicy(
#             Qt.ScrollBarAlwaysOff
#         )

#         self.text.setHorizontalScrollBarPolicy(
#             Qt.ScrollBarAlwaysOff
#         )

#         self.text.document().setDocumentMargin(0)

#         # =========================
#         # FONT
#         # =========================
#         font_family = "JetBrains Mono"
#         # self.text.setAlignment(Qt.AlignCenter)
#         self.text.setStyleSheet(f"""
#             QTextBrowser {{
#                 background: transparent;

#                 color: {text_color};

#                 border: none;

#                 font-family: "{font_family}";
#                 font-size: 11px;

#                 line-height: 1.2;
#                 padding-top: 2px;

#                 padding-bottom: 2px;
#             }}
#         """)

#         # =========================
#         # IMPORTANT
#         # =========================

#         #
#         # 固定宽度
#         #
#         self.text.setFixedWidth(self.MAX_WIDTH)

#         #
#         # document 换行宽度
#         #
#         self.text.document().setTextWidth(
#             self.MAX_WIDTH - 24
#         )

#         #
#         # 重新 layout
#         #
#         self.text.document().adjustSize()

#         #
#         # 获取真实高度
#         #
#         doc_height = int(
#             self.text.document().size().height()
#         )

#         # final_height = min(
#         #     max(doc_height + 12, 40),
#         #     self.MAX_HEIGHT
#         # )
#         min_h = self.text.fontMetrics().height() + 6

#         final_height = min(

#             max(doc_height, min_h),

#             self.MAX_HEIGHT

# )

#         #
#         # 高度限制
#         #
#         self.text.setMinimumHeight(final_height)

#         self.text.setMaximumHeight(final_height)

#         #
#         # add text widget
#         #
#         outer_layout.addWidget(self.text)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QTextBrowser, QSizePolicy


class MessageBubble(QFrame):

    MAX_WIDTH = 300
    MAX_HEIGHT = 2000

    def __init__(self, text: str, is_user: bool = False, font_family: str = "JetBrains Mono") -> None:
        super().__init__()

        # =========================
        # COLORS
        # =========================
        bg_color = "#4ecca3" if is_user else "#1f2937"
        text_color = "#111827" if is_user else "#f3f4f6"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 14px;
            }}
        """)

        # =========================
        # LAYOUT
        # =========================
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(0)

        # =========================
        # TEXT
        # =========================
        self.text = QTextBrowser()
        self.text.setMarkdown(text)

        self.text.setFrameShape(QFrame.NoFrame)
        self.text.setOpenExternalLinks(True)

        # 禁止内部滚动（关键）
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.text.document().setDocumentMargin(0)

        # =========================
        # STYLE
        # =========================
        self.text.setStyleSheet(f"""
            QTextBrowser {{
                background: transparent;
                color: {text_color};

                border: none;

                font-family: "{font_family}";
                font-size: 11px;

                line-height: 1.2;

                padding: 2px 2px;
            }}
        """)

        # =========================
        # WIDTH CONTROL
        # =========================
        self.text.setFixedWidth(self.MAX_WIDTH)
        self.text.document().setTextWidth(self.MAX_WIDTH - 10)
        self.text.document().adjustSize()

        # =========================
        # HEIGHT CONTROL (核心修复)
        # =========================

        font_h = self.text.fontMetrics().height()

        doc_h = int(self.text.document().size().height())

        min_h = font_h + 6   # ⭐ 一行高度（关键）

        final_h = min(max(doc_h, min_h), self.MAX_HEIGHT)

        # ❗不要 fixedHeight（Qt layout 会炸）
        self.text.setMinimumHeight(final_h)
        self.text.setMaximumHeight(self.MAX_HEIGHT)

        # 让 sizeHint 跟随内容
        self.text.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

        layout.addWidget(self.text)


class AgentWorker(QThread):
    """Worker thread to run agent processing without blocking UI."""
    
    response_ready = Signal(str, bool)
    
    def __init__(self, engine, message: str) -> None:
        super().__init__()
        self.engine = engine
        self.message = message
    
    def run(self) -> None:
        try:
            response = self.engine.process_message(self.message)
            self.response_ready.emit(response, False)
        except Exception as e:
            self.response_ready.emit(f"Error: {str(e)}", False)


class TerminalDialog(QDialog):
    """Terminal-style dialog with chat-like interface and agent integration."""

    command_executed = Signal(str)

    def __init__(self, parent=None, provider_name: str = "qwen") -> None:
        super().__init__(parent)
        self.setModal(False)
        self.setFixedSize(450, 600)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._drag_pos = None
        self.engine = None
        self._worker = None
        self._pixel_font = _load_pixel_font()

        self._init_ui()
        self._init_agent(provider_name)
        self._add_message("WELCOME TO PIXELBEAT TERMINAL.", is_user=False)
        self._add_message("SYSTEM STATUS: NOMINAL.", is_user=False)
        self._add_message("AGENT READY. AWAITING COMMANDS.", is_user=False)

    def _init_agent(self, provider_name: str) -> None:
        """Initialize the agent engine."""
        try:
            from core.agent.agent_engine import AgentEngine
            self.engine = AgentEngine(
                provider_name=provider_name,
                on_message=self._on_agent_message,
                on_tool_call=self._on_tool_call,
            )
        except Exception as e:
            self._add_message(f"AGENT INIT ERROR: {str(e)}", is_user=False)

    def _on_agent_message(self, message: str, is_user: bool) -> None:
        """Callback for agent messages - runs in worker thread, use QTimer to update UI."""
        QTimer.singleShot(0, lambda: self._add_message(message, is_user))

    def _on_tool_call(self, name: str, args: dict) -> None:
        """Callback for tool calls."""
        QTimer.singleShot(0, lambda: self._add_message(f"[TOOL] {name} CALLED", is_user=False))

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
        bubble = MessageBubble(text, is_user, self._pixel_font)

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

        if self.engine is not None:
            self._add_message("PROCESSING...", is_user=False)
            self._worker = AgentWorker(self.engine, text)
            self._worker.response_ready.connect(self._on_response_ready)
            self._worker.start()
        else:
            QTimer.singleShot(800, lambda: self._add_message("COMMAND RECEIVED. PROCESSING...", is_user=False))

    def _on_response_ready(self, response: str, is_user: bool) -> None:
        """Handle agent response."""
        self._add_message(response, is_user)

    def closeEvent(self, event) -> None:
        """Clean up agent engine on close."""
        if self.engine is not None:
            self.engine.close()
        super().closeEvent(event)
