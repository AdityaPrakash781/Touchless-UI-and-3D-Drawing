"""
GestureVLC — Main Window (Obsidian Cinematic Edition)

Central application window embedding VLC video playback,
YouTube search/URL integration, gesture controls, and 3D drawing.
Styled with Stitch MCP Obsidian Cinematic design system.

Air Writing: CNN-based character recognition from pinch-gesture drawing.
"""

import sys
import os
import time
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLineEdit, QPushButton, QLabel,
    QFrame, QScrollArea, QSizePolicy, QStatusBar,
    QApplication, QMessageBox, QComboBox, QGridLayout,
    QFileDialog, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QKeySequence, QShortcut, QFont, QIcon, QAction, QActionGroup

import vlc
from app.vlc_player import VLCPlayer
from app.youtube import StreamExtractor, SearchWorker, search_youtube
from app.controls import TransportBar
from app.file_browser import pick_video_file, get_recent_files
from app.styles import STYLESHEET, COLORS
from app.drawing import DrawingCanvas, FullscreenDrawingWindow
from app.popout_windows import HandPreviewWindow, PictureInPictureWindow
from app.air_writing import AirWritingEngine
from gesture.tracker import GestureTracker
from gesture.settings import (
    load_gesture_mapping, save_gesture_mapping, reset_gesture_mapping,
    AVAILABLE_ACTIONS, get_gesture_display_name, get_action_display_name,
)


class VideoFrame(QFrame):
    """
    Black frame that hosts the VLC video output.
    Double-click toggles fullscreen.
    """
    double_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("videoFrame")
        # Obsidian dark — no border-radius (breaks VLC rendering)
        self.setStyleSheet("background-color: #0d0e12;")
        self.setMinimumSize(640, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # CRITICAL: Ensure this widget gets a real native X11 window handle
        # Without this, winId() may return an unstable/invalid ID
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class SearchResultCard(QFrame):
    """A clickable card representing a single YouTube search result."""
    clicked = pyqtSignal(str, str)  # url, title

    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("resultCard")
        self.url = result.get("url", "")
        self.title = result.get("title", "Unknown")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Title
        title_label = QLabel(self.title)
        title_label.setObjectName("titleLabel")
        title_label.setWordWrap(True)
        font = title_label.font()
        font.setPointSize(12)
        font.setWeight(QFont.Weight.DemiBold)
        title_label.setFont(font)

        # Metadata row
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(16)

        channel = QLabel(result.get("channel", ""))
        channel.setObjectName("secondaryLabel")

        duration = QLabel(result.get("duration_str", ""))
        duration.setObjectName("secondaryLabel")

        views = result.get("view_count", 0)
        view_text = self._format_views(views)
        views_label = QLabel(view_text)
        views_label.setObjectName("secondaryLabel")

        meta_layout.addWidget(channel)
        meta_layout.addWidget(duration)
        meta_layout.addWidget(views_label)
        meta_layout.addStretch()

        layout.addWidget(title_label)
        layout.addLayout(meta_layout)

    def _format_views(self, count: int) -> str:
        if count <= 0:
            return ""
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M views"
        if count >= 1_000:
            return f"{count / 1_000:.1f}K views"
        return f"{count} views"

    def mousePressEvent(self, event):
        self.clicked.emit(self.url, self.title)
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """
    The main GestureVLC application window.
    
    Layout:
    ┌──────────────────────────────────────────┐
    │  [Menu Bar]                               │
    ├──────────────────┬───────────────────────┤
    │                  │  Sidebar (Tabs)         │
    │   VLC Video      │  ├─ YouTube             │
    │   Frame          │  │  URL bar + Search    │
    │                  │  │  Results list         │
    │                  │  ├─ Local Files          │
    │                  │  │  Open file / Recent   │
    ├──────────────────┴───────────────────────┤
    │  [Transport Bar: ◀◀ ▶/⏸ ▶▶ | seek | vol]  │
    ├──────────────────────────────────────────┤
    │  [Status Bar]                             │
    └──────────────────────────────────────────┘
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GestureVLC")
        self.setMinimumSize(1100, 700)
        self.resize(1380, 860)

        # VLC Player backend
        self.player = VLCPlayer()

        # Active threads
        self._stream_worker = None
        self._search_worker = None
        self._gesture_tracker = None
        self._gesture_mapping = load_gesture_mapping()
        self._gesture_combos = {}  # gesture_name -> QComboBox
        self._drawing_active = False
        self._last_draw_time = 0
        self._is_pinching = False

        # Air Writing Engine
        self._air_engine = AirWritingEngine()
        self._air_model_loaded = False
        self._recognize_timer = None  # Timer for delayed recognition after stroke ends

        # New feature windows
        self._pip_window = None
        self._closing_pip = False
        self._hand_preview = None
        self._fullscreen_draw = None
        self._loop_current = False
        self._always_on_top = False

        self._setup_ui()
        self._setup_shortcuts()
        self._start_update_timer()
        self._load_air_writing_model()

        # Apply stylesheet
        self.setStyleSheet(STYLESHEET)

    # ── UI Construction ──────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Brand header ──
        header = QWidget()
        header.setStyleSheet(f"background-color: {COLORS['bg_secondary']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 10, 24, 10)
        header_layout.setSpacing(12)

        brand = QLabel("GESTUREVLC")
        brand.setObjectName("brandLabel")
        header_layout.addWidget(brand)

        header_layout.addStretch()

        self.now_playing = QLabel("")
        self.now_playing.setObjectName("nowPlaying")
        self.now_playing.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.now_playing)

        # Hand preview toggle button in header
        self.btn_hand_preview = QPushButton("Hand Preview")
        self.btn_hand_preview.setCheckable(True)
        self.btn_hand_preview.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid {COLORS['border_visible']};
                border-radius: 8px; color: {COLORS['text_secondary']};
                padding: 4px 12px; font-size: 11px; font-weight: 600;
            }}
            QPushButton:hover {{ border-color: {COLORS['accent']}; color: {COLORS['text_accent']}; }}
            QPushButton:checked {{ background: {COLORS['accent']}; color: #2b1700; border-color: {COLORS['accent']}; }}
        """)
        self.btn_hand_preview.toggled.connect(self._toggle_hand_preview)
        header_layout.addWidget(self.btn_hand_preview)

        # PiP toggle button in header
        self.btn_pip = QPushButton("PiP")
        self.btn_pip.setCheckable(True)
        self.btn_pip.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid {COLORS['border_visible']};
                border-radius: 8px; color: {COLORS['text_secondary']};
                padding: 4px 12px; font-size: 11px; font-weight: 600;
            }}
            QPushButton:hover {{ border-color: {COLORS['accent']}; color: {COLORS['text_accent']}; }}
            QPushButton:checked {{ background: {COLORS['accent']}; color: #2b1700; border-color: {COLORS['accent']}; }}
        """)
        self.btn_pip.toggled.connect(self._toggle_pip)
        header_layout.addWidget(self.btn_pip)

        root_layout.addWidget(header)

        # ── Main content area (video + sidebar) ──
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(20, 12, 20, 8)
        content_layout.setSpacing(16)

        # Video frame
        self.video_frame = VideoFrame()
        self.video_frame.double_clicked.connect(self._toggle_fullscreen)
        content_layout.addWidget(self.video_frame, stretch=7)

        # Sidebar
        sidebar = self._build_sidebar()
        content_layout.addWidget(sidebar, stretch=3)

        root_layout.addLayout(content_layout, stretch=1)

        # ── Transport bar ──
        self.transport = TransportBar()
        self.transport.play_pause_clicked.connect(self._on_play_pause)
        self.transport.stop_clicked.connect(self._on_stop)
        self.transport.seek_requested.connect(self._on_seek)
        self.transport.rewind_clicked.connect(lambda: self.player.seek_relative(-10000))
        self.transport.forward_clicked.connect(lambda: self.player.seek_relative(10000))
        self.transport.volume_changed.connect(self.player.set_volume)
        self.transport.mute_clicked.connect(self._on_mute)
        self.transport.speed_changed.connect(self._on_speed_change)
        self.transport.fullscreen_clicked.connect(self._toggle_fullscreen)
        root_layout.addWidget(self.transport)

        # ── Status bar ──
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — Open a file or paste a YouTube link")

        self._setup_menu_bar()

        # Embed VLC into the video frame
        # Use a longer delay to ensure the window is fully mapped on XWayland
        QTimer.singleShot(500, self._embed_vlc)

    def _embed_vlc(self):
        """Attach the VLC player output to the video frame widget."""
        # Process pending events to ensure the widget is fully realized
        QApplication.processEvents()
        win_id = int(self.video_frame.winId())
        self.player.set_window(win_id)
        self.player.set_volume(80)
        self.status_bar.showMessage(
            f"Ready — VLC embedded (Window ID: {win_id})"
        )

    def _build_sidebar(self) -> QTabWidget:
        """Build the sidebar tab widget with YouTube and Local tabs."""
        tabs = QTabWidget()
        tabs.setMinimumWidth(360)
        tabs.setMaximumWidth(460)

        # ── YouTube Tab ──
        yt_widget = QWidget()
        yt_layout = QVBoxLayout(yt_widget)
        yt_layout.setContentsMargins(16, 20, 16, 16)
        yt_layout.setSpacing(14)

        # URL input
        url_label = QLabel("YOUTUBE URL")
        url_label.setObjectName("titleLabel")
        yt_layout.addWidget(url_label)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube URL here…")
        self.url_input.returnPressed.connect(self._play_youtube_url)

        self.btn_play_url = QPushButton("▶ Play")
        self.btn_play_url.setObjectName("accentButton")
        self.btn_play_url.setFixedWidth(80)
        self.btn_play_url.clicked.connect(self._play_youtube_url)

        url_row.addWidget(self.url_input)
        url_row.addWidget(self.btn_play_url)
        yt_layout.addLayout(url_row)

        # Separator
        sep1 = QFrame()
        sep1.setObjectName("separator")
        sep1.setFrameShape(QFrame.Shape.HLine)
        yt_layout.addWidget(sep1)

        # Search input
        search_label = QLabel("SEARCH")
        search_label.setObjectName("titleLabel")
        yt_layout.addWidget(search_label)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for videos…")
        self.search_input.returnPressed.connect(self._search_youtube)

        self.btn_search = QPushButton("Search")
        self.btn_search.setObjectName("accentButton")
        self.btn_search.setFixedWidth(80)
        self.btn_search.clicked.connect(self._search_youtube)

        search_row.addWidget(self.search_input)
        search_row.addWidget(self.btn_search)
        yt_layout.addLayout(search_row)

        # Search results scroll area
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(6)
        self.results_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.results_container)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        yt_layout.addWidget(scroll, stretch=1)

        # Loading label
        self.yt_status = QLabel("")
        self.yt_status.setObjectName("statusLabel")
        self.yt_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        yt_layout.addWidget(self.yt_status)

        tabs.addTab(yt_widget, "YOUTUBE")

        # ── Local Files Tab ──
        local_widget = QWidget()
        local_layout = QVBoxLayout(local_widget)
        local_layout.setContentsMargins(16, 20, 16, 16)
        local_layout.setSpacing(14)

        open_label = QLabel("OPEN FILE")
        open_label.setObjectName("titleLabel")
        local_layout.addWidget(open_label)

        self.btn_open_file = QPushButton("Browse Files…")
        self.btn_open_file.setObjectName("accentButton")
        self.btn_open_file.setFixedHeight(44)
        self.btn_open_file.clicked.connect(self._open_local_file)
        local_layout.addWidget(self.btn_open_file)

        # Separator
        sep2 = QFrame()
        sep2.setObjectName("separator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        local_layout.addWidget(sep2)

        # Recent files
        recent_label = QLabel("RECENT")
        recent_label.setObjectName("titleLabel")
        local_layout.addWidget(recent_label)

        self.recent_container = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(4)

        recent_scroll = QScrollArea()
        recent_scroll.setWidgetResizable(True)
        recent_scroll.setWidget(self.recent_container)
        recent_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        local_layout.addWidget(recent_scroll, stretch=1)

        tabs.addTab(local_widget, "LOCAL")

        # ── Gesture Controls Tab ──
        gesture_widget = QWidget()
        gesture_layout = QVBoxLayout(gesture_widget)
        gesture_layout.setContentsMargins(16, 20, 16, 16)
        gesture_layout.setSpacing(12)

        gesture_title = QLabel("GESTURE CONTROLS")
        gesture_title.setObjectName("titleLabel")
        gesture_layout.addWidget(gesture_title)

        gesture_desc = QLabel(
            "Use hand gestures to control playback.\n"
            "Requires a webcam and trained model."
        )
        gesture_desc.setObjectName("secondaryLabel")
        gesture_desc.setWordWrap(True)
        gesture_layout.addWidget(gesture_desc)

        self.btn_gesture_toggle = QPushButton("Start Gesture Control")
        self.btn_gesture_toggle.setObjectName("accentButton")
        self.btn_gesture_toggle.setFixedHeight(44)
        self.btn_gesture_toggle.clicked.connect(self._toggle_gesture_tracking)
        gesture_layout.addWidget(self.btn_gesture_toggle)

        self.gesture_status = QLabel("Status: Inactive")
        self.gesture_status.setObjectName("statusLabel")
        gesture_layout.addWidget(self.gesture_status)

        # Separator
        sep3 = QFrame()
        sep3.setObjectName("separator")
        sep3.setFrameShape(QFrame.Shape.HLine)
        gesture_layout.addWidget(sep3)

        # ── Customizable gesture mapping ──
        gesture_map_label = QLabel("CUSTOMIZE MAPPING")
        gesture_map_label.setObjectName("titleLabel")
        gesture_layout.addWidget(gesture_map_label)

        # Scrollable area for gesture mappings
        gesture_scroll_widget = QWidget()
        gesture_scroll_layout = QVBoxLayout(gesture_scroll_widget)
        gesture_scroll_layout.setContentsMargins(0, 0, 0, 0)
        gesture_scroll_layout.setSpacing(4)

        action_keys = list(AVAILABLE_ACTIONS.keys())
        action_labels = [AVAILABLE_ACTIONS[k] for k in action_keys]

        gestures_in_order = [
            "palm", "fist", "like", "dislike", "stop", "peace",
            "ok", "one", "mute", "rock", "two_up", "call", "three", "four",
        ]

        self._gesture_combos = {}
        for gesture_name in gestures_in_order:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(8)

            label = QLabel(get_gesture_display_name(gesture_name))
            label.setFixedWidth(100)
            label.setObjectName("secondaryLabel")

            arrow = QLabel("→")
            arrow.setFixedWidth(16)
            arrow.setObjectName("secondaryLabel")

            combo = QComboBox()
            combo.addItems(action_labels)
            # Set current selection from mapping
            current_action = self._gesture_mapping.get(gesture_name, "none")
            if current_action in action_keys:
                combo.setCurrentIndex(action_keys.index(current_action))
            combo.setProperty("gesture_name", gesture_name)

            row_layout.addWidget(label)
            row_layout.addWidget(arrow)
            row_layout.addWidget(combo, stretch=1)

            self._gesture_combos[gesture_name] = combo
            gesture_scroll_layout.addWidget(row_widget)

        gesture_scroll = QScrollArea()
        gesture_scroll.setWidgetResizable(True)
        gesture_scroll.setWidget(gesture_scroll_widget)
        gesture_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        gesture_scroll.setMaximumHeight(280)
        gesture_layout.addWidget(gesture_scroll)

        # Save / Reset buttons
        btn_row = QHBoxLayout()
        btn_save = QPushButton("Save Mapping")
        btn_save.setObjectName("accentButton")
        btn_save.clicked.connect(self._save_gesture_mapping)

        btn_reset = QPushButton("Reset Defaults")
        btn_reset.clicked.connect(self._reset_gesture_mapping)

        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_reset)
        gesture_layout.addLayout(btn_row)

        # Gesture log
        sep4 = QFrame()
        sep4.setObjectName("separator")
        sep4.setFrameShape(QFrame.Shape.HLine)
        gesture_layout.addWidget(sep4)

        gesture_log_label = QLabel("RECENT GESTURES")
        gesture_log_label.setObjectName("titleLabel")
        gesture_layout.addWidget(gesture_log_label)

        self.gesture_log = QLabel("No gestures detected yet")
        self.gesture_log.setObjectName("secondaryLabel")
        self.gesture_log.setWordWrap(True)
        gesture_layout.addWidget(self.gesture_log)

        gesture_layout.addStretch()

        tabs.addTab(gesture_widget, "GESTURES")

        # ── 3D Drawing Tab ──
        drawing_widget = QWidget()
        drawing_layout = QVBoxLayout(drawing_widget)
        drawing_layout.setContentsMargins(16, 20, 16, 16)
        drawing_layout.setSpacing(12)

        drawing_title = QLabel("AIR DRAWING & WRITING")
        drawing_title.setObjectName("titleLabel")
        drawing_layout.addWidget(drawing_title)

        drawing_desc = QLabel(
            "Pinch your thumb and index finger together to draw.\n"
            "Release to stop. Characters are recognized automatically."
        )
        drawing_desc.setObjectName("secondaryLabel")
        drawing_layout.addWidget(drawing_desc)

        # Drawing Status Indicator
        status_row = QHBoxLayout()
        self.drawing_indicator = QLabel("TRACKING DISABLED")
        self.drawing_indicator.setStyleSheet("color: #f85149; font-weight: 700; font-size: 13px; letter-spacing: 0.05em;")
        status_row.addWidget(self.drawing_indicator)

        self.btn_draw_toggle_tracking = QPushButton("Start Tracking")
        self.btn_draw_toggle_tracking.setFixedWidth(150)
        self.btn_draw_toggle_tracking.clicked.connect(self._toggle_gesture_tracking)
        status_row.addWidget(self.btn_draw_toggle_tracking, alignment=Qt.AlignmentFlag.AlignRight)

        drawing_layout.addLayout(status_row)

        # Air Writing Model Status
        self.air_writing_status = QLabel("")
        self.air_writing_status.setObjectName("secondaryLabel")
        drawing_layout.addWidget(self.air_writing_status)

        # The Canvas
        self.canvas = DrawingCanvas()
        drawing_layout.addWidget(self.canvas, stretch=1)

        # Recognized text display
        text_row = QHBoxLayout()
        text_row.setSpacing(8)

        text_label = QLabel("TEXT:")
        text_label.setObjectName("titleLabel")
        text_label.setFixedWidth(50)
        text_row.addWidget(text_label)

        self.recognized_text_display = QLabel("")
        self.recognized_text_display.setStyleSheet(
            f"color: {COLORS['text_accent']}; font-family: 'JetBrains Mono', monospace; "
            f"font-size: 16px; font-weight: 600; padding: 4px 8px; "
            f"background: {COLORS['bg_tertiary']}; border-radius: 8px;"
        )
        self.recognized_text_display.setMinimumHeight(32)
        text_row.addWidget(self.recognized_text_display, stretch=1)

        drawing_layout.addLayout(text_row)

        # Controls (split into two rows for readability in narrow sidebar)
        draw_btn_grid = QGridLayout()
        draw_btn_grid.setHorizontalSpacing(8)
        draw_btn_grid.setVerticalSpacing(8)

        self.btn_clear_canvas = QPushButton("Clear Canvas")
        self.btn_clear_canvas.setToolTip("Clear drawing and recognized text")
        self.btn_clear_canvas.setMinimumHeight(40)
        self.btn_clear_canvas.clicked.connect(self._clear_drawing_and_text)
        draw_btn_grid.addWidget(self.btn_clear_canvas, 0, 0)

        self.btn_undo_canvas = QPushButton("Undo Stroke")
        self.btn_undo_canvas.setToolTip("Undo the last stroke")
        self.btn_undo_canvas.setMinimumHeight(40)
        self.btn_undo_canvas.clicked.connect(self.canvas.undo)
        draw_btn_grid.addWidget(self.btn_undo_canvas, 0, 1)

        self.btn_recognize = QPushButton("Recognize Text")
        self.btn_recognize.setToolTip("Recognize current drawing now")
        self.btn_recognize.setMinimumHeight(40)
        self.btn_recognize.clicked.connect(self._force_recognize)
        draw_btn_grid.addWidget(self.btn_recognize, 0, 2)

        self.btn_backspace = QPushButton("Backspace")
        self.btn_backspace.setToolTip("Delete last recognized character")
        self.btn_backspace.setMinimumHeight(40)
        self.btn_backspace.clicked.connect(self._air_writing_backspace)
        draw_btn_grid.addWidget(self.btn_backspace, 1, 0)

        self.btn_move_mode = QPushButton("Move Paths")
        self.btn_move_mode.setToolTip("Toggle move mode to drag strokes")
        self.btn_move_mode.setCheckable(True)
        self.btn_move_mode.setMinimumHeight(40)
        self.btn_move_mode.toggled.connect(self.canvas.set_move_mode)
        draw_btn_grid.addWidget(self.btn_move_mode, 1, 1)

        self.btn_fullscreen_draw = QPushButton("Fullscreen Canvas")
        self.btn_fullscreen_draw.setObjectName("accentButton")
        self.btn_fullscreen_draw.setToolTip("Open drawing canvas in fullscreen")
        self.btn_fullscreen_draw.setMinimumHeight(40)
        self.btn_fullscreen_draw.clicked.connect(self._open_fullscreen_drawing)
        draw_btn_grid.addWidget(self.btn_fullscreen_draw, 1, 2)

        drawing_layout.addLayout(draw_btn_grid)

        tabs.addTab(drawing_widget, "AIR DRAW")

        # Populate recent files
        self._refresh_recent_files()

        return tabs

    # ── Menu Bar ─────────────────────────────────────────────────────

    def _setup_menu_bar(self):
        """Build VLC-style top menus for media, playback, audio, video, and tools."""
        menubar = self.menuBar()

        # Media
        media_menu = menubar.addMenu("Media")

        action_open_file = QAction("Open File...", self)
        action_open_file.setShortcut("Ctrl+O")
        action_open_file.triggered.connect(self._open_local_file)
        media_menu.addAction(action_open_file)

        action_open_url = QAction("Open Network Stream...", self)
        action_open_url.setShortcut("Ctrl+L")
        action_open_url.triggered.connect(self._open_network_url_dialog)
        media_menu.addAction(action_open_url)

        media_menu.addSeparator()

        action_snapshot = QAction("Take Snapshot...", self)
        action_snapshot.setShortcut("Shift+S")
        action_snapshot.triggered.connect(self._save_snapshot)
        media_menu.addAction(action_snapshot)

        media_menu.addSeparator()

        action_quit = QAction("Quit", self)
        action_quit.setShortcut("Ctrl+Q")
        action_quit.triggered.connect(self.close)
        media_menu.addAction(action_quit)

        # Playback
        playback_menu = menubar.addMenu("Playback")

        action_play_pause = QAction("Play/Pause", self)
        action_play_pause.setShortcut("Space")
        action_play_pause.triggered.connect(self._on_play_pause)
        playback_menu.addAction(action_play_pause)

        action_stop = QAction("Stop", self)
        action_stop.setShortcut("S")
        action_stop.triggered.connect(self._on_stop)
        playback_menu.addAction(action_stop)

        playback_menu.addSeparator()

        action_back_10 = QAction("Jump Backward 10s", self)
        action_back_10.setShortcut("Left")
        action_back_10.triggered.connect(lambda: self.player.seek_relative(-10000))
        playback_menu.addAction(action_back_10)

        action_fwd_10 = QAction("Jump Forward 10s", self)
        action_fwd_10.setShortcut("Right")
        action_fwd_10.triggered.connect(lambda: self.player.seek_relative(10000))
        playback_menu.addAction(action_fwd_10)

        action_back_30 = QAction("Jump Backward 30s", self)
        action_back_30.setShortcut("Shift+Left")
        action_back_30.triggered.connect(lambda: self.player.seek_relative(-30000))
        playback_menu.addAction(action_back_30)

        action_fwd_30 = QAction("Jump Forward 30s", self)
        action_fwd_30.setShortcut("Shift+Right")
        action_fwd_30.triggered.connect(lambda: self.player.seek_relative(30000))
        playback_menu.addAction(action_fwd_30)

        playback_menu.addSeparator()

        action_speed_up = QAction("Faster", self)
        action_speed_up.setShortcut("]")
        action_speed_up.triggered.connect(lambda: self.player.cycle_speed(forward=True))
        playback_menu.addAction(action_speed_up)

        action_speed_down = QAction("Slower", self)
        action_speed_down.setShortcut("[")
        action_speed_down.triggered.connect(lambda: self.player.cycle_speed(forward=False))
        playback_menu.addAction(action_speed_down)

        action_speed_normal = QAction("Normal Speed", self)
        action_speed_normal.setShortcut("=")
        action_speed_normal.triggered.connect(lambda: self.player.set_rate(1.0))
        playback_menu.addAction(action_speed_normal)

        playback_menu.addSeparator()

        action_loop_current = QAction("Loop Current Media", self)
        action_loop_current.setCheckable(True)
        action_loop_current.toggled.connect(self._toggle_loop_current)
        playback_menu.addAction(action_loop_current)

        # Audio
        audio_menu = menubar.addMenu("Audio")

        action_mute = QAction("Mute", self)
        action_mute.setShortcut("M")
        action_mute.triggered.connect(self._on_mute)
        audio_menu.addAction(action_mute)

        action_vol_up = QAction("Volume Up", self)
        action_vol_up.setShortcut("Up")
        action_vol_up.triggered.connect(lambda: self._adjust_volume(5))
        audio_menu.addAction(action_vol_up)

        action_vol_down = QAction("Volume Down", self)
        action_vol_down.setShortcut("Down")
        action_vol_down.triggered.connect(lambda: self._adjust_volume(-5))
        audio_menu.addAction(action_vol_down)

        audio_menu.addSeparator()
        self.audio_tracks_menu = audio_menu.addMenu("Audio Track")
        self.audio_tracks_menu.aboutToShow.connect(self._populate_audio_tracks_menu)

        # Video
        video_menu = menubar.addMenu("Video")

        action_fullscreen = QAction("Fullscreen", self)
        action_fullscreen.setShortcut("F")
        action_fullscreen.triggered.connect(self._toggle_fullscreen)
        video_menu.addAction(action_fullscreen)

        aspect_menu = video_menu.addMenu("Aspect Ratio")
        aspect_group = QActionGroup(self)
        aspect_group.setExclusive(True)
        aspect_options = [
            ("Default", ""),
            ("16:9", "16:9"),
            ("4:3", "4:3"),
            ("1:1", "1:1"),
            ("21:9", "21:9"),
        ]
        for label, ratio in aspect_options:
            action = QAction(label, self)
            action.setCheckable(True)
            if ratio == "":
                action.setChecked(True)
            action.triggered.connect(lambda checked, r=ratio, l=label: self._set_aspect_ratio(r, l))
            aspect_group.addAction(action)
            aspect_menu.addAction(action)

        crop_menu = video_menu.addMenu("Crop")
        crop_group = QActionGroup(self)
        crop_group.setExclusive(True)
        crop_options = [
            ("None", ""),
            ("16:9", "16:9"),
            ("4:3", "4:3"),
            ("1:1", "1:1"),
            ("21:9", "21:9"),
        ]
        for label, crop in crop_options:
            action = QAction(label, self)
            action.setCheckable(True)
            if crop == "":
                action.setChecked(True)
            action.triggered.connect(lambda checked, c=crop, l=label: self._set_crop(c, l))
            crop_group.addAction(action)
            crop_menu.addAction(action)

        video_menu.addSeparator()
        self.subtitle_tracks_menu = video_menu.addMenu("Subtitle Track")
        self.subtitle_tracks_menu.aboutToShow.connect(self._populate_subtitle_tracks_menu)

        # View
        view_menu = menubar.addMenu("View")

        action_pip = QAction("Picture-in-Picture", self)
        action_pip.setCheckable(True)
        action_pip.toggled.connect(lambda checked: self.btn_pip.setChecked(checked))
        self.btn_pip.toggled.connect(action_pip.setChecked)
        view_menu.addAction(action_pip)

        action_hand_preview = QAction("Hand Preview", self)
        action_hand_preview.setCheckable(True)
        action_hand_preview.toggled.connect(lambda checked: self.btn_hand_preview.setChecked(checked))
        self.btn_hand_preview.toggled.connect(action_hand_preview.setChecked)
        view_menu.addAction(action_hand_preview)

        action_always_on_top = QAction("Always On Top", self)
        action_always_on_top.setCheckable(True)
        action_always_on_top.toggled.connect(self._toggle_always_on_top)
        view_menu.addAction(action_always_on_top)

        # Tools
        tools_menu = menubar.addMenu("Tools")

        action_media_info = QAction("Media Information", self)
        action_media_info.triggered.connect(self._show_media_info)
        tools_menu.addAction(action_media_info)

    def _open_network_url_dialog(self):
        """Prompt for a URL and play it directly in VLC."""
        url, ok = QInputDialog.getText(self, "Open Network Stream", "Enter media URL:")
        if not ok:
            return
        url = url.strip()
        if not url:
            return
        self.player.play(url)
        self.now_playing.setText(f"▶ {url}")
        self.status_bar.showMessage("Playing network stream")

    def _save_snapshot(self):
        """Save a frame snapshot to an image file."""
        if not self.player.has_media():
            self.status_bar.showMessage("No media loaded for snapshot")
            return

        default_name = f"vlc_snapshot_{int(time.time())}.png"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Snapshot",
            str(Path.home() / default_name),
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)",
        )
        if not path:
            return

        ok = self.player.take_snapshot(path)
        if ok:
            self.status_bar.showMessage(f"Snapshot saved: {path}")
        else:
            self.status_bar.showMessage("Snapshot failed")

    def _toggle_loop_current(self, enabled: bool):
        """Toggle looping for the currently loaded media item."""
        self._loop_current = enabled
        self.status_bar.showMessage("Loop current media: ON" if enabled else "Loop current media: OFF")

    def _set_aspect_ratio(self, ratio: str, label: str):
        """Apply selected aspect ratio."""
        self.player.set_aspect_ratio(ratio)
        self.status_bar.showMessage(f"Aspect ratio: {label}")

    def _set_crop(self, crop: str, label: str):
        """Apply selected crop mode."""
        self.player.set_crop(crop)
        self.status_bar.showMessage(f"Crop: {label}")

    def _populate_audio_tracks_menu(self):
        """Rebuild audio tracks submenu based on current media."""
        self.audio_tracks_menu.clear()
        tracks = self.player.get_audio_tracks()
        if not tracks:
            action = QAction("No audio tracks", self)
            action.setEnabled(False)
            self.audio_tracks_menu.addAction(action)
            return

        current = self.player.get_current_audio_track()
        group = QActionGroup(self)
        group.setExclusive(True)
        for track_id, label in tracks:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(track_id == current)
            action.triggered.connect(lambda checked, tid=track_id: self.player.set_audio_track(tid))
            group.addAction(action)
            self.audio_tracks_menu.addAction(action)

    def _populate_subtitle_tracks_menu(self):
        """Rebuild subtitle tracks submenu based on current media."""
        self.subtitle_tracks_menu.clear()
        tracks = self.player.get_subtitle_tracks()
        if not tracks:
            action = QAction("No subtitle tracks", self)
            action.setEnabled(False)
            self.subtitle_tracks_menu.addAction(action)
            return

        current = self.player.get_current_subtitle_track()
        group = QActionGroup(self)
        group.setExclusive(True)
        for track_id, label in tracks:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(track_id == current)
            action.triggered.connect(lambda checked, tid=track_id: self.player.set_subtitle_track(tid))
            group.addAction(action)
            self.subtitle_tracks_menu.addAction(action)

    def _toggle_always_on_top(self, enabled: bool):
        """Toggle top-most window mode."""
        self._always_on_top = enabled
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        self.show()
        self.status_bar.showMessage("Always on top: ON" if enabled else "Always on top: OFF")

    def _show_media_info(self):
        """Show current media playback diagnostics."""
        state = self.player.media_player.get_state()
        state_name = state.name if hasattr(state, "name") else str(state)
        info = (
            f"State: {state_name}\n"
            f"Time: {self.player.get_time() / 1000:.1f}s\n"
            f"Duration: {self.player.get_duration() / 1000:.1f}s\n"
            f"Volume: {self.player.get_volume()}%\n"
            f"Muted: {'Yes' if self.player.is_muted() else 'No'}\n"
            f"Speed: {self.player.get_rate():.2f}x\n"
            f"Loop current: {'On' if self._loop_current else 'Off'}"
        )
        QMessageBox.information(self, "Media Information", info)

    # ── YouTube Actions ──────────────────────────────────────────────

    def _play_youtube_url(self):
        """Extract and play a YouTube URL from the URL input field."""
        url = self.url_input.text().strip()
        if not url:
            self.status_bar.showMessage("⚠ Please enter a YouTube URL")
            return

        self._set_youtube_loading(True, "Extracting stream…")
        self.btn_play_url.setEnabled(False)

        self._stream_worker = StreamExtractor(url)
        self._stream_worker.finished.connect(self._on_stream_ready)
        self._stream_worker.error.connect(self._on_stream_error)
        self._stream_worker.progress.connect(
            lambda msg: self.status_bar.showMessage(msg)
        )
        self._stream_worker.start()

    def _on_stream_ready(self, stream_url: str):
        """Play the extracted stream URL in VLC."""
        self.player.play(stream_url)
        title = self.url_input.text().strip()
        self.now_playing.setText(f"▶ {title}")
        self.status_bar.showMessage("Playing YouTube video (ad-free)")
        self._set_youtube_loading(False)
        self.btn_play_url.setEnabled(True)

    def _on_stream_error(self, error_msg: str):
        """Handle stream extraction errors."""
        self.status_bar.showMessage(f"❌ Error: {error_msg}")
        self._set_youtube_loading(False)
        self.btn_play_url.setEnabled(True)
        QMessageBox.warning(self, "YouTube Error",
                          f"Could not extract video stream:\n{error_msg}")

    def _search_youtube(self):
        """Search YouTube using the search input."""
        query = self.search_input.text().strip()
        if not query:
            self.status_bar.showMessage("⚠ Please enter a search query")
            return

        self._set_youtube_loading(True, f"Searching '{query}'…")
        self.btn_search.setEnabled(False)

        self._search_worker = SearchWorker(query, max_results=10)
        self._search_worker.finished.connect(self._on_search_results)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.progress.connect(
            lambda msg: self.status_bar.showMessage(msg)
        )
        self._search_worker.start()

    def _on_search_results(self, results: list):
        """Display search results in the sidebar."""
        self._clear_results()

        if not results:
            self.status_bar.showMessage("No results found")
            self._set_youtube_loading(False)
            self.yt_status.setText("No results found")
            self.btn_search.setEnabled(True)
            return

        for result in results:
            card = SearchResultCard(result)
            card.clicked.connect(self._play_search_result)
            self.results_layout.insertWidget(
                self.results_layout.count() - 1, card  # Before the stretch
            )

        self.status_bar.showMessage(f"Found {len(results)} results")
        self._set_youtube_loading(False)
        self.btn_search.setEnabled(True)

    def _on_search_error(self, error_msg: str):
        """Handle search errors."""
        self.status_bar.showMessage(f"❌ Search error: {error_msg}")
        self._set_youtube_loading(False)
        self.btn_search.setEnabled(True)

    def _play_search_result(self, url: str, title: str):
        """Play a video from the search results."""
        self.url_input.setText(url)
        self.now_playing.setText(f"▶ Loading: {title}")
        self._set_youtube_loading(True, f"Loading: {title}")

        self._stream_worker = StreamExtractor(url)
        self._stream_worker.finished.connect(
            lambda stream_url: self._on_result_stream_ready(stream_url, title)
        )
        self._stream_worker.error.connect(self._on_stream_error)
        self._stream_worker.start()

    def _on_result_stream_ready(self, stream_url: str, title: str):
        """Play the extracted stream from a search result."""
        self.player.play(stream_url)
        self.now_playing.setText(f"▶ {title}")
        self.status_bar.showMessage(f"Playing: {title} (ad-free)")
        self._set_youtube_loading(False)

    def _set_youtube_loading(self, loading: bool, message: str = ""):
        """Show or hide the YouTube loading indicator."""
        if loading:
            self.yt_status.setText(f"⏳ {message}")
        else:
            self.yt_status.setText("")

    def _clear_results(self):
        """Remove all search result cards."""
        while self.results_layout.count() > 1:  # Keep the stretch
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── Local File Actions ───────────────────────────────────────────

    def _open_local_file(self):
        """Open a local video file via file dialog."""
        path = pick_video_file(self)
        if path:
            self.player.play(path)
            filename = os.path.basename(path)
            self.now_playing.setText(f"▶ {filename}")
            self.status_bar.showMessage(f"Playing: {filename}")
            self._refresh_recent_files()

    def _play_recent_file(self, path: str):
        """Play a file from the recent files list."""
        if os.path.exists(path):
            self.player.play(path)
            filename = os.path.basename(path)
            self.now_playing.setText(f"▶ {filename}")
            self.status_bar.showMessage(f"Playing: {filename}")
        else:
            self.status_bar.showMessage(f"⚠ File not found: {path}")

    def _refresh_recent_files(self):
        """Refresh the recent files list in the sidebar."""
        # Clear existing items
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        recent = get_recent_files(10)
        if not recent:
            empty_label = QLabel("No recent files")
            empty_label.setObjectName("secondaryLabel")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.recent_layout.addWidget(empty_label)
            return

        for path in recent:
            filename = os.path.basename(path)
            btn = QPushButton(filename)
            btn.setToolTip(path)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 10px 14px;
                    background: {COLORS['bg_tertiary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 12px;
                    color: {COLORS['text_primary']};
                    font-size: 12px;
                    letter-spacing: 0.01em;
                }}
                QPushButton:hover {{
                    background: {COLORS['bg_hover']};
                    border-color: {COLORS['accent']};
                    color: {COLORS['text_accent']};
                }}
            """)
            # Capture path in closure
            btn.clicked.connect(lambda checked, p=path: self._play_recent_file(p))
            self.recent_layout.addWidget(btn)

        self.recent_layout.addStretch()

    # ── Transport Control Handlers ───────────────────────────────────

    def _on_play_pause(self):
        self.player.toggle_play_pause()

    def _on_stop(self):
        self.player.stop()
        self.now_playing.setText("")
        self.status_bar.showMessage("Stopped")

    def _on_seek(self, position: float):
        self.player.seek(position)

    def _on_mute(self):
        self.player.toggle_mute()
        self.transport.set_muted_state(self.player.is_muted())

    def _on_speed_change(self, rate: float):
        self.player.set_rate(rate)
        self.status_bar.showMessage(f"Playback speed: {rate}x")

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # ── Keyboard Shortcuts ───────────────────────────────────────────

    def _setup_shortcuts(self):
        """Register global keyboard shortcuts."""
        shortcuts = {
            "Space": self._on_play_pause,
            "F": self._toggle_fullscreen,
            "Escape": lambda: self.showNormal() if self.isFullScreen() else None,
            "Left": lambda: self.player.seek_relative(-10000),
            "Right": lambda: self.player.seek_relative(10000),
            "Shift+Left": lambda: self.player.seek_relative(-30000),
            "Shift+Right": lambda: self.player.seek_relative(30000),
            "Up": lambda: self._adjust_volume(5),
            "Down": lambda: self._adjust_volume(-5),
            "M": self._on_mute,
            "S": self._on_stop,
            "Ctrl+O": self._open_local_file,
            "Ctrl+L": self._open_network_url_dialog,
            "]": lambda: self.player.cycle_speed(forward=True),
            "[": lambda: self.player.cycle_speed(forward=False),
            "=": lambda: self.player.set_rate(1.0),
            "Shift+S": self._save_snapshot,
        }

        for key_seq, callback in shortcuts.items():
            shortcut = QShortcut(QKeySequence(key_seq), self)
            shortcut.activated.connect(callback)

    def _adjust_volume(self, delta: int):
        """Adjust volume by delta percent."""
        current = self.player.get_volume()
        new_vol = max(0, min(100, current + delta))
        self.player.set_volume(new_vol)
        self.transport.volume_slider.setValue(new_vol)
        self.status_bar.showMessage(f"Volume: {new_vol}%")

    # ── Update Timer ─────────────────────────────────────────────────

    def _start_update_timer(self):
        """Start a timer to periodically sync the transport bar with VLC."""
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(250)  # 4 updates/sec
        self.update_timer.timeout.connect(self._update_transport)
        self.update_timer.start()

    def _update_transport(self):
        """Sync transport bar with current player state."""
        state = self.player.media_player.get_state()
        if self._loop_current and state == vlc.State.Ended and self.player.has_media():
            self.player.set_time(0)
            self.player.media_player.play()

        position = self.player.get_position()
        current_ms = self.player.get_time()
        total_ms = self.player.get_duration()
        self.transport.update_position(position, current_ms, total_ms)
        self.transport.set_playing_state(self.player.is_playing())

        # Sync speed display
        rate = self.player.get_rate()
        self.transport.set_speed(rate)

    # ── Gesture Control ──────────────────────────────────────────────

    def _save_gesture_mapping(self):
        """Save the current dropdown selections as the gesture mapping."""
        action_keys = list(AVAILABLE_ACTIONS.keys())
        for gesture_name, combo in self._gesture_combos.items():
            idx = combo.currentIndex()
            self._gesture_mapping[gesture_name] = action_keys[idx]
        save_gesture_mapping(self._gesture_mapping)
        self.status_bar.showMessage("✅ Gesture mapping saved!")

    def _reset_gesture_mapping(self):
        """Reset all gesture dropdowns to default mapping."""
        self._gesture_mapping = reset_gesture_mapping()
        action_keys = list(AVAILABLE_ACTIONS.keys())
        for gesture_name, combo in self._gesture_combos.items():
            default_action = self._gesture_mapping.get(gesture_name, "none")
            if default_action in action_keys:
                combo.setCurrentIndex(action_keys.index(default_action))
        self.status_bar.showMessage("↩ Gesture mapping reset to defaults")

    def _toggle_gesture_tracking(self):
        """Start or stop gesture tracking."""
        if self._gesture_tracker and self._gesture_tracker.isRunning():
            self._gesture_tracker.stop()
            self._gesture_tracker.wait(2000)
            self._gesture_tracker = None
            if self._recognize_timer:
                self._recognize_timer.stop()
            if self._is_pinching:
                self._air_engine.end_stroke()
            self._is_pinching = False
            self._set_drawing_active(False)
            self.btn_gesture_toggle.setText("Start Gesture Control")
            self.btn_draw_toggle_tracking.setText("Start Tracking")
            self.gesture_status.setText("Status: Inactive")
            self.drawing_indicator.setText("TRACKING DISABLED")
            self.drawing_indicator.setStyleSheet("color: #f85149; font-weight: 700; font-size: 13px; letter-spacing: 0.05em;")
            self.canvas.clear_pinch_indicator()
            self.status_bar.showMessage("Gesture tracking stopped")
        else:
            # Save current dropdown selections before starting
            self._save_gesture_mapping()
            self._gesture_tracker = GestureTracker(camera_index=0)
            self._gesture_tracker.gesture_detected.connect(self._on_gesture_detected)
            self._gesture_tracker.finger_moved.connect(self._on_finger_moved)
            self._gesture_tracker.pinch_moved.connect(self._on_pinch_moved)
            self._gesture_tracker.hand_lost.connect(self._on_hand_lost_drawing)
            self._gesture_tracker.hand_found.connect(lambda: None)
            self._gesture_tracker.status_changed.connect(
                lambda msg: self.gesture_status.setText(f"Status: {msg}")
            )
            self._gesture_tracker.error.connect(
                lambda msg: self._on_gesture_error(msg)
            )
            # Connect frame_ready for hand preview if open
            self._gesture_tracker.frame_ready.connect(self._on_tracker_frame)
            if self._hand_preview and self._hand_preview.isVisible():
                self._gesture_tracker.set_emit_frames(True)
            self._gesture_tracker.set_drawing_mode(True)
            self._gesture_tracker.start()
            self.btn_gesture_toggle.setText("Stop Gesture Control")
            self.btn_draw_toggle_tracking.setText("Stop Tracking")
            self.drawing_indicator.setText("READY — Pinch to Draw")
            self.drawing_indicator.setStyleSheet("color: #3fb950; font-weight: 700; font-size: 13px; letter-spacing: 0.05em;")
            self.status_bar.showMessage("Gesture tracking started — pinch to draw")

    def _on_gesture_detected(self, gesture: str, action: str, confidence: float):
        """Handle a detected gesture by performing the mapped action."""
        # Use the USER's custom mapping, not the tracker's built-in one
        custom_action = self._gesture_mapping.get(gesture, action)

        display_action = get_action_display_name(custom_action)
        self.gesture_log.setText(
            f"🤚 {get_gesture_display_name(gesture)} → {display_action} ({confidence:.0%})"
        )
        self.status_bar.showMessage(
            f"Gesture: {gesture} → {display_action} ({confidence:.0%})"
        )

        # Execute the action (drawing is now pinch-based, not gesture-based)
        action_map = {
            "play_pause": self._on_play_pause,
            "stop": self._on_stop,
            "pause": lambda: self.player.pause(),
            "volume_up": lambda: self._adjust_volume(10),
            "volume_down": lambda: self._adjust_volume(-10),
            "forward": lambda: self.player.seek_relative(10000),
            "forward_skip": lambda: self.player.seek_relative(30000),
            "rewind": lambda: self.player.seek_relative(-10000),
            "speed_cycle": lambda: self.player.cycle_speed(forward=True),
            "mute_toggle": self._on_mute,
            "fullscreen": self._toggle_fullscreen,
        }

        handler = action_map.get(custom_action)
        if handler:
            handler()

    # ── Air Writing & Pinch Drawing ──────────────────────────────────

    def _load_air_writing_model(self):
        """Load the CNN model for air writing recognition."""
        self._air_model_loaded = self._air_engine.load_model()
        if self._air_model_loaded:
            if hasattr(self, 'air_writing_status'):
                self.air_writing_status.setText(
                    f"✅ Character recognition active ({self._air_engine._model_type})"
                )
                self.air_writing_status.setStyleSheet(
                    "color: #3fb950; font-size: 11px; font-weight: 600;"
                )
        else:
            if hasattr(self, 'air_writing_status'):
                self.air_writing_status.setText(
                    "⚠️ No CNN model found — drawing only (no recognition)"
                )
                self.air_writing_status.setStyleSheet(
                    "color: #f0a030; font-size: 11px; font-weight: 600;"
                )

    def _on_pinch_moved(self, x: float, y: float, z: float, is_pinching: bool):
        """Handle pinch point movement — drives drawing and air writing."""
        # Update pinch indicator on canvas
        self.canvas.set_pinch_indicator(x, y, is_pinching)
        if self._fullscreen_draw and self._fullscreen_draw.isVisible():
            self._fullscreen_draw.canvas.set_pinch_indicator(x, y, is_pinching)

        if is_pinching:
            # Pen is down — draw
            if not self._is_pinching:
                # Pinch just started
                self._is_pinching = True
                self._set_drawing_active(True)
                self._air_engine.begin_stroke()
                # Cancel any pending recognition timer
                if self._recognize_timer:
                    self._recognize_timer.stop()

            # Add point to canvas and air writing engine
            self.canvas.add_point(x, y, z)
            self._air_engine.add_stroke_point(x, y)

            # Also send to fullscreen canvas if open
            if self._fullscreen_draw and self._fullscreen_draw.isVisible():
                self._fullscreen_draw.canvas.add_point(x, y, z)
        else:
            # Pen is up
            if self._is_pinching:
                # Pinch just released — end stroke
                self._is_pinching = False
                self._set_drawing_active(False)
                self._air_engine.end_stroke()

                # Start a delayed recognition (wait for multi-stroke chars)
                if self._air_model_loaded and self._air_engine.has_content():
                    if self._recognize_timer:
                        self._recognize_timer.stop()
                    self._recognize_timer = QTimer(self)
                    self._recognize_timer.setSingleShot(True)
                    self._recognize_timer.timeout.connect(self._auto_recognize)
                    self._recognize_timer.start(1500)  # 1.5s after last stroke

    def _auto_recognize(self):
        """Auto-recognize after a pause in drawing."""
        if not self._air_engine.has_content():
            return

        char, confidence = self._air_engine.recognize_and_clear()
        if char and confidence > 0.3:
            self._update_recognized_text()
            self.canvas.set_live_preview(char, confidence)
            self.status_bar.showMessage(
                f"Recognized: '{char}' ({confidence:.0%})"
            )
        else:
            self.canvas.set_live_preview("", 0.0)
            self._air_engine.clear_board()

    def _force_recognize(self):
        """Force recognition of whatever is on the blackboard."""
        if not self._air_model_loaded:
            self.status_bar.showMessage("⚠ No recognition model loaded")
            return

        if not self._air_engine.has_content():
            self.status_bar.showMessage("⚠ Nothing to recognize")
            return

        char, confidence = self._air_engine.recognize_and_clear()
        if char:
            self._update_recognized_text()
            self.canvas.set_live_preview(char, confidence)
            self.status_bar.showMessage(
                f"Recognized: '{char}' ({confidence:.0%})"
            )
        else:
            self.status_bar.showMessage("Could not recognize character")

    def _update_recognized_text(self):
        """Sync the recognized text display."""
        text = self._air_engine.recognized_text
        self.recognized_text_display.setText(text)
        self.canvas.set_recognized_text(text)
        if self._fullscreen_draw and self._fullscreen_draw.isVisible():
            self._fullscreen_draw.canvas.set_recognized_text(text)

    def _air_writing_backspace(self):
        """Remove last recognized character."""
        self._air_engine.backspace()
        self._update_recognized_text()

    def _clear_drawing_and_text(self):
        """Clear both the canvas and recognized text."""
        self.canvas.clear()
        self._air_engine.clear_text()
        self._air_engine.clear_board()
        self._update_recognized_text()
        self.canvas.set_live_preview("", 0.0)

    def _set_drawing_active(self, active: bool):
        """Update drawing state and notify canvas."""
        if self._drawing_active == active:
            return
        self._drawing_active = active
        self.canvas.set_drawing(active)
        if active:
            self.drawing_indicator.setText("✏️ DRAWING")
            self.drawing_indicator.setStyleSheet("color: #f0a030; font-weight: 700; font-size: 13px; letter-spacing: 0.05em;")
        else:
            # Only show 'Ready' if the tracker is actually running
            if self._gesture_tracker and self._gesture_tracker.isRunning():
                self.drawing_indicator.setText("READY — Pinch to Draw")
                self.drawing_indicator.setStyleSheet("color: #3fb950; font-weight: 700; font-size: 13px; letter-spacing: 0.05em;")
            else:
                self.drawing_indicator.setText("TRACKING DISABLED")
                self.drawing_indicator.setStyleSheet("color: #f85149; font-weight: 700; font-size: 13px; letter-spacing: 0.05em;")

    def _on_hand_lost_drawing(self):
        """Handle hand lost for drawing."""
        if self._is_pinching:
            self._is_pinching = False
            self._set_drawing_active(False)
            self._air_engine.end_stroke()
        self.canvas.clear_pinch_indicator()
        self.hand_lost_handler()

    def hand_lost_handler(self):
        """Generic hand lost handler."""
        pass  # Can be extended

    def _on_finger_moved(self, x: float, y: float, z: float):
        """Handle smoothed finger movement from tracker (legacy, kept for compat)."""
        pass  # Drawing is now handled by _on_pinch_moved

    def _on_gesture_error(self, error_msg: str):
        """Handle gesture tracking errors."""
        if self._gesture_tracker and self._gesture_tracker.isRunning():
            self._gesture_tracker.stop()
            self._gesture_tracker.wait(2000)
        self._gesture_tracker = None
        if self._is_pinching:
            self._air_engine.end_stroke()
        self._is_pinching = False
        self.canvas.clear_pinch_indicator()
        self._set_drawing_active(False)

        self.gesture_status.setText(f"Status: Error")
        self.btn_gesture_toggle.setText("Start Gesture Control")
        self.btn_draw_toggle_tracking.setText("Start Tracking")
        self.status_bar.showMessage(f"Gesture error: {error_msg}")
        QMessageBox.warning(self, "Gesture Error", error_msg)

    # ── Hand Preview Window ──────────────────────────────────────────

    def _toggle_hand_preview(self, checked: bool):
        """Open or close the hand tracking preview window."""
        if checked:
            self._hand_preview = HandPreviewWindow()
            self._hand_preview.closed.connect(lambda: self.btn_hand_preview.setChecked(False))
            self._hand_preview.show()
            if self._gesture_tracker and self._gesture_tracker.isRunning():
                self._gesture_tracker.set_emit_frames(True)
            self.status_bar.showMessage("Hand tracking preview opened")
        else:
            if self._hand_preview:
                self._hand_preview.close()
                self._hand_preview = None
            if self._gesture_tracker:
                self._gesture_tracker.set_emit_frames(False)
            self.status_bar.showMessage("Hand tracking preview closed")

    def _on_tracker_frame(self, q_image):
        """Forward annotated webcam frame to the hand preview window."""
        if self._hand_preview and self._hand_preview.isVisible():
            self._hand_preview.set_frame(q_image)

    # ── Picture-in-Picture Window ────────────────────────────────────

    def _toggle_pip(self, checked: bool):
        """Open or close the PiP video window."""
        if checked:
            self._pip_window = PictureInPictureWindow()
            self._pip_window.closed.connect(self._on_pip_closed)
            self._pip_window.play_pause.connect(self._on_play_pause)
            self._pip_window.seek_relative.connect(lambda ms: self.player.seek_relative(ms))
            self._pip_window.volume_changed.connect(self.player.set_volume)
            self._pip_window.show()

            # Re-embed VLC output into PiP video frame
            QTimer.singleShot(100, self._embed_vlc_in_pip)

            # Start PiP update timer
            self._pip_timer = QTimer(self)
            self._pip_timer.setInterval(250)
            self._pip_timer.timeout.connect(self._update_pip)
            self._pip_timer.start()

            self.status_bar.showMessage("Picture-in-Picture enabled")
        else:
            self._close_pip()

    def _embed_vlc_in_pip(self):
        """Move VLC output to the PiP window."""
        if self._pip_window:
            QApplication.processEvents()
            pip_wid = int(self._pip_window.video_frame.winId())
            self.player.set_window(pip_wid)

    def _update_pip(self):
        """Sync PiP transport state with VLC."""
        if self._pip_window:
            self._pip_window.update_state(
                self.player.is_playing(),
                self.player.get_time(),
                self.player.get_duration(),
            )

    def _on_pip_closed(self):
        """Restore VLC output to main window when PiP closes."""
        self._close_pip()
        self.btn_pip.blockSignals(True)
        self.btn_pip.setChecked(False)
        self.btn_pip.blockSignals(False)

    def _close_pip(self):
        """Close PiP and restore VLC to main frame."""
        if self._closing_pip:
            return
        self._closing_pip = True

        if hasattr(self, '_pip_timer') and self._pip_timer:
            self._pip_timer.stop()
            self._pip_timer = None
        if self._pip_window:
            try:
                self._pip_window.closed.disconnect(self._on_pip_closed)
            except Exception:
                pass
            self._pip_window.close()
            self._pip_window = None
        # Re-embed VLC in main video frame
        QTimer.singleShot(100, self._embed_vlc)
        self.status_bar.showMessage("Video restored to main window")
        self._closing_pip = False

    # ── Fullscreen Drawing ───────────────────────────────────────────

    def _open_fullscreen_drawing(self):
        """Open the fullscreen drawing overlay."""
        self._fullscreen_draw = FullscreenDrawingWindow(self.canvas)
        self._fullscreen_draw.closed.connect(self._on_fullscreen_draw_closed)
        self._fullscreen_draw.show()
        self.status_bar.showMessage("Fullscreen drawing mode")

    def _on_fullscreen_draw_closed(self):
        """Sync paths back from fullscreen canvas."""
        self._fullscreen_draw = None
        self.status_bar.showMessage("Fullscreen drawing closed")

    # ── Cleanup ──────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Clean up VLC, gesture, PiP, preview, and air writing resources on close."""
        self.update_timer.stop()
        if self._recognize_timer:
            self._recognize_timer.stop()
        if self._gesture_tracker and self._gesture_tracker.isRunning():
            self._gesture_tracker.stop()
            self._gesture_tracker.wait(2000)
        if self._pip_window:
            self._close_pip()
        if self._hand_preview:
            self._hand_preview.close()
        if self._fullscreen_draw:
            self._fullscreen_draw.close()
        self.player.release()
        super().closeEvent(event)
