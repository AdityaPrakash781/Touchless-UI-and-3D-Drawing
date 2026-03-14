"""
GestureVLC — Main Window

Central application window embedding VLC video playback,
YouTube search/URL integration, and local file browsing.
"""

import sys
import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLineEdit, QPushButton, QLabel,
    QFrame, QScrollArea, QSizePolicy, QStatusBar,
    QApplication, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QKeySequence, QShortcut, QFont, QIcon

from app.vlc_player import VLCPlayer
from app.youtube import StreamExtractor, SearchWorker, search_youtube
from app.controls import TransportBar
from app.file_browser import pick_video_file, get_recent_files
from app.styles import STYLESHEET, COLORS
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
        # Plain black background — no border-radius (breaks VLC rendering)
        self.setStyleSheet("background-color: #000000;")
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
        self.setWindowTitle("GestureVLC — Media Player")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        # VLC Player backend
        self.player = VLCPlayer()

        # Active threads
        self._stream_worker = None
        self._search_worker = None
        self._gesture_tracker = None
        self._gesture_mapping = load_gesture_mapping()
        self._gesture_combos = {}  # gesture_name -> QComboBox

        self._setup_ui()
        self._setup_shortcuts()
        self._start_update_timer()

        # Apply stylesheet
        self.setStyleSheet(STYLESHEET)

    # ── UI Construction ──────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Main content area (video + sidebar) ──
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(8, 8, 8, 4)
        content_layout.setSpacing(8)

        # Video frame
        self.video_frame = VideoFrame()
        self.video_frame.double_clicked.connect(self._toggle_fullscreen)
        content_layout.addWidget(self.video_frame, stretch=7)

        # Sidebar
        sidebar = self._build_sidebar()
        content_layout.addWidget(sidebar, stretch=3)

        root_layout.addLayout(content_layout, stretch=1)

        # ── Now-playing label ──
        self.now_playing = QLabel("")
        self.now_playing.setObjectName("statusLabel")
        self.now_playing.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.now_playing.setFixedHeight(24)
        root_layout.addWidget(self.now_playing)

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
        tabs.setMinimumWidth(320)
        tabs.setMaximumWidth(420)

        # ── YouTube Tab ──
        yt_widget = QWidget()
        yt_layout = QVBoxLayout(yt_widget)
        yt_layout.setContentsMargins(8, 12, 8, 8)
        yt_layout.setSpacing(10)

        # URL input
        url_label = QLabel("🔗  YouTube URL")
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
        search_label = QLabel("🔍  Search YouTube")
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

        tabs.addTab(yt_widget, "🎬  YouTube")

        # ── Local Files Tab ──
        local_widget = QWidget()
        local_layout = QVBoxLayout(local_widget)
        local_layout.setContentsMargins(8, 12, 8, 8)
        local_layout.setSpacing(10)

        open_label = QLabel("📁  Open Video File")
        open_label.setObjectName("titleLabel")
        local_layout.addWidget(open_label)

        self.btn_open_file = QPushButton("📂  Browse Files…")
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
        recent_label = QLabel("🕐  Recent Files")
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

        tabs.addTab(local_widget, "📁  Local")

        # ── Gesture Controls Tab ──
        gesture_widget = QWidget()
        gesture_layout = QVBoxLayout(gesture_widget)
        gesture_layout.setContentsMargins(8, 12, 8, 8)
        gesture_layout.setSpacing(8)

        gesture_title = QLabel("🤚  Gesture Controls")
        gesture_title.setObjectName("titleLabel")
        gesture_layout.addWidget(gesture_title)

        gesture_desc = QLabel(
            "Use hand gestures to control playback.\n"
            "Requires a webcam and trained model."
        )
        gesture_desc.setObjectName("secondaryLabel")
        gesture_desc.setWordWrap(True)
        gesture_layout.addWidget(gesture_desc)

        self.btn_gesture_toggle = QPushButton("🤚  Start Gesture Control")
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
        gesture_map_label = QLabel("⚙️  Customize Gesture → Action:")
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
        btn_save = QPushButton("💾  Save Mapping")
        btn_save.setObjectName("accentButton")
        btn_save.clicked.connect(self._save_gesture_mapping)

        btn_reset = QPushButton("↩  Reset Defaults")
        btn_reset.clicked.connect(self._reset_gesture_mapping)

        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_reset)
        gesture_layout.addLayout(btn_row)

        # Gesture log
        sep4 = QFrame()
        sep4.setObjectName("separator")
        sep4.setFrameShape(QFrame.Shape.HLine)
        gesture_layout.addWidget(sep4)

        gesture_log_label = QLabel("Recent Gestures:")
        gesture_log_label.setObjectName("titleLabel")
        gesture_layout.addWidget(gesture_log_label)

        self.gesture_log = QLabel("No gestures detected yet")
        self.gesture_log.setObjectName("secondaryLabel")
        self.gesture_log.setWordWrap(True)
        gesture_layout.addWidget(self.gesture_log)

        gesture_layout.addStretch()

        tabs.addTab(gesture_widget, "🤚  Gestures")

        # Populate recent files
        self._refresh_recent_files()

        return tabs

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
            btn = QPushButton(f"🎬  {filename}")
            btn.setToolTip(path)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 8px 12px;
                    background: {COLORS['bg_tertiary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    color: {COLORS['text_primary']};
                }}
                QPushButton:hover {{
                    background: {COLORS['bg_hover']};
                    border-color: {COLORS['accent']};
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
            "]": lambda: self.player.cycle_speed(forward=True),
            "[": lambda: self.player.cycle_speed(forward=False),
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
            self.btn_gesture_toggle.setText("🤚  Start Gesture Control")
            self.gesture_status.setText("Status: Inactive")
            self.status_bar.showMessage("Gesture tracking stopped")
        else:
            # Save current dropdown selections before starting
            self._save_gesture_mapping()
            self._gesture_tracker = GestureTracker(camera_index=0)
            self._gesture_tracker.gesture_detected.connect(self._on_gesture_detected)
            self._gesture_tracker.status_changed.connect(
                lambda msg: self.gesture_status.setText(f"Status: {msg}")
            )
            self._gesture_tracker.error.connect(
                lambda msg: self._on_gesture_error(msg)
            )
            self._gesture_tracker.start()
            self.btn_gesture_toggle.setText("⏹  Stop Gesture Control")
            self.gesture_status.setText("Status: Starting...")
            self.status_bar.showMessage("Gesture tracking started")

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

        # Execute the action
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

    def _on_gesture_error(self, error_msg: str):
        """Handle gesture tracking errors."""
        self.gesture_status.setText(f"Status: Error")
        self.status_bar.showMessage(f"Gesture error: {error_msg}")
        self.btn_gesture_toggle.setText("🤚  Start Gesture Control")
        QMessageBox.warning(self, "Gesture Error", error_msg)

    # ── Cleanup ──────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Clean up VLC and gesture resources on window close."""
        self.update_timer.stop()
        if self._gesture_tracker and self._gesture_tracker.isRunning():
            self._gesture_tracker.stop()
            self._gesture_tracker.wait(2000)
        self.player.release()
        super().closeEvent(event)
