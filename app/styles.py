"""
Dark-mode QSS stylesheet for GestureVLC.

Modern dark theme with accent colors and smooth visual styling.
"""

# Color palette
COLORS = {
    "bg_primary": "#0d1117",       # Main background (deep dark)
    "bg_secondary": "#161b22",     # Sidebar / panels
    "bg_tertiary": "#21262d",      # Cards / elevated surfaces
    "bg_hover": "#30363d",         # Hover state
    "bg_active": "#1f6feb22",      # Active/selected (translucent blue)
    "border": "#30363d",           # Subtle borders
    "text_primary": "#e6edf3",     # Main text
    "text_secondary": "#8b949e",   # Muted text
    "text_tertiary": "#6e7681",    # Disabled text
    "accent": "#58a6ff",           # Primary accent (blue)
    "accent_hover": "#79c0ff",     # Accent hover
    "accent_dark": "#1f6feb",      # Accent darker
    "success": "#3fb950",          # Green
    "warning": "#d29922",          # Yellow
    "danger": "#f85149",           # Red
    "slider_bg": "#30363d",        # Slider track
    "slider_handle": "#58a6ff",    # Slider handle
}

STYLESHEET = f"""
/* ── Global ──────────────────────────────────────────────────────── */
QMainWindow, QWidget {{
    background-color: {COLORS["bg_primary"]};
    color: {COLORS["text_primary"]};
    font-family: "Inter", "Segoe UI", "SF Pro Display", system-ui, sans-serif;
    font-size: 13px;
}}

/* ── Menu Bar ────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {COLORS["bg_secondary"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 2px 0;
}}
QMenuBar::item {{
    padding: 6px 12px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {COLORS["bg_hover"]};
}}
QMenu {{
    background-color: {COLORS["bg_tertiary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {COLORS["accent_dark"]};
}}

/* ── Push Buttons ────────────────────────────────────────────────── */
QPushButton {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {COLORS["bg_hover"]};
    border-color: {COLORS["accent"]};
}}
QPushButton:pressed {{
    background-color: {COLORS["accent_dark"]};
}}
QPushButton:disabled {{
    color: {COLORS["text_tertiary"]};
    border-color: {COLORS["border"]};
}}
QPushButton#accentButton {{
    background-color: {COLORS["accent_dark"]};
    border-color: {COLORS["accent"]};
    color: white;
}}
QPushButton#accentButton:hover {{
    background-color: {COLORS["accent"]};
}}

/* ── Transport Control Buttons ───────────────────────────────────── */
QPushButton#transportBtn {{
    background: transparent;
    border: none;
    border-radius: 20px;
    padding: 8px;
    font-size: 18px;
    min-width: 40px;
    min-height: 40px;
}}
QPushButton#transportBtn:hover {{
    background-color: {COLORS["bg_hover"]};
}}
QPushButton#playBtn {{
    background-color: {COLORS["accent_dark"]};
    border-radius: 22px;
    min-width: 44px;
    min-height: 44px;
    font-size: 20px;
}}
QPushButton#playBtn:hover {{
    background-color: {COLORS["accent"]};
}}

/* ── Line Edits ──────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    selection-background-color: {COLORS["accent_dark"]};
}}
QLineEdit:focus {{
    border-color: {COLORS["accent"]};
}}
QLineEdit::placeholder {{
    color: {COLORS["text_tertiary"]};
}}

/* ── Sliders ─────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    background: {COLORS["slider_bg"]};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {COLORS["slider_handle"]};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {COLORS["accent_hover"]};
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}}
QSlider::sub-page:horizontal {{
    background: {COLORS["accent"]};
    border-radius: 3px;
}}

/* ── Volume slider (vertical) ────────────────────────────────────── */
QSlider::groove:vertical {{
    background: {COLORS["slider_bg"]};
    width: 6px;
    border-radius: 3px;
}}
QSlider::handle:vertical {{
    background: {COLORS["slider_handle"]};
    width: 16px;
    height: 16px;
    margin: 0 -5px;
    border-radius: 8px;
}}
QSlider::sub-page:vertical {{
    background: {COLORS["accent"]};
    border-radius: 3px;
}}

/* ── Combo Boxes ─────────────────────────────────────────────────── */
QComboBox {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 70px;
}}
QComboBox:hover {{
    border-color: {COLORS["accent"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS["bg_tertiary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    selection-background-color: {COLORS["accent_dark"]};
}}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel {{
    color: {COLORS["text_primary"]};
}}
QLabel#secondaryLabel {{
    color: {COLORS["text_secondary"]};
    font-size: 12px;
}}
QLabel#titleLabel {{
    font-size: 16px;
    font-weight: 600;
}}
QLabel#statusLabel {{
    color: {COLORS["accent"]};
    font-size: 12px;
    font-weight: 500;
}}

/* ── Tab Widget ──────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    background: {COLORS["bg_secondary"]};
    margin-top: -1px;
}}
QTabBar::tab {{
    background: {COLORS["bg_tertiary"]};
    color: {COLORS["text_secondary"]};
    border: 1px solid {COLORS["border"]};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 10px 20px;
    margin-right: 2px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background: {COLORS["bg_secondary"]};
    color: {COLORS["accent"]};
    border-bottom: 2px solid {COLORS["accent"]};
}}
QTabBar::tab:hover:!selected {{
    background: {COLORS["bg_hover"]};
    color: {COLORS["text_primary"]};
}}

/* ── Scroll Bars ─────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {COLORS["border"]};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS["text_tertiary"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS["border"]};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Scroll Area ─────────────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}

/* ── Group Box ───────────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    padding: 0 8px;
    color: {COLORS["accent"]};
}}

/* ── Status Bar ──────────────────────────────────────────────────── */
QStatusBar {{
    background: {COLORS["bg_secondary"]};
    border-top: 1px solid {COLORS["border"]};
    color: {COLORS["text_secondary"]};
    font-size: 12px;
}}

/* ── Tool Tips ───────────────────────────────────────────────────── */
QToolTip {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Frame Separator ─────────────────────────────────────────────── */
QFrame#separator {{
    background-color: {COLORS["border"]};
    max-height: 1px;
}}

/* ── Video Frame ─────────────────────────────────────────────────── */
QFrame#videoFrame {{
    background-color: #000000;
    border: none;
    border-radius: 8px;
}}

/* ── Search Result Card ──────────────────────────────────────────── */
QFrame#resultCard {{
    background-color: {COLORS["bg_tertiary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 12px;
}}
QFrame#resultCard:hover {{
    border-color: {COLORS["accent"]};
    background-color: {COLORS["bg_hover"]};
}}
"""
