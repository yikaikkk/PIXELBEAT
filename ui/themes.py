"""Pixeltune-inspired stylesheet."""

PIXEL_RETRO = """
QWidget {
    background-color: #1A1A2E;
    color: #FFFFFF;
    font-family: "Press Start 2P", "Courier New", monospace;
    font-size: 9px;
}

QFrame#appShell {
    background-color: #0F3460;
    border: 4px solid #000000;
}

QFrame#pixelShadow {
    background-color: #000000;
}

QFrame#titleBar {
    background-color: #1A1A2E;
    border: 0px;
}

QFrame#appIcon {
    background-color: #E94560;
    border: 2px solid #000000;
}

QFrame#displayFrame {
    background-color: #16213E;
    border: 4px solid #000000;
}

QFrame#artCard {
    background-color: #0F3460;
    border: 4px solid #000000;
}

QFrame#progressBox, QFrame#volumeBox, QFrame#playlistPanel {
    background-color: #1A1A2E;
    border: 4px solid #000000;
}

QFrame#playlistPanel {
    border-top: 4px solid #000000;
}

QLabel#brand {
    background-color: transparent;
    color: #E94560;
    font-size: 10px;
}

QLabel#trackTitle {
    background-color: transparent;
    color: #4ECCA3;
    font-size: 13px;
    line-height: 18px;
}

QLabel#artistText, QLabel#timeText, QLabel#mutedText {
    background-color: transparent;
    color: #95A5A6;
}

QLabel#accentText {
    background-color: transparent;
    color: #4ECCA3;
}

QSlider::groove:horizontal {
    border: 0px;
    height: 8px;
    background: #0F3460;
}

QSlider::sub-page:horizontal {
    background: #4ECCA3;
}

QSlider::add-page:horizontal {
    background: #0F3460;
}

QSlider::handle:horizontal {
    background: #E94560;
    border: 2px solid #000000;
    width: 12px;
    margin: -4px 0;
}

QListWidget {
    background: #1A1A2E;
    border: 0px;
    outline: none;
}

QListWidget::item {
    background: transparent;
    color: #FFFFFF;
    padding: 8px;
    border: 2px solid transparent;
}

QListWidget::item:selected {
    background: #0F3460;
    color: #4ECCA3;
    border: 2px solid #4ECCA3;
}

QScrollBar:vertical {
    background: #0F3460;
    width: 12px;
}

QScrollBar::handle:vertical {
    background: #E94560;
    border: 3px solid #1A1A2E;
    min-height: 20px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QSizeGrip {
    background: #0F3460;
    width: 14px;
    height: 14px;
}
"""
