"""
Real-time Gesture Tracker — Webcam hand gesture recognition.

Uses MediaPipe Tasks API (HandLandmarker) for landmark extraction
and the trained classifier for gesture recognition in real-time.
"""

import sys
import time
import numpy as np
import pickle
import json
import cv2
from pathlib import Path

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
)

from PyQt6.QtCore import QThread, pyqtSignal


GESTURE_DIR = Path(__file__).parent
MODEL_FILE = GESTURE_DIR / "gesture_model.pkl"
SCALER_FILE = GESTURE_DIR / "gesture_scaler.pkl"
CLASS_MAP_FILE = GESTURE_DIR / "class_map.json"
HAND_MODEL = GESTURE_DIR / "hand_landmarker.task"


class GestureTracker(QThread):
    """
    Real-time gesture recognition thread.
    
    Captures webcam frames, extracts hand landmarks via MediaPipe Tasks API,
    classifies gestures, and emits action signals.
    
    Signals:
        gesture_detected(str, str, float): (gesture_name, action, confidence)
        status_changed(str): Status message updates
        error(str): Error messages
    """

    gesture_detected = pyqtSignal(str, str, float)
    status_changed = pyqtSignal(str)
    error = pyqtSignal(str)

    DEBOUNCE_TIME = 1.5
    CONFIDENCE_THRESHOLD = 0.65
    STABILITY_COUNT = 3

    def __init__(self, camera_index: int = 0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self._running = False
        self._model = None
        self._scaler = None
        self._class_names = []
        self._class_to_action = {}
        self._needs_scaling = False

    def load_model(self) -> bool:
        """Load the trained gesture model and class mapping."""
        try:
            if not MODEL_FILE.exists():
                self.error.emit("Gesture model not found. Run training first.")
                return False
            if not HAND_MODEL.exists():
                self.error.emit("hand_landmarker.task not found in gesture/ dir.")
                return False

            with open(MODEL_FILE, "rb") as f:
                model_data = pickle.load(f)
            self._model = model_data["model"]
            self._class_names = model_data["class_names"]
            self._needs_scaling = model_data.get("needs_scaling", False)

            with open(SCALER_FILE, "rb") as f:
                self._scaler = pickle.load(f)

            if CLASS_MAP_FILE.exists():
                with open(CLASS_MAP_FILE, "r") as f:
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
        if not self.load_model():
            return

        self._running = True
        self.status_changed.emit("Starting webcam...")

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self.error.emit(f"Could not open webcam (index {self.camera_index})")
            return

        # Create HandLandmarker with Tasks API
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(HAND_MODEL)),
            running_mode=RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        detector = HandLandmarker.create_from_options(options)

        self.status_changed.emit("Gesture tracking active 🤚")

        last_gesture = ""
        last_trigger_time = 0
        consecutive_predictions = []

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    continue

                # Flip for mirror effect
                frame = cv2.flip(frame, 1)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Create MediaPipe Image
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                result = detector.detect(mp_image)

                if result.hand_landmarks:
                    hand_lms = result.hand_landmarks[0]

                    # Extract landmarks
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
                else:
                    consecutive_predictions.clear()

                time.sleep(0.03)

        except Exception as e:
            self.error.emit(f"Tracking error: {e}")
        finally:
            detector.close()
            cap.release()
            self.status_changed.emit("Gesture tracking stopped")

    def stop(self):
        """Stop the tracking loop."""
        self._running = False

    def _normalize_landmarks(self, hand_landmarks) -> np.ndarray | None:
        """Extract and normalize landmarks from MediaPipe Tasks results."""
        landmarks = []
        for lm in hand_landmarks:
            landmarks.extend([lm.x, lm.y, lm.z])

        arr = np.array(landmarks, dtype=np.float32)

        # Normalize relative to wrist
        wrist = arr[:3].copy()
        for i in range(21):
            arr[i * 3]     -= wrist[0]
            arr[i * 3 + 1] -= wrist[1]
            arr[i * 3 + 2] -= wrist[2]

        # Scale normalize
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
        except Exception:
            return "", 0.0
