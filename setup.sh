#!/bin/bash
# ──────────────────────────────────────────────────────────────────
# GestureVLC — Automated Setup Script
# ──────────────────────────────────────────────────────────────────
# Installs system dependencies, Python packages, downloads the
# hand landmark model, and optionally trains the gesture classifier.
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
# ──────────────────────────────────────────────────────────────────

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     GestureVLC — Setup & Installation          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: Detect OS and install system dependencies ──

echo -e "${YELLOW}[1/6]${NC} Detecting OS and installing system dependencies..."

install_vlc() {
    if command -v pacman &>/dev/null; then
        echo -e "  ${GREEN}→${NC} Arch Linux detected (pacman)"
        sudo pacman -S --noconfirm --needed vlc python python-pip python-virtualenv
    elif command -v apt &>/dev/null; then
        echo -e "  ${GREEN}→${NC} Debian/Ubuntu detected (apt)"
        sudo apt update
        sudo apt install -y vlc python3 python3-pip python3-venv
    elif command -v dnf &>/dev/null; then
        echo -e "  ${GREEN}→${NC} Fedora/RHEL detected (dnf)"
        sudo dnf install -y vlc python3 python3-pip python3-virtualenv
    elif command -v brew &>/dev/null; then
        echo -e "  ${GREEN}→${NC} macOS detected (Homebrew)"
        brew install --cask vlc
        brew install python
    else
        echo -e "  ${RED}⚠${NC} Could not detect package manager."
        echo -e "  Please install VLC and Python 3.10+ manually."
    fi
}

# Check if VLC is installed
if ! command -v vlc &>/dev/null; then
    echo -e "  ${YELLOW}VLC not found. Installing...${NC}"
    install_vlc
else
    echo -e "  ${GREEN}✓${NC} VLC already installed"
fi

# Check Python version
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION found"

# ── Step 2: Create virtual environment ──

echo ""
echo -e "${YELLOW}[2/6]${NC} Creating virtual environment..."

if [ ! -d ".venv" ]; then
    $PYTHON_CMD -m venv .venv
    echo -e "  ${GREEN}✓${NC} Virtual environment created"
else
    echo -e "  ${GREEN}✓${NC} Virtual environment already exists"
fi

source .venv/bin/activate

# ── Step 3: Install Python dependencies ──

echo ""
echo -e "${YELLOW}[3/6]${NC} Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "  ${GREEN}✓${NC} All Python packages installed"

# ── Step 4: Download MediaPipe hand landmark model ──

echo ""
echo -e "${YELLOW}[4/6]${NC} Downloading MediaPipe hand landmark model..."

MODEL_PATH="gesture/hand_landmarker.task"
MODEL_URL="https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"

if [ ! -f "$MODEL_PATH" ]; then
    curl -sSL -o "$MODEL_PATH" "$MODEL_URL"
    echo -e "  ${GREEN}✓${NC} Model downloaded ($(du -h "$MODEL_PATH" | cut -f1))"
else
    echo -e "  ${GREEN}✓${NC} Model already downloaded"
fi

# ── Step 5: Gesture model training (optional) ──

echo ""
echo -e "${YELLOW}[5/6]${NC} Gesture classifier setup..."

if [ -f "gesture/gesture_model.pkl" ]; then
    echo -e "  ${GREEN}✓${NC} Trained gesture model found"
else
    echo -e "  ${YELLOW}⚠${NC} No trained gesture model found."
    echo ""
    echo -e "  To train the gesture classifier, you need the HaGRID dataset."
    echo -e "  Download from: ${CYAN}https://github.com/hukenovs/hagrid${NC}"
    echo ""
    echo -e "  After downloading, place it at:"
    echo -e "    ${CYAN}dataset/hagrid-sample-120k-384p/${NC}"
    echo ""
    echo -e "  Then run:"
    echo -e "    ${CYAN}python3 gesture/extract_landmarks.py${NC}"
    echo -e "    ${CYAN}python3 gesture/train_classifier.py${NC}"
    echo ""
    echo -e "  Or use a pre-trained model from the project releases."
fi

# ── Step 6: Done! ──

echo ""
echo -e "${YELLOW}[6/6]${NC} Verifying installation..."

$PYTHON_CMD -c "import vlc; print(f'  VLC: {vlc.libvlc_get_version().decode()}')" 2>/dev/null || echo -e "  ${RED}⚠${NC} python-vlc import failed"
$PYTHON_CMD -c "import PyQt6; print(f'  PyQt6: OK')" 2>/dev/null || echo -e "  ${RED}⚠${NC} PyQt6 import failed"
$PYTHON_CMD -c "import yt_dlp; print(f'  yt-dlp: {yt_dlp.version.__version__}')" 2>/dev/null || echo -e "  ${RED}⚠${NC} yt-dlp import failed"
$PYTHON_CMD -c "import mediapipe; print(f'  MediaPipe: {mediapipe.__version__}')" 2>/dev/null || echo -e "  ${RED}⚠${NC} mediapipe import failed"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Setup Complete!                             ║${NC}"
echo -e "${GREEN}║                                                ║${NC}"
echo -e "${GREEN}║  To run GestureVLC:                            ║${NC}"
echo -e "${GREEN}║    source .venv/bin/activate                   ║${NC}"
echo -e "${GREEN}║    python3 main.py                             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
