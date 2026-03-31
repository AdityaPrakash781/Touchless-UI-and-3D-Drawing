"""
Gesture Settings — Persistent gesture-to-action mapping customization.

Users can reassign which gesture triggers which media control action.
Settings are stored as JSON and loaded at startup.
"""

import json
from pathlib import Path
from PyQt6.QtCore import QSettings


# All available media control actions
AVAILABLE_ACTIONS = {
    "play_pause":    "▶⏸  Play / Pause",
    "stop":          "⏹  Stop",
    "pause":         "⏸  Pause",
    "volume_up":     "🔊  Volume Up",
    "volume_down":   "🔉  Volume Down",
    "forward":       "⏩  Forward 10s",
    "rewind":        "⏪  Rewind 10s",
    "forward_skip":  "⏭  Forward 30s",
    "speed_cycle":   "⚡  Cycle Speed",
    "mute_toggle":   "🔇  Mute / Unmute",
    "fullscreen":    "⛶  Fullscreen Toggle",
    "draw":          "🖊️  Draw (3D)",
    "none":          "—  (No Action)",
}

# Default gesture → action mapping
DEFAULT_MAPPING = {
    "palm":      "play_pause",
    "fist":      "stop",
    "like":      "volume_up",
    "dislike":   "volume_down",
    "stop":      "pause",
    "peace":     "forward",
    "ok":        "speed_cycle",
    "one":       "forward_skip",
    "mute":      "mute_toggle",
    "call":      "none",
    "rock":      "fullscreen",
    "two_up":    "rewind",
    "three":     "none",
    "four":      "none",
}

SETTINGS_FILE = Path(__file__).parent / "gesture_settings.json"


def load_gesture_mapping() -> dict:
    """Load the gesture → action mapping from settings file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                mapping = json.load(f)
            # Validate all actions exist
            for gesture, action in mapping.items():
                if action not in AVAILABLE_ACTIONS:
                    mapping[gesture] = DEFAULT_MAPPING.get(gesture, "none")
            return mapping
        except (json.JSONDecodeError, KeyError):
            pass
    return DEFAULT_MAPPING.copy()


def save_gesture_mapping(mapping: dict):
    """Save the gesture → action mapping to settings file."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(mapping, f, indent=2)


def reset_gesture_mapping() -> dict:
    """Reset to default mapping."""
    save_gesture_mapping(DEFAULT_MAPPING)
    return DEFAULT_MAPPING.copy()


def get_action_display_name(action: str) -> str:
    """Get the human-readable display name for an action."""
    return AVAILABLE_ACTIONS.get(action, action)


def get_gesture_display_name(gesture: str) -> str:
    """Get a human-readable display name with emoji for a gesture."""
    GESTURE_EMOJIS = {
        "palm":     "✋ Palm",
        "fist":     "✊ Fist",
        "like":     "👍 Like",
        "dislike":  "👎 Dislike",
        "stop":     "🛑 Stop",
        "peace":    "✌️ Peace",
        "ok":       "👌 OK",
        "one":      "☝️ One",
        "mute":     "🤫 Mute",
        "call":     "🤙 Call",
        "rock":     "🤟 Rock",
        "two_up":   "👆 Two Up",
        "three":    "🖖 Three",
        "four":     "🖐️ Four",
    }
    return GESTURE_EMOJIS.get(gesture, gesture)
