"""
YouTube Integration — extract stream URLs and search YouTube via yt-dlp.

All extraction runs in background threads to keep the UI responsive.
"""

import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal


class StreamExtractor(QThread):
    """
    Worker thread that extracts a playable stream URL from a YouTube URL.
    
    Signals:
        finished(str): Emitted with the stream URL on success.
        error(str): Emitted with an error message on failure.
        progress(str): Emitted with status updates during extraction.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            self.progress.emit("Extracting stream URL…")
            url = extract_stream_url(self.url)
            if url:
                self.finished.emit(url)
            else:
                self.error.emit("Could not extract a playable stream URL.")
        except Exception as e:
            self.error.emit(str(e))


class SearchWorker(QThread):
    """
    Worker thread that searches YouTube and returns results.
    
    Signals:
        finished(list): Emitted with a list of result dicts on success.
        error(str): Emitted with an error message on failure.
        progress(str): Emitted with status updates.
    """
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, query: str, max_results: int = 10, parent=None):
        super().__init__(parent)
        self.query = query
        self.max_results = max_results

    def run(self):
        try:
            self.progress.emit(f"Searching YouTube for '{self.query}'…")
            results = search_youtube(self.query, self.max_results)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


def extract_stream_url(url: str) -> str | None:
    """
    Extract the best playable stream URL from a YouTube (or compatible) URL.
    
    Uses yt-dlp to resolve the direct media URL that VLC can play.
    Prefers combined audio+video formats; falls back to best available.
    
    Args:
        url: A YouTube URL (or any URL supported by yt-dlp).
        
    Returns:
        Direct stream URL string, or None if extraction fails.
    """
    ydl_opts = {
        "format": "best[ext=mp4]/best",  # Prefer mp4 for widest VLC compat
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                return None
            # Direct URL
            if "url" in info:
                return info["url"]
            # Requested formats list (merged)
            if "requested_formats" in info:
                # Return the video format URL (VLC handles muxing)
                for fmt in info["requested_formats"]:
                    if fmt.get("vcodec", "none") != "none":
                        return fmt["url"]
            # Fallback: formats list
            if "formats" in info:
                # Pick the last (usually best) format with video
                for fmt in reversed(info["formats"]):
                    if fmt.get("vcodec", "none") != "none" and fmt.get("url"):
                        return fmt["url"]
            return info.get("url")
    except Exception:
        return None


def search_youtube(query: str, max_results: int = 10) -> list[dict]:
    """
    Search YouTube and return a list of video results.
    
    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        
    Returns:
        List of dicts, each containing:
            - title (str)
            - url (str): YouTube watch URL
            - thumbnail (str): Thumbnail URL
            - duration (int): Duration in seconds
            - duration_str (str): Human-readable duration
            - channel (str): Channel name
            - view_count (int): Number of views
            - upload_date (str): Upload date
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "ignoreerrors": True,
    }

    results = []
    try:
        search_url = f"ytsearch{max_results}:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            if info is None:
                return results

            entries = info.get("entries", [])
            for entry in entries:
                if entry is None:
                    continue
                duration_secs = entry.get("duration") or 0

                # Build proper YouTube watch URL
                video_id = entry.get("id", "")
                video_url = entry.get("webpage_url") or entry.get("url", "")
                if video_id and not video_url.startswith("http"):
                    video_url = f"https://www.youtube.com/watch?v={video_id}"

                results.append({
                    "title": entry.get("title", "Unknown"),
                    "url": video_url,
                    "thumbnail": entry.get("thumbnail") or entry.get("thumbnails", [{}])[0].get("url", "") if entry.get("thumbnails") else "",
                    "duration": duration_secs,
                    "duration_str": _format_duration(duration_secs),
                    "channel": entry.get("channel") or entry.get("uploader") or entry.get("uploader_id", "Unknown"),
                    "view_count": entry.get("view_count") or 0,
                    "upload_date": entry.get("upload_date", ""),
                })
    except Exception as e:
        import traceback
        traceback.print_exc()

    return results


def _format_duration(seconds: int) -> str:
    """Convert seconds to a human-readable HH:MM:SS or MM:SS string."""
    if seconds <= 0:
        return "LIVE"
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
