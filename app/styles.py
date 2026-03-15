# Complete replacement of app/styles.py
"""
Dark-mode QSS stylesheet for GestureVLC.

Modern dark theme with vibrant blue accents and premium aesthetic.
"""

# Premium Modern Color Palette
COLORS = {
    "bg_primary": "#0B0F19",       # Deep charcoal blue (Main window bg)
    "bg_secondary": "#131B2F",     # Tab widget and sidebar background
    "bg_tertiary": "#1D283A",      # Cards, dropdowns, elevated panels
    "bg_hover": "#25344A",         # Buttons/Items on hover
    "bg_active": "#3B82F633",      # Soft translucent blue for active states
    "border": "#2E3B52",           # Soft border colors to separate panels
    "text_primary": "#F1F5F9",     # Crisp bright text
    "text_secondary": "#94A3B8",   # Subtle muted text
    "text_tertiary": "#64748B",    # Placeholders, disabled text
    "accent": "#3B82F6",           # Vibrant Blue (Primary branding)
    "accent_hover": "#60A5FA",     # Lighter blue for hover glowing
    "accent_dark": "#2563EB",      # Deeper blue for active press
    "success": "#10B981",          # Emerald Green
    "warning": "#F59E0B",          # Amber
    "danger": "#EF4444",           # Rose Red
    "slider_bg": "#1E293B",        # Slider track
    "slider_handle": "#60A5FA",    # Slider glowing handle
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
    padding: 4px 6px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    border-radius: 6px;
}}
QMenuBar::item:selected {{
    background-color: {COLORS["bg_hover"]};
}}
QMenu {{
    background-color: {COLORS["bg_tertiary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 30px 8px 24px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {COLORS["accent"]};
}}

/* ── Push Buttons ────────────────────────────────────────────────── */
QPushButton {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 8px 18px;
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
    background-color: transparent;
}}
QPushButton#accentButton {{
    background-color: {COLORS["accent"]};
    border-color: {COLORS["accent"]};
    color: white;
    font-weight: 600;
}}
QPushButton#accentButton:hover {{
    background-color: {COLORS["accent_hover"]};
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
    color: {COLORS["accent_hover"]};
}}
QPushButton#playBtn {{
    background-color: {COLORS["accent"]};
    border-radius: 24px;
    min-width: 48px;
    min-height: 48px;
    font-size: 22px;
}}
QPushButton#playBtn:hover {{
    background-color: {COLORS["accent_hover"]};
}}

/* ── Line Edits ──────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    selection-background-color: {COLORS["accent"]};
}}
QLineEdit:focus {{
    border-color: {COLORS["accent"]};
    background-color: {COLORS["bg_primary"]};
}}
QLineEdit::placeholder {{
    color: {COLORS["text_tertiary"]};
}}

/* ── Sliders ─────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    background: {COLORS["slider_bg"]};
    height: 8px;
    border-radius: 4px;
}}
QSlider::handle:horizontal {{
    background: {COLORS["slider_handle"]};
    width: 18px;
    height: 18px;
    margin: -5px 0;
    border-radius: 9px;
}}
QSlider::handle:horizontal:hover {{
    background: #FFFFFF;
    width: 20px;
    height: 20px;
    margin: -6px 0;
    border-radius: 10px;
}}
QSlider::sub-page:horizontal {{
    background: {COLORS["accent"]};
    border-radius: 4px;
}}

/* ── Volume slider (vertical) ────────────────────────────────────── */
QSlider::groove:vertical {{
    background: {COLORS["slider_bg"]};
    width: 8px;
    border-radius: 4px;
}}
QSlider::handle:vertical {{
    background: {COLORS["slider_handle"]};
    width: 18px;
    height: 18px;
    margin: 0 -5px;
    border-radius: 9px;
}}
QSlider::sub-page:vertical {{
    background: {COLORS["accent"]};
    border-radius: 4px;
}}

/* ── Combo Boxes ─────────────────────────────────────────────────── */
QComboBox {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 8px 12px;
    min-width: 90px;
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
    border-radius: 8px;
    selection-background-color: {COLORS["accent"]};
    padding: 4px;
}}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel {{
    color: {COLORS["text_primary"]};
}}
QLabel#secondaryLabel {{
    color: {COLORS["text_secondary"]};
    font-size: 13px;
}}
QLabel#titleLabel {{
    font-size: 15px;
    font-weight: 600;
    color: {COLORS["text_primary"]};
}}
QLabel#statusLabel {{
    color: {COLORS["accent_hover"]};
    font-size: 13px;
    font-weight: 600;
}}

/* ── Tab Widget ──────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    background: {COLORS["bg_secondary"]};
    margin-top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {COLORS["text_secondary"]};
    border: none;
    padding: 12px 24px;
    margin-right: 4px;
    font-weight: 600;
    font-size: 14px;
    border-bottom: 3px solid transparent;
}}
QTabBar::tab:selected {{
    color: {COLORS["accent"]};
    border-bottom: 3px solid {COLORS["accent"]};
}}
QTabBar::tab:hover:!selected {{
    color: {COLORS["text_primary"]};
    background: {COLORS["bg_hover"]};
    border-bottom: 3px solid {COLORS["border"]};
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}

/* ── Scroll Bars ─────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS["border"]};
    border-radius: 5px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS["text_tertiary"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS["border"]};
    border-radius: 5px;
    min-width: 40px;
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
    border: 2px solid {COLORS["border"]};
    border-radius: 12px;
    margin-top: 24px;
    padding: 16px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: {COLORS["accent"]};
    font-weight: 600;
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
    background-color: {COLORS["bg_primary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["accent"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
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
    /* Warning: VLC on Wayland/X11 can break if we clip rounded corners */
}}

/* ── Search Result Card ──────────────────────────────────────────── */
QFrame#resultCard {{
    background-color: {COLORS["bg_tertiary"]};
    border: 1px solid transparent;
    border-radius: 12px;
    padding: 14px;
}}
QFrame#resultCard:hover {{
    border-color: {COLORS["accent"]};
    background-color: {COLORS["bg_hover"]};
}}
"""
