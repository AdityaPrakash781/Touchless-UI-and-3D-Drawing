"""
File browser — local video file selection with recent-files memory.
"""

from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QSettings


# Supported video extensions
VIDEO_FILTERS = (
    "Video Files (*.mp4 *.mkv *.avi *.webm *.mov *.flv *.wmv *.m4v *.ts *.m2ts *.mpg *.mpeg *.3gp *.ogv);;"
    "All Files (*)"
)


def pick_video_file(parent=None) -> str | None:
    """
    Open a native file dialog to select a video file.
    
    Returns:
        The selected file path, or None if cancelled.
    """
    path, _ = QFileDialog.getOpenFileName(
        parent,
        "Open Video File",
        _get_last_directory(),
        VIDEO_FILTERS,
    )
    if path:
        _save_last_directory(path)
        _add_to_recent(path)
        return path
    return None


def get_recent_files(max_count: int = 10) -> list[str]:
    """Retrieve the list of recently played files."""
    settings = QSettings("GestureVLC", "GestureVLC")
    files = settings.value("recent_files", [], type=list)
    return files[:max_count]


def clear_recent_files():
    """Clear the recent files list."""
    settings = QSettings("GestureVLC", "GestureVLC")
    settings.setValue("recent_files", [])


def _add_to_recent(path: str):
    """Add a file path to the recent files list (deduplicating)."""
    settings = QSettings("GestureVLC", "GestureVLC")
    files = settings.value("recent_files", [], type=list)
    if path in files:
        files.remove(path)
    files.insert(0, path)
    settings.setValue("recent_files", files[:20])  # Keep last 20


def _get_last_directory() -> str:
    """Get the last used directory for the file dialog."""
    settings = QSettings("GestureVLC", "GestureVLC")
    return settings.value("last_directory", "", type=str)


def _save_last_directory(path: str):
    """Save the directory of the selected file."""
    import os
    settings = QSettings("GestureVLC", "GestureVLC")
    settings.setValue("last_directory", os.path.dirname(path))
