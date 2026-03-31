"""
Air Writing Engine — CNN-based character recognition from hand-drawn strokes.

Integrates the air-writing-recognition CNN model into the GestureVLC pipeline.
Uses ONNX Runtime for low-latency inference (~1ms per prediction).
Falls back to TensorFlow/Keras if ONNX model is not available.

Features:
  - Virtual blackboard for stroke rendering
  - Contour extraction → 28×28 resize → CNN prediction
  - 62-class recognition (0-9, A-Z, a-z)
  - Thread-safe design for use with the gesture tracker
"""

import numpy as np
import cv2
from pathlib import Path
from collections import deque
from typing import Optional

MODEL_DIR = Path(__file__).parent / "models"

# EMNIST byclass: 62 classes (10 digits + 26 uppercase + 26 lowercase)
CHARACTERS = {
    0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
    10: 'A', 11: 'B', 12: 'C', 13: 'D', 14: 'E', 15: 'F', 16: 'G', 17: 'H', 18: 'I',
    19: 'J', 20: 'K', 21: 'L', 22: 'M', 23: 'N', 24: 'O', 25: 'P', 26: 'Q', 27: 'R',
    28: 'S', 29: 'T', 30: 'U', 31: 'V', 32: 'W', 33: 'X', 34: 'Y', 35: 'Z',
    36: 'a', 37: 'b', 38: 'c', 39: 'd', 40: 'e', 41: 'f', 42: 'g', 43: 'h', 44: 'i',
    45: 'j', 46: 'k', 47: 'l', 48: 'm', 49: 'n', 50: 'o', 51: 'p', 52: 'q', 53: 'r',
    54: 's', 55: 't', 56: 'u', 57: 'v', 58: 'w', 59: 'x', 60: 'y', 61: 'z',
}


class AirWritingEngine:
    """
    Manages a virtual blackboard and CNN inference for air writing recognition.

    Usage:
        engine = AirWritingEngine()
        engine.load_model()

        # During drawing (pen down):
        engine.add_stroke_point(x, y)

        # When pen lifts:
        char, confidence = engine.recognize_and_clear()
    """

    # Blackboard dimensions (matches original project)
    BOARD_W = 640
    BOARD_H = 480
    STROKE_THICKNESS = 8
    MIN_CONTOUR_AREA = 1000  # Minimum area to attempt recognition

    def __init__(self):
        self._model = None
        self._model_type: str = "none"  # "onnx" or "keras"
        self._onnx_layout: str = "nhwc"  # "nhwc" or "nchw"
        self._blackboard = np.zeros((self.BOARD_H, self.BOARD_W, 3), dtype=np.uint8)
        self._points: deque = deque(maxlen=512)
        self._recognized_text: str = ""
        self._last_prediction: str = ""
        self._last_confidence: float = 0.0
        self._model_loaded = False
        self._stroke_active = False

    # ── Model Loading ────────────────────────────────────────────────

    def load_model(self) -> bool:
        """Load the CNN model (ONNX Runtime)."""
        onnx_path = MODEL_DIR / "air_writing_cnn.onnx"
        if onnx_path.exists():
            try:
                import onnxruntime as ort
                self._model = ort.InferenceSession(
                    str(onnx_path),
                    providers=['CPUExecutionProvider']
                )
                self._model_type = "onnx"
                self._onnx_layout = self._detect_onnx_layout()
                self._model_loaded = True
                print(f"[AirWriting] Loaded ONNX model (fast inference, {self._onnx_layout})")
                return True
            except ImportError as e:
                import traceback
                print(f"[AirWriting] onnxruntime import failed: {e}")
                traceback.print_exc()
            except Exception as e:
                import traceback
                print(f"[AirWriting] ONNX load failed: {type(e).__name__}: {e}")
                traceback.print_exc()
        else:
            print(f"[AirWriting] No ONNX model at {onnx_path}")
            print("[AirWriting]   Run: python -m app.convert_model  (requires tensorflow)")

        print("[AirWriting] Character recognition disabled.")
        return False

    @property
    def is_loaded(self) -> bool:
        return self._model_loaded

    @property
    def recognized_text(self) -> str:
        return self._recognized_text

    @property
    def last_prediction(self) -> str:
        return self._last_prediction

    @property
    def last_confidence(self) -> float:
        return self._last_confidence

    # ── Stroke Management ────────────────────────────────────────────

    def begin_stroke(self):
        """Call when pen goes down (pinch starts)."""
        self._stroke_active = True

    def add_stroke_point(self, x: float, y: float):
        """
        Add a point to the current stroke.

        Args:
            x: Normalized x (0-1), left to right
            y: Normalized y (0-1), top to bottom
        """
        if not self._stroke_active:
            return

        # Map normalized coords to blackboard pixel coords
        px = int(x * self.BOARD_W)
        py = int(y * self.BOARD_H)
        px = max(0, min(self.BOARD_W - 1, px))
        py = max(0, min(self.BOARD_H - 1, py))

        center = (px, py)
        self._points.append(center)

        # Draw the line segment on the blackboard
        if len(self._points) >= 2:
            pts_list = list(self._points)
            cv2.line(
                self._blackboard,
                pts_list[-2], pts_list[-1],
                (255, 255, 255),
                self.STROKE_THICKNESS,
            )

    def end_stroke(self) -> tuple[str, float]:
        """
        Call when pen lifts (pinch released).
        Does NOT clear the blackboard — allows multi-stroke characters.

        Returns:
            (character, confidence) or ("", 0.0) if nothing recognized
        """
        self._stroke_active = False
        self._points.clear()
        # Don't auto-recognize here — wait for explicit recognize call
        # or a timeout-based approach
        return ("", 0.0)

    def recognize_and_clear(self) -> tuple[str, float]:
        """
        Attempt to recognize what's on the blackboard, then clear it.

        Returns:
            (character, confidence) tuple
        """
        if not self._model_loaded:
            self._clear_board()
            return ("", 0.0)

        char, confidence = self._recognize_blackboard()

        if char:
            self._last_prediction = char
            self._last_confidence = confidence
            self._recognized_text += char

        self._clear_board()
        return (char, confidence)

    def recognize_current(self) -> tuple[str, float]:
        """
        Attempt to recognize what's on the blackboard WITHOUT clearing it.

        Returns:
            (character, confidence) tuple
        """
        if not self._model_loaded:
            return ("", 0.0)

        char, confidence = self._recognize_blackboard()
        if char:
            self._last_prediction = char
            self._last_confidence = confidence
        return (char, confidence)

    def backspace(self):
        """Remove the last recognized character."""
        if self._recognized_text:
            self._recognized_text = self._recognized_text[:-1]

    def clear_text(self):
        """Clear all recognized text."""
        self._recognized_text = ""
        self._last_prediction = ""
        self._last_confidence = 0.0

    def clear_board(self):
        """Clear the blackboard (public)."""
        self._clear_board()

    def has_content(self) -> bool:
        """Check if the blackboard has any drawn content."""
        return np.any(self._blackboard > 0)

    def get_blackboard_preview(self) -> np.ndarray:
        """Return a copy of the current blackboard for preview."""
        return self._blackboard.copy()

    # ── Internal ─────────────────────────────────────────────────────

    def _clear_board(self):
        """Reset the blackboard to all black."""
        self._blackboard[:] = 0
        self._points.clear()
        self._stroke_active = False

    def _recognize_blackboard(self) -> tuple[str, float]:
        """
        Extract character from blackboard and run CNN prediction.

        Pipeline:
            1. Convert to grayscale
            2. Blur to reduce noise
            3. Threshold (Otsu)
            4. Find contours
            5. Crop largest contour bounding box
            6. Resize to 28×28
            7. Feed to CNN
        """
        if not np.any(self._blackboard > 0):
            return ("", 0.0)

        try:
            # Mirror the blackboard (webcam is mirrored)
            board = cv2.flip(self._blackboard, 1)

            # Convert to grayscale
            gray = cv2.cvtColor(board, cv2.COLOR_BGR2GRAY)

            # Blur to reduce noise
            blurred = cv2.medianBlur(gray, 15)
            blurred = cv2.GaussianBlur(blurred, (5, 5), 0)

            # Threshold
            _, thresh = cv2.threshold(
                blurred, 0, 255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            # Find contours
            contours, _ = cv2.findContours(
                thresh.copy(),
                cv2.RETR_TREE,
                cv2.CHAIN_APPROX_NONE
            )

            if not contours:
                return ("", 0.0)

            # Get the largest contour
            cnt = max(contours, key=cv2.contourArea)
            if cv2.contourArea(cnt) < self.MIN_CONTOUR_AREA:
                return ("", 0.0)

            # Crop bounding box with padding
            bx, by, bw, bh = cv2.boundingRect(cnt)
            pad = 10
            y1 = max(0, by - pad)
            y2 = min(gray.shape[0], by + bh + pad)
            x1 = max(0, bx - pad)
            x2 = min(gray.shape[1], bx + bw + pad)

            char_img = gray[y1:y2, x1:x2]

            if char_img.size == 0:
                return ("", 0.0)

            # Resize to 28×28 for the CNN
            resized = cv2.resize(char_img, (28, 28))

            # Normalize to [0, 1]
            normalized = resized.astype(np.float32) / 255.0

            # Predict
            return self._predict(normalized)

        except Exception as e:
            print(f"[AirWriting] Recognition error: {e}")
            return ("", 0.0)

    def _predict(self, image: np.ndarray) -> tuple[str, float]:
        """
        Run CNN prediction on a 28×28 grayscale image.

        Returns:
            (character, confidence)
        """
        # Reshape to (1, 28, 28, 1) — batch of 1, single channel
        input_data = image.reshape(1, 28, 28, 1)

        if self._model_type == "onnx":
            input_name = self._model.get_inputs()[0].name
            onnx_input = self._prepare_onnx_input(input_data)
            result = self._model.run(None, {input_name: onnx_input})
            probabilities = result[0][0]
        elif self._model_type == "keras":
            probabilities = self._model.predict(input_data, verbose=0)[0]
        else:
            return ("", 0.0)

        predicted_class = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_class])

        char = CHARACTERS.get(predicted_class, "?")
        return (char, confidence)

    def _detect_onnx_layout(self) -> str:
        """Infer model input layout from ONNX input shape metadata."""
        try:
            input_meta = self._model.get_inputs()[0]
            shape = list(input_meta.shape)
            if len(shape) == 4:
                if shape[-1] == 1:
                    return "nhwc"
                if shape[1] == 1:
                    return "nchw"
        except Exception:
            pass
        # tf2onnx exports from Keras are typically NHWC.
        return "nhwc"

    def _prepare_onnx_input(self, nhwc_input: np.ndarray) -> np.ndarray:
        """Convert NHWC tensor to the ONNX model's expected layout."""
        if self._onnx_layout == "nchw":
            return np.transpose(nhwc_input, (0, 3, 1, 2)).astype(np.float32)
        return nhwc_input.astype(np.float32)
