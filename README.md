# GestureVLC — Touchless Media Player

A cross-platform media player built on top of VLC with **ad-free YouTube playback** and **real-time hand gesture controls**.

> 🤚 Control video playback with hand gestures — no keyboard or mouse needed.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎬 **VLC Video Player** | Embedded VLC for local video playback |
| 📺 **Ad-Free YouTube** | Paste a URL or search — plays without ads via `yt-dlp` |
| 🤚 **Gesture Controls** | Control playback with 14 hand gestures via webcam |
| ⚙️ **Customizable Gestures** | Reassign any gesture to any media action |
| ⌨️ **Keyboard Shortcuts** | Full keyboard control (Space, F, ←/→, ↑/↓, etc.) |
| 🌙 **Dark Theme** | GitHub-inspired dark UI |
| 🖥️ **Cross-Platform** | Linux, Windows, macOS |

---

## 🚀 Quick Start

### Automated Setup (Recommended)

```bash
git clone https://github.com/AdityaPrakash781/Touchless-UI-and-3D-Drawing.git
cd Touchless-UI-and-3D-Drawing
chmod +x setup.sh
./setup.sh
```

### Manual Setup

#### Prerequisites
- **Python 3.10+**
- **VLC Media Player** (system install)
- **Webcam** (for gesture controls, optional)

#### Step 1: Clone & Create Environment
```bash
git clone https://github.com/AdityaPrakash781/Touchless-UI-and-3D-Drawing.git
cd Touchless-UI-and-3D-Drawing
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

#### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 3: Download Hand Landmark Model
```bash
curl -o gesture/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
```

#### Step 4: Run
```bash
python3 main.py
```

---

## 🎮 Gesture Controls

| Gesture | Default Action |
|---------|---------------|
| ✋ Palm | Play / Pause |
| ✊ Fist | Stop |
| 👍 Like | Volume Up |
| 👎 Dislike | Volume Down |
| ✌️ Peace | Forward 10s |
| 👆 Two Up | Rewind 10s |
| 👌 OK | Cycle Speed |
| ☝️ One | Forward 30s |
| 🤟 Rock | Fullscreen |
| 🤫 Mute | Mute/Unmute |

> All gestures are **fully customizable** via the Gestures tab in the app.

### Training the Gesture Model

To train the gesture classifier from scratch:

1. Download the [HaGRID dataset](https://github.com/hukenovs/hagrid) (120K hand gesture images)
2. Place it at `dataset/hagrid-sample-120k-384p/`
3. Run extraction and training:
```bash
source .venv/bin/activate
python3 gesture/extract_landmarks.py   # Extract MediaPipe landmarks (~5 min)
python3 gesture/train_classifier.py    # Train classifier (~10 min)
```

The trained model achieves **94% accuracy** across 14 gesture classes.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `F` | Fullscreen |
| `Escape` | Exit Fullscreen |
| `←` / `→` | Seek -10s / +10s |
| `Shift+←` / `Shift+→` | Seek -30s / +30s |
| `↑` / `↓` | Volume Up / Down |
| `M` | Mute |
| `S` | Stop |
| `Ctrl+O` | Open File |
| `]` / `[` | Speed Up / Down |

---

## 📁 Project Structure

```
gesturevlc/
├── main.py                 # Entry point
├── setup.sh                # Automated setup script
├── requirements.txt        # Python dependencies
├── app/
│   ├── main_window.py      # Main application window (PyQt6)
│   ├── vlc_player.py       # VLC media player wrapper
│   ├── youtube.py          # YouTube search & stream extraction
│   ├── controls.py         # Transport bar (play/pause/seek/volume)
│   ├── file_browser.py     # Local file browser
│   └── styles.py           # Dark theme stylesheet
├── gesture/
│   ├── extract_landmarks.py  # HaGRID → MediaPipe landmarks
│   ├── train_classifier.py   # Train RF/GBM/MLP classifiers
│   ├── tracker.py             # Real-time webcam gesture tracker
│   ├── settings.py            # Gesture customization persistence
│   └── hand_landmarker.task   # MediaPipe model (downloaded)
└── dataset/                   # HaGRID dataset (not included)
```

---

## 🐛 Troubleshooting

### Video not visible (Linux/Wayland)
The app automatically forces XWayland mode. If video still doesn't show:
```bash
QT_QPA_PLATFORM=xcb python3 main.py
```

### YouTube search not working
Update `yt-dlp` to the latest version:
```bash
pip install --upgrade yt-dlp
```

### Webcam not detected
Check that your webcam is accessible:
```bash
ls /dev/video*
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [VLC](https://www.videolan.org/) — Media playback
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — YouTube stream extraction
- [MediaPipe](https://ai.google.dev/edge/mediapipe) — Hand landmark detection
- [HaGRID](https://github.com/hukenovs/hagrid) — Hand gesture dataset
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — GUI framework
