"""
Real-time Gesture Tracker — Webcam hand gesture recognition.

Uses MediaPipe Tasks API (HandLandmarker) for landmark extraction
and the trained classifier for gesture recognition in real-time.

Optimised for low-latency:
  - Reduced sleep interval (10ms vs 30ms)
  - Emits annotated webcam frames for the live preview overlay
  - Pinch-point tracking for pen-holding gesture drawing
  - Geometry-based pinch detection (no ML overhead)
"""

import sys
import time
import math
import numpy as np
import pickle
import json
import cv2
from pathlib import Path
import urllib.request

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
)

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage


HAND_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)


def _candidate_gesture_dirs() -> list[Path]:
    """Return likely gesture asset directories for dev and packaged builds."""
    dirs: list[Path] = []

    # Source run: .../gesture/tracker.py
    dirs.append(Path(__file__).resolve().parent)

    # PyInstaller one-folder: app root + _internal
    exe_dir = Path(sys.executable).resolve().parent
    dirs.append(exe_dir / "_internal" / "gesture")
    dirs.append(exe_dir / "gesture")

    # CWD fallback (helps debugging/custom launches)
    dirs.append(Path.cwd() / "gesture")

    seen = set()
    unique: list[Path] = []
    for d in dirs:
        key = str(d)
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def _resolve_asset(name: str) -> Path | None:
    """Find an asset file in any known runtime gesture directory."""
    for d in _candidate_gesture_dirs():
        p = d / name
        if p.exists():
            return p
    return None


def _preferred_gesture_dir() -> Path:
    """Choose preferred gesture directory for saving/downloading runtime assets."""
    for d in _candidate_gesture_dirs():
        if d.exists():
            return d
    return _candidate_gesture_dirs()[0]

# MediaPipe landmark connections for drawing skeleton
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),       # thumb
    (0,5),(5,6),(6,7),(7,8),       # index
    (0,9),(9,10),(10,11),(11,12),  # middle
    (0,13),(13,14),(14,15),(15,16),# ring
    (0,17),(17,18),(18,19),(19,20),# pinky
    (5,9),(9,13),(13,17),          # palm
]

# Landmark indices
THUMB_TIP = 4
INDEX_TIP = 8
INDEX_MCP = 5  # base of index finger


class KalmanFilter:
    """Simple 1D Kalman Filter for smoothing noisy signals."""
    def __init__(self, process_variance: float = 1e-5, measurement_variance: float = 1e-3):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.posteriari_estimate = 0.0
        self.posteriari_error_estimate = 1.0

    def update(self, measurement: float) -> float:
        priori_estimate = self.posteriari_estimate
        priori_error_estimate = self.posteriari_error_estimate + self.process_variance

        blending_factor = priori_error_estimate / (priori_error_estimate + self.measurement_variance)
        self.posteriari_estimate = priori_estimate + blending_factor * (measurement - priori_estimate)
        self.posteriari_error_estimate = (1 - blending_factor) * priori_error_estimate

        return self.posteriari_estimate

    def reset(self):
        """Reset the filter state."""
        self.posteriari_estimate = 0.0
        self.posteriari_error_estimate = 1.0


class Point3DSmoother:
    """Smoothes a 3D point (x, y, z) using three Kalman filters."""
    def __init__(self, process_variance: float = 1e-5, measurement_variance: float = 1e-3):
        self.kf_x = KalmanFilter(process_variance, measurement_variance)
        self.kf_y = KalmanFilter(process_variance, measurement_variance)
        self.kf_z = KalmanFilter(process_variance, measurement_variance)

    def update(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        return (
            self.kf_x.update(x),
            self.kf_y.update(y),
            self.kf_z.update(z)
        )

    def reset(self):
        self.kf_x.reset()
        self.kf_y.reset()
        self.kf_z.reset()


class GestureTracker(QThread):
    """
    Real-time gesture recognition thread.

    Captures webcam frames, extracts hand landmarks via MediaPipe Tasks API,
    classifies gestures, and emits action signals.

    Signals:
        gesture_detected(str, str, float): (gesture_name, action, confidence)
        finger_moved(float, float, float): (x, y, z) index finger tip
        pinch_moved(float, float, float, bool): (x, y, z, is_pinching) pinch point
        hand_lost(): emitted when no hand is detected
        hand_found(): emitted when a hand re-appears
        status_changed(str): Status message updates
        error(str): Error messages
        frame_ready(QImage): Annotated webcam frame for live preview
    """

    gesture_detected = pyqtSignal(str, str, float)
    finger_moved = pyqtSignal(float, float, float)
    pinch_moved = pyqtSignal(float, float, float, bool)  # x, y, z, is_pinching
    hand_lost = pyqtSignal()
    hand_found = pyqtSignal()
    status_changed = pyqtSignal(str)
    error = pyqtSignal(str)
    frame_ready = pyqtSignal(QImage)

    DEBOUNCE_TIME = 1.0
    CONFIDENCE_THRESHOLD = 0.5
    STABILITY_COUNT = 5
    BUFFER_SIZE = 30

    # Pinch detection threshold: distance between thumb tip and index tip
    # in normalized coordinates. Below this = pinching (pen down).
    PINCH_THRESHOLD = 0.06
    PINCH_RELEASE_THRESHOLD = 0.09  # Hysteresis: slightly higher to release
    PINCH_ENGAGE_FRAMES = 3
    PINCH_RELEASE_FRAMES = 2
    UI_EMIT_INTERVAL = 1.0 / 45.0  # Cap high-frequency UI updates to ~45 FPS

    def __init__(self, camera_index: int = 0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self._running = False
        self._model = None
        self._scaler = None
        self._hand_model_path: Path | None = None
        self._class_names = []
        self._class_to_action = {}
        self._needs_scaling = False
        self._emit_frames = False  # Only emit frames if preview is active
        self._drawing_mode = False  # When True, skip gesture classification for speed

        # Temporal buffering & Smoothing
        self._landmark_buffer = []
        self._finger_smoother = Point3DSmoother()
        # Pinch smoother: faster response for drawing (higher process variance)
        self._pinch_smoother = Point3DSmoother(
            process_variance=5e-4,   # Faster tracking
            measurement_variance=5e-4  # Less smoothing for responsiveness
        )
        self._hand_lost_count = 0
        self._grace_period = 10
        self._is_pinching = False  # Current pinch state
        self._pinch_close_frames = 0
        self._pinch_open_frames = 0
        self._last_pinch_point: tuple[float, float, float] | None = None
        self._last_pinch_emit_time = 0.0
        self._last_finger_emit_time = 0.0

    def set_emit_frames(self, enabled: bool):
        """Toggle webcam frame emission for the live preview."""
        self._emit_frames = enabled

    def set_drawing_mode(self, enabled: bool):
        """
        Toggle drawing mode. When active, gesture classification is skipped
        for lower latency, and pinch tracking gets priority.
        """
        self._drawing_mode = enabled

    def load_model(self) -> bool:
        """Load the trained gesture model and class mapping."""
        try:
            model_file = _resolve_asset("gesture_model.pkl")
            scaler_file = _resolve_asset("gesture_scaler.pkl")
            class_map_file = _resolve_asset("class_map.json")
            hand_model = _resolve_asset("hand_landmarker.task")

            if model_file is None:
                self.error.emit("Gesture model not found. Run training first.")
                return False

            if hand_model is None:
                try:
                    target_dir = _preferred_gesture_dir()
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_file = target_dir / "hand_landmarker.task"
                    self.status_changed.emit("Downloading hand landmark model...")
                    with urllib.request.urlopen(HAND_MODEL_URL, timeout=20) as response:
                        with open(target_file, "wb") as out:
                            out.write(response.read())
                    hand_model = target_file
                except Exception as e:
                    self.error.emit(f"hand_landmarker.task missing and download failed: {e}")
                    return False

            self._hand_model_path = hand_model

            with open(model_file, "rb") as f:
                model_data = pickle.load(f)
            self._model = model_data["model"]
            self._class_names = model_data["class_names"]
            self._needs_scaling = model_data.get("needs_scaling", False)

            if self._needs_scaling:
                if scaler_file is None:
                    self.error.emit("Scaler file missing but model requires scaling.")
                    return False
                with open(scaler_file, "rb") as f:
                    self._scaler = pickle.load(f)
            else:
                self._scaler = None

            if class_map_file is not None:
                with open(class_map_file, "r") as f:
                    class_map = json.load(f)
                self._class_to_action = class_map.get("class_to_action", {})
            else:
                self._class_to_action = {name: "none" for name in self._class_names}

            self.status_changed.emit(f"Model loaded: {len(self._class_names)} gestures")
            return True

        except Exception as e:
            self.error.emit(f"Failed to load model: {e}")
            return False

    def run(self):
        """Main tracking loop — runs in a separate thread."""
        self.status_changed.emit("Loading AI Model...")
        if not self.load_model():
            self.error.emit("Failed to load gesture classifier model")
            return

        self._running = True

        self.status_changed.emit("Opening Webcam...")
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.error.emit(f"Could not open webcam (index {self.camera_index})")
            return

        # Set camera resolution for performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        self.status_changed.emit("Initializing AI Backend...")
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(self._hand_model_path)),
            running_mode=RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        try:
            detector = HandLandmarker.create_from_options(options)
            self.status_changed.emit("Ready")
        except Exception as e:
            self.error.emit(f"AI Initialization failed: {e}")
            return

        last_gesture = ""
        last_trigger_time = 0
        consecutive_predictions = []
        frame_count = 0

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    continue

                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                result = detector.detect(mp_image)

                detected_landmarks = None

                if result.hand_landmarks:
                    if self._hand_lost_count > 0:
                        self.hand_found.emit()
                    self._hand_lost_count = 0
                    hand_lms = result.hand_landmarks[0]
                    detected_landmarks = hand_lms

                    # ── Pinch Detection (always runs, geometry-only) ──
                    thumb_tip = hand_lms[THUMB_TIP]
                    index_tip = hand_lms[INDEX_TIP]

                    # Distance between thumb tip and index tip
                    pinch_dist = math.sqrt(
                        (thumb_tip.x - index_tip.x) ** 2 +
                        (thumb_tip.y - index_tip.y) ** 2 +
                        (thumb_tip.z - index_tip.z) ** 2
                    )

                    # Frame-confirmed hysteresis pinch detection
                    if pinch_dist < self.PINCH_THRESHOLD:
                        self._pinch_close_frames += 1
                        self._pinch_open_frames = 0
                    elif pinch_dist > self.PINCH_RELEASE_THRESHOLD:
                        self._pinch_open_frames += 1
                        self._pinch_close_frames = 0
                    else:
                        # Between thresholds: hold current state.
                        pass

                    if (not self._is_pinching and
                            self._pinch_close_frames >= self.PINCH_ENGAGE_FRAMES):
                        self._is_pinching = True
                        self._pinch_close_frames = 0

                    if (self._is_pinching and
                            self._pinch_open_frames >= self.PINCH_RELEASE_FRAMES):
                        self._is_pinching = False
                        self._pinch_open_frames = 0

                    # Pinch midpoint (where the "pen tip" is)
                    mid_x = (thumb_tip.x + index_tip.x) / 2.0
                    mid_y = (thumb_tip.y + index_tip.y) / 2.0
                    mid_z = (thumb_tip.z + index_tip.z) / 2.0

                    # Smooth the pinch point
                    sx, sy, sz = self._pinch_smoother.update(mid_x, mid_y, mid_z)
                    self._last_pinch_point = (sx, sy, sz)
                    now_emit = time.time()
                    if now_emit - self._last_pinch_emit_time >= self.UI_EMIT_INTERVAL:
                        self.pinch_moved.emit(sx, sy, sz, self._is_pinching)
                        self._last_pinch_emit_time = now_emit

                    # ── Gesture Classification (skip during active drawing) ──
                    if not (self._drawing_mode and self._is_pinching):
                        landmarks = self._normalize_landmarks(hand_lms)
                        if landmarks is not None:
                            gesture, confidence = self._classify(landmarks)

                            if gesture and confidence >= self.CONFIDENCE_THRESHOLD:
                                consecutive_predictions.append(gesture)
                                if len(consecutive_predictions) > self.STABILITY_COUNT:
                                    consecutive_predictions = consecutive_predictions[-self.STABILITY_COUNT:]

                                if (len(consecutive_predictions) >= self.STABILITY_COUNT and
                                        len(set(consecutive_predictions)) == 1):
                                    now = time.time()
                                    if (gesture != last_gesture or
                                            now - last_trigger_time >= self.DEBOUNCE_TIME):
                                        action = self._class_to_action.get(gesture, "none")
                                        if action != "none":
                                            self.gesture_detected.emit(
                                                gesture, action, confidence
                                            )
                                            last_gesture = gesture
                                            last_trigger_time = now
                            else:
                                consecutive_predictions.clear()

                            # Legacy finger tracking (still used for backward compat)
                            idx_tip = hand_lms[INDEX_TIP]
                            fsx, fsy, fsz = self._finger_smoother.update(
                                idx_tip.x, idx_tip.y, idx_tip.z
                            )
                            if now_emit - self._last_finger_emit_time >= self.UI_EMIT_INTERVAL:
                                self.finger_moved.emit(fsx, fsy, fsz)
                                self._last_finger_emit_time = now_emit

                            self._landmark_buffer.append(landmarks)
                            if len(self._landmark_buffer) > self.BUFFER_SIZE:
                                self._landmark_buffer.pop(0)

                    self._hand_lost_count = 0

                else:
                    consecutive_predictions.clear()
                    self._hand_lost_count += 1
                    if self._is_pinching or self._last_pinch_point is not None:
                        self._is_pinching = False
                        self._pinch_close_frames = 0
                        self._pinch_open_frames = 0
                        if self._last_pinch_point is not None:
                            px, py, pz = self._last_pinch_point
                            self.pinch_moved.emit(px, py, pz, False)
                    if self._hand_lost_count == self._grace_period:
                        self.hand_lost.emit()

                # Emit annotated frame for preview (every other frame for perf)
                frame_count += 1
                if self._emit_frames and frame_count % 2 == 0:
                    self._emit_annotated_frame(rgb_frame, detected_landmarks)

                # Lower sleep for reduced latency
                time.sleep(0.01)

        except Exception as e:
            self.error.emit(f"Tracking error: {e}")
        finally:
            detector.close()
            cap.release()
            self.status_changed.emit("Gesture tracking stopped")

    def _emit_annotated_frame(self, rgb_frame: np.ndarray, hand_landmarks):
        """Draw hand skeleton overlay and emit as QImage."""
        h, w, ch = rgb_frame.shape
        display = rgb_frame.copy()

        if hand_landmarks is not None:
            # Draw connections
            for (s, e) in HAND_CONNECTIONS:
                x1, y1 = int(hand_landmarks[s].x * w), int(hand_landmarks[s].y * h)
                x2, y2 = int(hand_landmarks[e].x * w), int(hand_landmarks[e].y * h)
                cv2.line(display, (x1, y1), (x2, y2), (240, 160, 48), 2, cv2.LINE_AA)

            # Draw landmarks
            for lm in hand_landmarks:
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(display, (cx, cy), 4, (255, 193, 118), -1, cv2.LINE_AA)
                cv2.circle(display, (cx, cy), 6, (240, 160, 48), 1, cv2.LINE_AA)

            # Highlight pinch point
            thumb = hand_landmarks[THUMB_TIP]
            index = hand_landmarks[INDEX_TIP]
            mid_x = int((thumb.x + index.x) / 2 * w)
            mid_y = int((thumb.y + index.y) / 2 * h)

            if self._is_pinching:
                # Green dot when pinching (drawing)
                cv2.circle(display, (mid_x, mid_y), 10, (48, 255, 100), -1, cv2.LINE_AA)
                cv2.circle(display, (mid_x, mid_y), 12, (255, 255, 255), 2, cv2.LINE_AA)
                # Draw line between thumb and index
                tx, ty = int(thumb.x * w), int(thumb.y * h)
                ix, iy = int(index.x * w), int(index.y * h)
                cv2.line(display, (tx, ty), (ix, iy), (48, 255, 100), 3, cv2.LINE_AA)
            else:
                # Orange dot when not pinching
                cv2.circle(display, (mid_x, mid_y), 8, (240, 160, 48), -1, cv2.LINE_AA)

        # Convert to QImage
        bytes_per_line = ch * w
        q_img = QImage(display.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.frame_ready.emit(q_img.copy())

    def stop(self):
        """Stop the tracking loop."""
        self._running = False

    def _normalize_landmarks(self, hand_landmarks) -> np.ndarray | None:
        """Extract and normalize landmarks from MediaPipe Tasks results."""
        landmarks = []
        for lm in hand_landmarks:
            landmarks.extend([lm.x, lm.y, lm.z])

        arr = np.array(landmarks, dtype=np.float32)

        wrist = arr[:3].copy()
        for i in range(21):
            arr[i * 3]     -= wrist[0]
            arr[i * 3 + 1] -= wrist[1]
            arr[i * 3 + 2] -= wrist[2]

        distances = []
        for i in range(21):
            dx = arr[i * 3]
            dy = arr[i * 3 + 1]
            dist = np.sqrt(dx**2 + dy**2)
            distances.append(dist)
        max_dist = max(distances) if distances else 1.0
        if max_dist > 0:
            arr /= max_dist

        return arr

    def _classify(self, landmarks: np.ndarray) -> tuple[str, float]:
        """Classify landmarks into a gesture."""
        try:
            features = landmarks.reshape(1, -1)
            if self._needs_scaling:
                features = self._scaler.transform(features)
            prediction = self._model.predict(features)[0]
            probabilities = self._model.predict_proba(features)[0]
            confidence = float(probabilities[prediction])
            gesture_name = self._class_names[prediction]
            return gesture_name, confidence
        except Exception as e:
            return "", 0.0
