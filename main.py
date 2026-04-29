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
# VLC's set_xwindow() requires an X11 window ID. On Wayland:
# 1. PyQt6's winId() returns a Wayland surface — force XCB so it
#    gives us a real X11 window ID under XWayland.
# 2. VLC 3.0.x independently checks WAYLAND_DISPLAY and uses its
#    own Wayland plugin — bypassing set_xwindow() entirely.
#    We MUST unset WAYLAND_DISPLAY so VLC falls back to X11.
# This MUST happen before any Qt imports create a QApplication.
_is_wayland = bool(
    os.environ.get("WAYLAND_DISPLAY") or
    os.environ.get("XDG_SESSION_TYPE") == "wayland"
)
if _is_wayland:
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    # Save and unset WAYLAND_DISPLAY so VLC doesn't try to use Wayland
    _saved_wayland = os.environ.pop("WAYLAND_DISPLAY", None)
    # Ensure DISPLAY is set for XWayland
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":0"

# ── Preload native libraries before Qt ──────────────────────
# On Windows, PyQt6 can interfere with onnxruntime's DLL loading.
# Importing onnxruntime BEFORE PyQt6 avoids the conflict.
try:
    import onnxruntime  # noqa: F401
except ImportError:
    pass  # Will be handled gracefully by AirWritingEngine

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
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

    # Set application icon
    _root = os.path.dirname(os.path.abspath(__file__))
    _icon_path = os.path.join(_root, "assets", "play-button.png")
    if os.path.isfile(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
