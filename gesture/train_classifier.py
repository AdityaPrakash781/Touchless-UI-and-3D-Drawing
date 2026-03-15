"""
Gesture Classifier — Train a model on MediaPipe hand landmarks.

Trains a Random Forest + MLP ensemble on the extracted landmarks 
from extract_landmarks.py and saves the best model.

Usage:
    python3 gesture/train_classifier.py

Output:
    gesture/gesture_model.pkl — Trained classifier
    gesture/training_report.txt — Classification report
"""

import os
import sys
import numpy as np
import pickle
import json
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score
)


# ── Config ────────────────────────────────────────────────────────

GESTURE_DIR = Path(__file__).parent
LANDMARKS_FILE = GESTURE_DIR / "landmarks_dataset.npz"
MODEL_FILE = GESTURE_DIR / "gesture_model.pkl"
SCALER_FILE = GESTURE_DIR / "gesture_scaler.pkl"
REPORT_FILE = GESTURE_DIR / "training_report.txt"
CLASS_MAP_FILE = GESTURE_DIR / "class_map.json"

# Gesture → media control action mapping
GESTURE_ACTIONS = {
    "palm":      "play_pause",       # Open palm → Toggle play/pause
    "fist":      "stop",             # Closed fist → Stop
    "like":      "volume_up",        # Thumbs up → Volume up
    "dislike":   "volume_down",      # Thumbs down → Volume down
    "stop":      "pause",            # Stop hand (facing camera) → Pause
    "peace":     "forward",          # Peace sign → Forward 10s
    "ok":        "speed_cycle",      # OK sign → Cycle speed
    "one":       "forward_skip",     # Pointing one finger → Forward
    "mute":      "mute_toggle",      # Mute gesture → Mute/unmute
    "call":      "none",             # Call gesture → No action
    "rock":      "fullscreen",       # Rock sign → Fullscreen toggle
    "two_up":    "rewind",           # Two fingers up → Rewind 10s
    "three":     "none",             # Three fingers → No action
    "four":      "none",             # Four fingers → No action
}


def load_dataset():
    """Load the extracted landmarks dataset."""
    if not LANDMARKS_FILE.exists():
        print(f"❌ Landmarks dataset not found: {LANDMARKS_FILE}")
        print("   Run extract_landmarks.py first.")
        sys.exit(1)

    data = np.load(str(LANDMARKS_FILE), allow_pickle=True)
    X = data["X"]
    y = data["y"]
    class_names = list(data["class_names"])

    print(f"  Loaded dataset: {X.shape[0]} samples, {X.shape[1]} features")
    print(f"  Classes: {class_names}")

    # Print class distribution
    unique, counts = np.unique(y, return_counts=True)
    for cls_idx, count in zip(unique, counts):
        print(f"    {class_names[cls_idx]:20s}: {count:6d} samples")

    return X, y, class_names


def train_model(X, y, class_names):
    """
    Train multiple classifiers and select the best one.
    
    Returns:
        (best_model, scaler, accuracy, report)
    """
    print("\n" + "=" * 60)
    print("  Training Gesture Classifier")
    print("=" * 60)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n  Train set: {len(X_train)} samples")
    print(f"  Test set:  {len(X_test)} samples")

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ── Models to try ──
    models = {
        "Random Forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=30,
            min_samples_split=5,
            min_samples_leaf=2,
            n_jobs=-1,
            random_state=42,
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=150,
            max_depth=8,
            learning_rate=0.1,
            random_state=42,
        ),
        "MLP Neural Net": MLPClassifier(
            hidden_layer_sizes=(256, 128, 64),
            activation="relu",
            solver="adam",
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.1,
            random_state=42,
        ),
    }

    best_model = None
    best_accuracy = 0
    best_name = ""
    all_results = {}

    for name, model in models.items():
        print(f"\n  🔄 Training {name}...")

        # Use scaled data for MLP, raw for tree-based
        if "MLP" in name:
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            cv_scores = cross_val_score(model, X_train, y_train, cv=5)

        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(
            y_test, y_pred,
            target_names=class_names,
            output_dict=True,
        )

        print(f"  ✅ {name}: accuracy = {accuracy:.4f}, "
              f"CV mean = {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

        all_results[name] = {
            "accuracy": accuracy,
            "cv_mean": cv_scores.mean(),
            "cv_std": cv_scores.std(),
            "report": report,
        }

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model = model
            best_name = name

    # ── Generate report ──
    print(f"\n  🏆 Best model: {best_name} (accuracy: {best_accuracy:.4f})")

    # Get predictions from best model
    if "MLP" in best_name:
        y_pred_best = best_model.predict(X_test_scaled)
    else:
        y_pred_best = best_model.predict(X_test)

    report_str = classification_report(
        y_test, y_pred_best, target_names=class_names
    )
    conf_matrix = confusion_matrix(y_test, y_pred_best)

    # Save report
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("GestureVLC — Gesture Classifier Training Report\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Best Model: {best_name}\n")
        f.write(f"Test Accuracy: {best_accuracy:.4f}\n\n")
        f.write("Classification Report:\n")
        f.write(report_str + "\n\n")
        f.write("Model Comparison:\n")
        f.write("-" * 60 + "\n")
        for name, result in all_results.items():
            f.write(f"  {name:20s}: acc={result['accuracy']:.4f}, "
                    f"CV={result['cv_mean']:.4f}±{result['cv_std']:.4f}\n")
        f.write("\nConfusion Matrix:\n")
        f.write(str(conf_matrix) + "\n")
        f.write(f"\nGesture → Action Mapping:\n")
        f.write("-" * 60 + "\n")
        for gesture, action in GESTURE_ACTIONS.items():
            f.write(f"  {gesture:20s} → {action}\n")

    print(f"\n  📄 Report saved to: {REPORT_FILE}")

    return best_model, scaler, best_accuracy, report_str, best_name


def save_model(model, scaler, class_names, model_name):
    """Save the trained model, scaler, and class mapping."""
    # Save model
    model_data = {
        "model": model,
        "model_name": model_name,
        "class_names": class_names,
        "needs_scaling": "MLP" in model_name,
    }
    with open(MODEL_FILE, "wb") as f:
        pickle.dump(model_data, f)
    print(f"  💾 Model saved to: {MODEL_FILE}")

    # Save scaler
    with open(SCALER_FILE, "wb") as f:
        pickle.dump(scaler, f)
    print(f"  💾 Scaler saved to: {SCALER_FILE}")

    # Save class map
    class_map = {
        "class_names": class_names,
        "gesture_actions": GESTURE_ACTIONS,
        "class_to_action": {
            name: GESTURE_ACTIONS.get(name, "none") for name in class_names
        },
    }
    with open(CLASS_MAP_FILE, "w") as f:
        json.dump(class_map, f, indent=2)
    print(f"  💾 Class map saved to: {CLASS_MAP_FILE}")


def main():
    print("=" * 60)
    print("  GestureVLC — Gesture Classifier Training")
    print("=" * 60)

    X, y, class_names = load_dataset()
    model, scaler, accuracy, report, model_name = train_model(X, y, class_names)

    print(f"\n{report}")

    save_model(model, scaler, class_names, model_name)

    print(f"\n{'=' * 60}")
    print(f"  Training complete!")
    print(f"  Best model: {model_name} — Accuracy: {accuracy:.4f}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
