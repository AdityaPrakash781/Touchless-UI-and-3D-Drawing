"""
Pop-out windows for GestureVLC:

1. HandPreviewWindow — Resizable, always-on-top window showing
   the live webcam feed with hand landmark overlay.

2. PictureInPictureWindow — Always-on-top mini video player
   with basic transport controls (like Zen browser PiP).
"""

import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QSizePolicy, QFrame, QComboBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QFont

from app.styles import COLORS


# ═════════════════════════════════════════════════════════════════
#  Hand Tracking Preview Window
# ═════════════════════════════════════════════════════════════════

class HandPreviewWindow(QWidget):
    """
    Resizable, always-on-top window displaying the webcam feed
    with hand landmarks drawn on top. Updated via set_frame().
    """
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hand Tracking Preview")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumSize(240, 180)
        self.resize(400, 300)
        self.setStyleSheet(f"background-color: {COLORS['bg_base']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(32)
        header.setStyleSheet(f"background: {COLORS['bg_secondary']};")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 0, 6, 0)
        h_layout.setSpacing(8)

        title = QLabel("HAND TRACKING")
        title.setStyleSheet(f"color: {COLORS['accent']}; font-size: 11px; font-weight: 700; letter-spacing: 0.06em;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; color: {COLORS['text_secondary']};
                font-size: 14px; font-weight: 700;
            }}
            QPushButton:hover {{ color: #f85149; }}
        """)
        btn_close.clicked.connect(self.close)
        h_layout.addWidget(btn_close)

        layout.addWidget(header)

        # Video feed label
        self._feed_label = QLabel("Waiting for webcam…")
        self._feed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._feed_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        self._feed_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._feed_label)

    def set_frame(self, q_image: QImage):
        """Update the displayed frame (called from main thread via signal)."""
        scaled = q_image.scaled(
            self._feed_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._feed_label.setPixmap(QPixmap.fromImage(scaled))

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


# ═════════════════════════════════════════════════════════════════
#  Picture-in-Picture Window (Pop-out Video)
# ═════════════════════════════════════════════════════════════════

class PictureInPictureWindow(QWidget):
    """
    Always-on-top mini video player window with basic controls.
    The VLC output is re-embedded into this window's video frame
    while PiP is active, and restored when closed.
    """
    closed = pyqtSignal()
    play_pause = pyqtSignal()
    seek_relative = pyqtSignal(int)  # delta ms
    volume_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GestureVLC — PiP")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # smaller taskbar footprint
        )
        self.setMinimumSize(360, 240)
        self.resize(520, 340)
        self.setStyleSheet(f"background-color: {COLORS['bg_base']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video frame — VLC will be re-embedded here
        self.video_frame = QFrame()
        self.video_frame.setObjectName("pipVideoFrame")
        self.video_frame.setStyleSheet("background-color: #0d0e12;")
        self.video_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        layout.addWidget(self.video_frame, stretch=1)

        # Control bar
        controls = QWidget()
        controls.setFixedHeight(48)
        controls.setStyleSheet(f"background: {COLORS['bg_secondary']};")
        c_layout = QHBoxLayout(controls)
        c_layout.setContentsMargins(12, 4, 12, 4)
        c_layout.setSpacing(10)

        self.btn_rw = QPushButton("⏪")
        self.btn_rw.setFixedSize(36, 36)
        self.btn_rw.setStyleSheet(self._ctrl_style())
        self.btn_rw.clicked.connect(lambda: self.seek_relative.emit(-10000))

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(40, 40)
        self.btn_play.setStyleSheet(self._play_style())
        self.btn_play.clicked.connect(self.play_pause.emit)

        self.btn_ff = QPushButton("⏩")
        self.btn_ff.setFixedSize(36, 36)
        self.btn_ff.setStyleSheet(self._ctrl_style())
        self.btn_ff.clicked.connect(lambda: self.seek_relative.emit(10000))

        self.time_label = QLabel("0:00")
        self.time_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
            font-size: 11px;
        """)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.valueChanged.connect(self.volume_changed.emit)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; color: {COLORS['text_secondary']};
                font-size: 14px;
            }}
            QPushButton:hover {{ color: #f85149; }}
        """)
        btn_close.clicked.connect(self.close)

        c_layout.addWidget(self.btn_rw)
        c_layout.addWidget(self.btn_play)
        c_layout.addWidget(self.btn_ff)
        c_layout.addSpacing(6)
        c_layout.addWidget(self.time_label)
        c_layout.addStretch()
        c_layout.addWidget(QLabel("🔊"))
        c_layout.addWidget(self.vol_slider)
        c_layout.addSpacing(6)
        c_layout.addWidget(btn_close)

        layout.addWidget(controls)

    def update_state(self, is_playing: bool, current_ms: int, total_ms: int):
        """Update play button icon and time display."""
        self.btn_play.setText("⏸" if is_playing else "▶")
        self.time_label.setText(f"{_fmt(current_ms)} / {_fmt(total_ms)}")

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    def _ctrl_style(self) -> str:
        return f"""
            QPushButton {{
                background: transparent; border: none;
                color: {COLORS['text_secondary']}; font-size: 16px;
            }}
            QPushButton:hover {{ color: {COLORS['text_accent']}; }}
        """

    def _play_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLORS['accent']}; border: 2px solid {COLORS['accent_hover']};
                border-radius: 20px; color: #2b1700; font-size: 18px; font-weight: 700;
            }}
            QPushButton:hover {{
                background: {COLORS['accent_hover']};
            }}
        """


def _fmt(ms: int) -> str:
    """Format milliseconds into M:SS or H:MM:SS."""
    if ms <= 0:
        return "0:00"
    total_secs = ms // 1000
    hours, remainder = divmod(total_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"
