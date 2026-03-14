#!/usr/bin/env python3
"""
GestureVLC — Cross-platform VLC Media Player with YouTube & Gesture Controls.

Run:
    python3 main.py

Requirements:
    - VLC media player installed on the system
    - Python packages: PyQt6, python-vlc, yt-dlp
"""

import sys
import os

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Wayland fix ──────────────────────────────────────────────────
# VLC's set_xwindow() requires an X11 window ID. On Wayland, PyQt6's
# winId() returns a Wayland surface which VLC can't render to.
# Force XCB (XWayland) so VLC embedding works on Wayland compositors.
# This MUST happen before any Qt imports create a QApplication.
if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland":
    os.environ["QT_QPA_PLATFORM"] = "xcb"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from app.main_window import MainWindow


def main():
    # High-DPI support
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("GestureVLC")
    app.setOrganizationName("GestureVLC")
    app.setApplicationVersion("0.1.0")

    # Set default font
    font = QFont("Inter", 11)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
