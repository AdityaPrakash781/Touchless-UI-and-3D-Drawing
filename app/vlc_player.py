"""
VLC Player Wrapper — cross-platform VLC media player integration.

Provides a clean interface around python-vlc for embedding video
playback inside a PyQt6 widget.
"""

import sys
import vlc
from pathlib import Path


class VLCPlayer:
    """Wraps a VLC MediaPlayer instance with convenience methods."""

    # Playback speed presets
    SPEED_PRESETS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 3.0]

    def __init__(self):
        # Create VLC instance with no video title show and quiet logging
        args = ["--no-video-title-show", "--quiet"]
        if sys.platform == "linux":
            # Force X11 video output (matching Qt's XCB/XWayland window)
            # WAYLAND_DISPLAY is unset in main.py so VLC can't use Wayland
            args.extend(["--vout=xcb_x11", "--aout=pulse"])
        self.instance = vlc.Instance(*args)
        self.media_player = self.instance.media_player_new()
        self._current_rate = 1.0
        self._win_id = None

    # ── Window embedding ─────────────────────────────────────────────

    def set_window(self, win_id: int):
        """Embed VLC output into a platform-native window handle."""
        self._win_id = win_id
        self._apply_window()

    def _apply_window(self):
        """Apply the stored window ID to the media player."""
        if self._win_id is None:
            return
        if sys.platform == "linux":
            self.media_player.set_xwindow(self._win_id)
        elif sys.platform == "win32":
            self.media_player.set_hwnd(self._win_id)
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(self._win_id)

    # ── Playback control ─────────────────────────────────────────────

    def play(self, uri: str):
        """
        Play a media URI (local file path or network URL).
        
        Args:
            uri: A local file path or a network stream URL.
        """
        media = self.instance.media_new(uri)
        # Add network caching for smoother streaming
        media.add_option(":network-caching=3000")
        self.media_player.set_media(media)
        # Re-apply window embedding before playing — VLC can lose
        # the window reference between plays
        self._apply_window()
        self.media_player.play()
        # Restore playback rate
        self._apply_rate()

    def pause(self):
        """Toggle pause state."""
        self.media_player.pause()

    def stop(self):
        """Stop playback entirely."""
        self.media_player.stop()

    def toggle_play_pause(self):
        """Toggle between play and pause based on current state."""
        state = self.media_player.get_state()
        if state == vlc.State.Playing:
            self.media_player.pause()
        elif state in (vlc.State.Paused, vlc.State.Stopped, vlc.State.Ended):
            self.media_player.play()

    def is_playing(self) -> bool:
        """Return True if media is currently playing."""
        return self.media_player.is_playing() == 1

    # ── Seeking ──────────────────────────────────────────────────────

    def seek(self, position: float):
        """
        Seek to a position in the media.
        
        Args:
            position: Float from 0.0 to 1.0 representing the position.
        """
        self.media_player.set_position(max(0.0, min(1.0, position)))

    def seek_relative(self, delta_ms: int):
        """
        Seek forward or backward by delta_ms milliseconds.
        
        Args:
            delta_ms: Positive = forward, negative = backward.
        """
        current = self.media_player.get_time()
        duration = self.media_player.get_length()
        if current < 0 or duration <= 0:
            return
        new_time = max(0, min(duration, current + delta_ms))
        self.media_player.set_time(new_time)

    def get_position(self) -> float:
        """Get current position as a float [0.0, 1.0]."""
        pos = self.media_player.get_position()
        return max(0.0, pos) if pos >= 0 else 0.0

    def get_time(self) -> int:
        """Get current playback time in milliseconds."""
        t = self.media_player.get_time()
        return max(0, t)

    def get_duration(self) -> int:
        """Get total media duration in milliseconds."""
        d = self.media_player.get_length()
        return max(0, d)

    def set_time(self, ms: int):
        """Seek to an absolute time in milliseconds."""
        self.media_player.set_time(max(0, int(ms)))

    def has_media(self) -> bool:
        """Return True if a media object is attached."""
        return self.media_player.get_media() is not None

    # ── Volume ───────────────────────────────────────────────────────

    def set_volume(self, percent: int):
        """Set volume from 0 to 150 (VLC supports amplification)."""
        self.media_player.audio_set_volume(max(0, min(150, percent)))

    def get_volume(self) -> int:
        """Get current volume (0–150)."""
        return self.media_player.audio_get_volume()

    def toggle_mute(self):
        """Toggle audio mute."""
        self.media_player.audio_toggle_mute()

    def is_muted(self) -> bool:
        """Return True if audio is muted."""
        return self.media_player.audio_get_mute() == 1

    # ── Playback speed ───────────────────────────────────────────────

    def set_rate(self, rate: float):
        """
        Set playback speed. 1.0 = normal.
        
        Args:
            rate: Playback rate (0.25–3.0 recommended).
        """
        self._current_rate = max(0.25, min(3.0, rate))
        self._apply_rate()

    def get_rate(self) -> float:
        """Get current playback rate."""
        return self._current_rate

    def cycle_speed(self, forward: bool = True):
        """
        Cycle through SPEED_PRESETS.
        
        Args:
            forward: True to go to the next faster speed, False for slower.
        """
        try:
            idx = self.SPEED_PRESETS.index(self._current_rate)
        except ValueError:
            idx = self.SPEED_PRESETS.index(1.0)

        if forward:
            idx = min(idx + 1, len(self.SPEED_PRESETS) - 1)
        else:
            idx = max(idx - 1, 0)

        self.set_rate(self.SPEED_PRESETS[idx])

    def _apply_rate(self):
        """Apply the stored rate to the media player."""
        self.media_player.set_rate(self._current_rate)

    # ── Video Features ──────────────────────────────────────────────

    def take_snapshot(self, output_path: str) -> bool:
        """Save a snapshot of the current frame to output_path."""
        out = str(Path(output_path))
        result = self.media_player.video_take_snapshot(0, out, 0, 0)
        return result == 0

    def set_aspect_ratio(self, ratio: str | None):
        """Set video aspect ratio. Use None or '' for default."""
        value = ratio if ratio else None
        self.media_player.video_set_aspect_ratio(value)

    def set_crop(self, crop: str | None):
        """Set crop geometry string (example: '16:9'), or None to reset."""
        value = crop if crop else None
        self.media_player.video_set_crop_geometry(value)

    # ── Tracks & Subtitles ──────────────────────────────────────────

    def get_audio_tracks(self) -> list[tuple[int, str]]:
        """Return available audio tracks as (id, label)."""
        tracks = self.media_player.audio_get_track_description() or []
        out = []
        for t in tracks:
            name = t.name.decode("utf-8", errors="replace") if isinstance(t.name, bytes) else str(t.name)
            out.append((int(t.id), name))
        return out

    def get_current_audio_track(self) -> int:
        """Return current audio track id."""
        return int(self.media_player.audio_get_track())

    def set_audio_track(self, track_id: int):
        """Switch to a specific audio track id."""
        self.media_player.audio_set_track(int(track_id))

    def get_subtitle_tracks(self) -> list[tuple[int, str]]:
        """Return subtitle/SPU tracks as (id, label)."""
        tracks = self.media_player.video_get_spu_description() or []
        out = []
        for t in tracks:
            name = t.name.decode("utf-8", errors="replace") if isinstance(t.name, bytes) else str(t.name)
            out.append((int(t.id), name))
        return out

    def get_current_subtitle_track(self) -> int:
        """Return current subtitle track id."""
        return int(self.media_player.video_get_spu())

    def set_subtitle_track(self, track_id: int):
        """Switch to a specific subtitle track id."""
        self.media_player.video_set_spu(int(track_id))

    # ── Fullscreen ───────────────────────────────────────────────────

    def set_fullscreen(self, enable: bool):
        """Enable or disable VLC fullscreen mode."""
        self.media_player.set_fullscreen(enable)

    def toggle_fullscreen(self):
        """Toggle fullscreen."""
        self.media_player.toggle_fullscreen()

    # ── Cleanup ──────────────────────────────────────────────────────

    def release(self):
        """Release all VLC resources."""
        self.media_player.stop()
        self.media_player.release()
        self.instance.release()
