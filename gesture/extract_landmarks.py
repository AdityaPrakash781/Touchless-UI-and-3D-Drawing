"""
Gesture Landmark Extractor — Extract MediaPipe hand landmarks from HaGRID images.

Uses the MediaPipe Tasks API (HandLandmarker) to process images from the
HaGRID dataset, extract 21 hand landmarks (63 features: x, y, z per landmark),
and save them with gesture labels for classifier training.

Usage:
    python3 gesture/extract_landmarks.py

Output:
    gesture/landmarks_dataset.npz
"""

import os
import sys
import json
import numpy as np
import cv2
from pathlib import Path

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
)

# ── Config ────────────────────────────────────────────────────────

DATASET_ROOT = Path("/home/aditya/Documents/cv/dataset/hagrid-sample-120k-384p")
IMAGE_DIR = DATASET_ROOT / "hagrid_120k"
ANN_DIR = DATASET_ROOT / "ann_train_val"
GESTURE_DIR = Path(__file__).parent
MODEL_PATH = GESTURE_DIR / "hand_landmarker.task"
OUTPUT_FILE = GESTURE_DIR / "landmarks_dataset.npz"

# Gestures we want to use for media controls (subset of 18 HaGRID classes)
GESTURE_MAP = {
    "palm":      "palm",
    "fist":      "fist",
    "like":      "like",
    "dislike":   "dislike",
    "stop":      "stop",
    "peace":     "peace",
    "ok":        "ok",
    "one":       "one",
    "mute":      "mute",
    "call":      "call",
    "rock":      "rock",
    "two_up":    "two_up",
    "three":     "three",
    "four":      "four",
}

# How many images to sample per class (limit processing time)
MAX_IMAGES_PER_CLASS = 2000


def normalize_landmarks(landmarks_list) -> np.ndarray | None:
    """
    Convert MediaPipe NormalizedLandmark list to a normalized (63,) array.
    
    Normalizes relative to wrist (landmark 0) and scales by max distance.
    """
    if not landmarks_list or len(landmarks_list) < 21:
        return None

    raw = []
    for lm in landmarks_list:
        raw.extend([lm.x, lm.y, lm.z])

    arr = np.array(raw, dtype=np.float32)

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


def extract_from_image(
    detector: HandLandmarker,
    image_path: str,
    bbox: list[float] | None = None
) -> np.ndarray | None:
    """
    Extract hand landmarks from one image using the Tasks API.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None

    h, w, _ = img.shape

    # Crop to bounding box if provided
    if bbox:
        bx, by, bw, bh = bbox
        pad = 0.3
        x1 = max(0, int((bx - pad * bw) * w))
        y1 = max(0, int((by - pad * bh) * h))
        x2 = min(w, int((bx + bw + pad * bw) * w))
        y2 = min(h, int((by + bh + pad * bh) * h))
        img = img[y1:y2, x1:x2]
        if img.size == 0:
            return None

    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Create MediaPipe Image
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

    # Detect
    result = detector.detect(mp_image)

    if not result.hand_landmarks:
        return None

    # Take first hand's landmarks
    hand_lms = result.hand_landmarks[0]
    return normalize_landmarks(hand_lms)


def process_dataset():
    """Process the full HaGRID dataset and extract landmarks."""

    if not MODEL_PATH.exists():
        print(f"❌ Model file not found: {MODEL_PATH}")
        print("   Download from: https://storage.googleapis.com/mediapipe-models/"
              "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task")
        sys.exit(1)

    # Create HandLandmarker
    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    detector = HandLandmarker.create_from_options(options)

    all_X = []
    all_y = []
    class_names = sorted(GESTURE_MAP.keys())
    class_to_idx = {name: idx for idx, name in enumerate(class_names)}

    print("=" * 60)
    print("  GestureVLC — Landmark Extraction from HaGRID Dataset")
    print("=" * 60)
    print(f"  Classes: {len(class_names)}")
    print(f"  Max images per class: {MAX_IMAGES_PER_CLASS}")
    print(f"  Output: {OUTPUT_FILE}")
    print("=" * 60)

    for gesture_class in class_names:
        ann_file = ANN_DIR / f"{gesture_class}.json"
        img_dir = IMAGE_DIR / f"train_val_{gesture_class}"

        if not ann_file.exists():
            print(f"  ⚠ Annotation file not found: {ann_file}")
            continue
        if not img_dir.exists():
            print(f"  ⚠ Image directory not found: {img_dir}")
            continue

        # Load annotations
        with open(ann_file, "r") as f:
            annotations = json.load(f)

        image_ids = list(annotations.keys())[:MAX_IMAGES_PER_CLASS]
        success_count = 0
        total_count = len(image_ids)

        print(f"\n  📂 Processing '{gesture_class}' ({total_count} images)...")

        for idx, image_id in enumerate(image_ids):
            img_path = img_dir / f"{image_id}.jpg"
            if not img_path.exists():
                continue

            ann = annotations[image_id]
            labels = ann.get("labels", [])
            bboxes = ann.get("bboxes", [])

            # Find the bbox for the gesture (not "no_gesture")
            bbox = None
            for label, box in zip(labels, bboxes):
                if label == gesture_class:
                    bbox = box
                    break

            landmarks = extract_from_image(detector, str(img_path), bbox)

            if landmarks is not None:
                all_X.append(landmarks)
                all_y.append(class_to_idx[gesture_class])
                success_count += 1

            if (idx + 1) % 200 == 0:
                print(f"    ... {idx + 1}/{total_count} processed, "
                      f"{success_count} landmarks extracted")

        print(f"  ✅ '{gesture_class}': {success_count}/{total_count} "
              f"landmarks extracted")

    detector.close()

    # Save dataset
    X = np.array(all_X, dtype=np.float32)
    y = np.array(all_y, dtype=np.int32)

    np.savez(
        str(OUTPUT_FILE),
        X=X, y=y,
        class_names=np.array(class_names),
    )

    print(f"\n{'=' * 60}")
    print(f"  Dataset saved to: {OUTPUT_FILE}")
    print(f"  Total samples: {len(X)}")
    print(f"  Feature shape: {X.shape}")
    print(f"  Classes: {class_names}")
    print(f"{'=' * 60}")

    return X, y, class_names


if __name__ == "__main__":
    process_dataset()
