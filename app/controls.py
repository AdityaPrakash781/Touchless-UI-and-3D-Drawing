"""
Transport controls widget — Obsidian Cinematic edition.

Sleek seek bar with amber accent, monospace timecodes,
cinematic play/pause button, and refined volume/speed controls.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QSlider, QLabel, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer


class TransportBar(QWidget):
    """
    Media transport control bar with play/pause, seek slider,
    time display, volume, playback speed, and fullscreen toggle.
    """

    # Signals emitted to the main window
    play_pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    seek_requested = pyqtSignal(float)       # position 0.0–1.0
    rewind_clicked = pyqtSignal()             # rewind 10s
    forward_clicked = pyqtSignal()            # forward 10s
    volume_changed = pyqtSignal(int)          # 0–100
    mute_clicked = pyqtSignal()
    speed_changed = pyqtSignal(float)         # playback rate
    fullscreen_clicked = pyqtSignal()

    SPEED_OPTIONS = ["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "1.75x", "2.0x", "3.0x"]
    SPEED_VALUES  = [0.25,    0.5,    0.75,    1.0,    1.25,    1.5,    1.75,    2.0,    3.0]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_seeking = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Build the transport bar layout."""
        self.setObjectName("transportBar")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 6, 20, 10)
        main_layout.setSpacing(6)

        # ── Seek slider + time labels row ──
        seek_row = QHBoxLayout()
        seek_row.setSpacing(12)

        self.time_current = QLabel("0:00")
        self.time_current.setObjectName("timeLabel")
        self.time_current.setFixedWidth(60)
        self.time_current.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 10000)
        self.seek_slider.setValue(0)
        self.seek_slider.setTracking(True)
        self.seek_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.time_total = QLabel("0:00")
        self.time_total.setObjectName("timeLabel")
        self.time_total.setFixedWidth(60)

        seek_row.addWidget(self.time_current)
        seek_row.addWidget(self.seek_slider)
        seek_row.addWidget(self.time_total)
        main_layout.addLayout(seek_row)

        # ── Controls row ──
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)

        # Left group: volume
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setObjectName("transportBtn")
        self.btn_mute.setToolTip("Mute / Unmute")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setToolTip("Volume")

        self.volume_label = QLabel("80%")
        self.volume_label.setObjectName("secondaryLabel")
        self.volume_label.setFixedWidth(35)

        controls_row.addWidget(self.btn_mute)
        controls_row.addWidget(self.volume_slider)
        controls_row.addWidget(self.volume_label)
        controls_row.addStretch()

        # Center group: stop, rewind, PLAY, forward
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setObjectName("transportBtn")
        self.btn_stop.setToolTip("Stop")

        self.btn_rewind = QPushButton("⏪")
        self.btn_rewind.setObjectName("transportBtn")
        self.btn_rewind.setToolTip("Rewind 10s")

        self.btn_play_pause = QPushButton("▶")
        self.btn_play_pause.setObjectName("playBtn")
        self.btn_play_pause.setToolTip("Play / Pause")

        self.btn_forward = QPushButton("⏩")
        self.btn_forward.setObjectName("transportBtn")
        self.btn_forward.setToolTip("Forward 10s")

        controls_row.addWidget(self.btn_stop)
        controls_row.addSpacing(4)
        controls_row.addWidget(self.btn_rewind)
        controls_row.addSpacing(4)
        controls_row.addWidget(self.btn_play_pause)
        controls_row.addSpacing(4)
        controls_row.addWidget(self.btn_forward)

        controls_row.addStretch()

        # Right group: speed, fullscreen
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(self.SPEED_OPTIONS)
        self.speed_combo.setCurrentIndex(3)  # 1.0x
        self.speed_combo.setToolTip("Playback Speed")
        self.speed_combo.setFixedWidth(80)

        self.btn_fullscreen = QPushButton("⛶")
        self.btn_fullscreen.setObjectName("transportBtn")
        self.btn_fullscreen.setToolTip("Fullscreen")

        controls_row.addWidget(self.speed_combo)
        controls_row.addSpacing(8)
        controls_row.addWidget(self.btn_fullscreen)

        main_layout.addLayout(controls_row)

    def _connect_signals(self):
        """Wire button clicks and slider changes to signals."""
        self.btn_play_pause.clicked.connect(self.play_pause_clicked.emit)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        self.btn_rewind.clicked.connect(self.rewind_clicked.emit)
        self.btn_forward.clicked.connect(self.forward_clicked.emit)
        self.btn_mute.clicked.connect(self.mute_clicked.emit)
        self.btn_fullscreen.clicked.connect(self.fullscreen_clicked.emit)

        # Seek slider
        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)
        self.seek_slider.sliderMoved.connect(self._on_seek_move)

        # Volume slider
        self.volume_slider.valueChanged.connect(self._on_volume_change)

        # Speed combo
        self.speed_combo.currentIndexChanged.connect(self._on_speed_change)

    # ── Seek handling ────────────────────────────────────────────────

    def _on_seek_start(self):
        self._is_seeking = True

    def _on_seek_end(self):
        position = self.seek_slider.value() / 10000.0
        self.seek_requested.emit(position)
        self._is_seeking = False

    def _on_seek_move(self, value):
        # Update the time label in real-time during drag
        if self._is_seeking:
            position = value / 10000.0
            total_text = self.time_total.text()
            self.time_current.setText(self._estimate_time(position, total_text))

    def _estimate_time(self, position: float, total_text: str) -> str:
        """Estimate current time from position and total duration text."""
        try:
            parts = total_text.split(":")
            if len(parts) == 3:
                total_secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                total_secs = int(parts[0]) * 60 + int(parts[1])
            else:
                return "0:00"
            current_secs = int(position * total_secs)
            return _format_time_ms(current_secs * 1000)
        except (ValueError, IndexError):
            return "0:00"

    # ── Volume ───────────────────────────────────────────────────────

    def _on_volume_change(self, value):
        self.volume_label.setText(f"{value}%")
        self.volume_changed.emit(value)

    # ── Speed ────────────────────────────────────────────────────────

    def _on_speed_change(self, index):
        if 0 <= index < len(self.SPEED_VALUES):
            self.speed_changed.emit(self.SPEED_VALUES[index])

    # ── Public update methods (called by timer in main_window) ──────

    def update_position(self, position: float, current_ms: int, total_ms: int):
        """Update the seek slider and time labels from the player state."""
        if not self._is_seeking:
            self.seek_slider.setValue(int(position * 10000))
        self.time_current.setText(_format_time_ms(current_ms))
        self.time_total.setText(_format_time_ms(total_ms))

    def set_playing_state(self, is_playing: bool):
        """Update the play/pause button icon."""
        self.btn_play_pause.setText("⏸" if is_playing else "▶")
        self.btn_play_pause.setToolTip("Pause" if is_playing else "Play")

    def set_muted_state(self, is_muted: bool):
        """Update the mute button icon."""
        self.btn_mute.setText("🔇" if is_muted else "🔊")

    def set_speed(self, rate: float):
        """Sync speed combo to a given rate."""
        try:
            idx = self.SPEED_VALUES.index(rate)
            self.speed_combo.blockSignals(True)
            self.speed_combo.setCurrentIndex(idx)
            self.speed_combo.blockSignals(False)
        except ValueError:
            pass


def _format_time_ms(ms: int) -> str:
    """Format milliseconds into H:MM:SS or M:SS."""
    if ms <= 0:
        return "0:00"
    total_secs = ms // 1000
    hours, remainder = divmod(total_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"
