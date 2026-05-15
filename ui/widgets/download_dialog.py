"""Download dialog for Bilibili audio."""

from __future__ import annotations

import os
from threading import Thread

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from ui.themes import PIXEL_RETRO
from utils.bilibili_downloader import BilibiliDownloader


class DownloadDialog(QDialog):
    """Modal dialog for downloading Bilibili videos as audio."""

    download_completed = Signal(str)
    progress_updated = Signal(int)
    show_ok_signal = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("DOWNLOAD FROM BILIBILI")
        self.setFixedSize(550, 520)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setStyleSheet(PIXEL_RETRO)

        self._downloader = BilibiliDownloader()
        self._is_downloading = False

        self._build_ui()
        self._wire_signals()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)

        # Title section
        title_frame = QFrame()
        title_frame.setObjectName("progressBox")
        title_frame.setMinimumHeight(60)
        title_layout = QVBoxLayout(title_frame)
        title_layout.setContentsMargins(24, 16, 24, 16)
        
        title_label = QLabel("DOWNLOAD BILIBILI AUDIO")
        title_label.setObjectName("accentText")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14px;")
        title_layout.addWidget(title_label)
        main_layout.addWidget(title_frame)

        # URL Input section
        url_frame = QFrame()
        url_frame.setObjectName("progressBox")
        url_frame.setMinimumHeight(110)
        url_layout = QVBoxLayout(url_frame)
        url_layout.setContentsMargins(24, 16, 24, 16)
        url_layout.setSpacing(12)
        
        url_label = QLabel("VIDEO URL:")
        url_label.setObjectName("artistText")
        url_label.setStyleSheet("font-size: 11px;")
        url_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter Bilibili video URL...")
        self.url_input.setMinimumHeight(44)
        self.url_input.setStyleSheet("""
            QLineEdit {
                background-color: #1A1A2E;
                border: 2px solid #000000;
                padding: 12px;
                color: #FFFFFF;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #4ECCA3;
            }
        """)
        url_layout.addWidget(self.url_input)
        main_layout.addWidget(url_frame)

        # Info Panel section
        info_frame = QFrame()
        info_frame.setObjectName("progressBox")
        info_frame.setMinimumHeight(120)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(24, 16, 24, 16)
        info_layout.setSpacing(12)

        self.title_info = QLabel("TITLE: -")
        self.size_info = QLabel("SIZE: -")
        self.status_info = QLabel("STATUS: READY")
        
        for label in [self.title_info, self.size_info, self.status_info]:
            label.setObjectName("artistText")
            label.setStyleSheet("font-size: 11px;")
            label.setWordWrap(True)
            info_layout.addWidget(label)
        
        main_layout.addWidget(info_frame)

        # Progress Bar section
        progress_frame = QFrame()
        progress_frame.setObjectName("progressBox")
        progress_frame.setMinimumHeight(90)
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(24, 16, 24, 16)
        progress_layout.setSpacing(12)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(24)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0F3460;
                border: 2px solid #000000;
                height: 24px;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #4ECCA3;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(progress_frame)

        # Buttons section
        button_frame = QFrame()
        button_frame.setObjectName("progressBox")
        button_frame.setMinimumHeight(80)
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(24, 16, 24, 16)
        button_layout.setSpacing(20)
        button_layout.setAlignment(Qt.AlignCenter)

        self.btn_download = QPushButton("DOWNLOAD")
        self.btn_download.setMinimumHeight(40)
        self.btn_download.setStyleSheet("""
            QPushButton {
                background-color: #4ECCA3;
                color: #000000;
                border: 3px solid #000000;
                padding: 10px 24px;
                font-family: "Press Start 2P", "Courier New", monospace;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #3DBD9A;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        """)

        self.btn_cancel = QPushButton("CANCEL")
        self.btn_cancel.setMinimumHeight(40)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #E94560;
                color: #FFFFFF;
                border: 3px solid #000000;
                padding: 10px 24px;
                font-family: "Press Start 2P", "Courier New", monospace;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #D83550;
            }
        """)

        button_layout.addWidget(self.btn_download)
        button_layout.addWidget(self.btn_cancel)
        main_layout.addWidget(button_frame)

    def _wire_signals(self) -> None:
        self.btn_download.clicked.connect(self._start_download)
        self.btn_cancel.clicked.connect(self.close)
        self.url_input.textChanged.connect(self._on_url_changed)
        self.progress_updated.connect(self._update_progress_gui)
        self.show_ok_signal.connect(self._show_ok_button)

    @Slot(int)
    def _update_progress_gui(self, progress: int) -> None:
        self.progress_bar.setValue(progress)

    def _on_url_changed(self) -> None:
        url = self.url_input.text().strip()
        if url and ("bilibili.com/video/" in url or "b23.tv/" in url):
            self._fetch_video_info(url)

    def _fetch_video_info(self, url: str) -> None:
        def fetch():
            try:
                info = self._downloader.get_video_info(url)
                if info:
                    title = info.get("title", "Unknown")
                    size = info.get("size", "Unknown")
                    self.title_info.setText(f"TITLE: {title[:35]}..." if len(title) > 35 else f"TITLE: {title}")
                    self.size_info.setText(f"SIZE: {size}")
                    self.status_info.setText("STATUS: READY TO DOWNLOAD")
            except Exception:
                self.status_info.setText("STATUS: INVALID URL")

        Thread(target=fetch, daemon=True).start()

    def _start_download(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            self.status_info.setText("STATUS: ENTER URL FIRST")
            return

        if self._is_downloading:
            return

        self._is_downloading = True
        self.btn_download.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_info.setText("STATUS: DOWNLOADING...")

        def download():
            try:
                def progress_callback(progress: int):
                    self.progress_updated.emit(progress)
                
                success, file_path = self._downloader.download_audio_only(
                    url, 
                    progress_callback=progress_callback
                )
                
                if success and file_path and os.path.exists(file_path):
                    self.status_info.setText("STATUS: DOWNLOAD COMPLETE!")
                    self.progress_bar.setValue(100)
                    self.show_ok_signal.emit()
                    self.download_completed.emit(file_path)
                else:
                    self.status_info.setText("STATUS: DOWNLOAD FAILED")
                    self.btn_download.setEnabled(True)
                    
            except Exception as e:
                self.status_info.setText(f"STATUS: ERROR - {str(e)[:25]}")
                self.btn_download.setEnabled(True)
            finally:
                self._is_downloading = False

        Thread(target=download, daemon=True).start()

    def _show_ok_button(self) -> None:
        self.btn_download.hide()
        self.btn_cancel.hide()
        
        self.btn_ok = QPushButton("OK")
        self.btn_ok.setMinimumHeight(40)
        self.btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #4ECCA3;
                color: #000000;
                border: 3px solid #000000;
                padding: 10px 40px;
                font-family: "Press Start 2P", "Courier New", monospace;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #3DBD9A;
            }
        """)
        self.btn_ok.clicked.connect(self.close)
        
        parent_layout = self.btn_download.parent().layout()
        if parent_layout:
            parent_layout.addWidget(self.btn_ok)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.globalPosition().toPoint()
            window = self.windowHandle()
            if window is not None and window.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)
