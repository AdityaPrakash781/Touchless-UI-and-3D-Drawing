# GestureVLC 🎬

A cross-platform VLC media player with YouTube integration (ad-free playback) and future gesture controls.

Built with **Python**, **PyQt6**, **python-vlc**, and **yt-dlp**.

---

## Features

- 🎥 **Local video playback** — Play any video file (mp4, mkv, avi, webm, mov, etc.) via VLC
- 📺 **YouTube ad-free** — Paste a YouTube URL or search YouTube, plays directly via VLC with zero ads
- 🔍 **YouTube search** — Search for videos directly from the app sidebar
- ⏯️ **Full transport controls** — Play/pause, stop, seek, volume, playback speed (0.25x–3x), fullscreen
- ⌨️ **Keyboard shortcuts** — Space (play/pause), F (fullscreen), arrow keys (seek/volume), M (mute), etc.
- 🕐 **Recent files** — Remembers your recently played local files
- 🌑 **Dark theme** — Modern, premium dark UI
- 🤚 **Gesture controls** — *Coming soon* — hand gesture recognition via MediaPipe

---

## Requirements

- **Python 3.10+**
- **VLC media player** installed on your system
  - Linux: `sudo pacman -S vlc` (Arch) or `sudo apt install vlc` (Debian/Ubuntu)
  - Windows: Download from [videolan.org](https://www.videolan.org/)
  - macOS: `brew install vlc` or download from videolan.org

---

## Installation

```bash
# Clone or navigate to the project directory
cd gesturevlc

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

```bash
# Activate your virtual environment first
source .venv/bin/activate

# Run the app
python3 main.py
```

### YouTube URL Playback
1. Go to the **YouTube** tab in the sidebar
2. Paste a YouTube URL in the URL field
3. Click **▶ Play** or press Enter
4. The video plays ad-free in the VLC player

### YouTube Search
1. Type a search query in the search field
2. Click **Search** or press Enter
3. Click any result card to play it

### Local File Playback
1. Go to the **Local** tab in the sidebar
2. Click **📂 Browse Files…** to open a file
3. Or click a recent file to replay it

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `F` | Toggle fullscreen |
| `Escape` | Exit fullscreen |
| `←` / `→` | Seek ±10 seconds |
| `Shift+←` / `Shift+→` | Seek ±30 seconds |
| `↑` / `↓` | Volume ±5% |
| `M` | Mute / Unmute |
| `S` | Stop |
| `]` / `[` | Speed up / Speed down |
| `Ctrl+O` | Open file |

---

## Project Structure

```
gesturevlc/
├── main.py                  # Entry point
├── requirements.txt         # Python dependencies
├── README.md
├── app/
│   ├── __init__.py
│   ├── main_window.py       # PyQt6 main window + VLC widget
│   ├── vlc_player.py        # VLC wrapper
│   ├── youtube.py           # yt-dlp integration
│   ├── file_browser.py      # Local file picker
│   ├── controls.py          # Transport bar widget
│   └── styles.py            # Dark theme stylesheet
└── gesture/                 # Future: gesture recognition
    └── __init__.py
```

---

## Gesture Controls (Planned)

The gesture module will use **MediaPipe Hands** for real-time hand tracking and a lightweight classifier for gesture recognition.

**Recommended dataset:** [HaGRID](https://arxiv.org/abs/2206.08219) — 552K images, 18 gesture classes.

| Gesture | Action |
|---------|--------|
| Open palm | Play / Pause |
| Closed fist | Stop |
| Swipe left | Rewind 10s |
| Swipe right | Forward 10s |
| Thumb up / down | Volume up / down |
| Pinch | Cycle playback speed |

---

## License

MIT
