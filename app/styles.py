"""
GestureVLC — Premium Dark Theme Stylesheet

Designed with Stitch MCP — modern dark navy UI with electric blue accents,
glassmorphic surfaces, 12px roundness, and Inter typography.
"""

# ── Design Tokens (Stitch MCP design system) ─────────────────────

COLORS = {
    # Backgrounds — deep navy layering
    "bg_primary":     "#0b0e14",   # Deepest background
    "bg_secondary":   "#111620",   # Panels / sidebar
    "bg_tertiary":    "#1a1f2e",   # Cards / elevated surfaces
    "bg_surface":     "#1e2436",   # Input fields / combo boxes
    "bg_hover":       "#252c3d",   # Hover state
    "bg_active":      "#2d3548",   # Active/pressed state

    # Borders
    "border":         "#2a3040",   # Subtle
    "border_focus":   "#259df4",   # Focused element

    # Text
    "text_primary":   "#e8ecf4",   # Main text
    "text_secondary": "#8892a4",   # Muted
    "text_tertiary":  "#565e70",   # Disabled

    # Accent — electric blue
    "accent":         "#259df4",   # Primary accent
    "accent_hover":   "#60b8ff",   # Light accent
    "accent_dark":    "#1a7fd4",   # Darker accent

    # Semantic
    "success":        "#22c55e",
    "warning":        "#f59e0b",
    "danger":         "#ef4444",

    # Slider
    "slider_bg":      "#1e2436",
    "slider_handle":  "#60b8ff",
}

STYLESHEET = f"""
/* ═══════════════════════════════════════════════════════════════
   GestureVLC — Premium Dark Theme (Stitch MCP)
   ═══════════════════════════════════════════════════════════════ */

/* ── Global ──────────────────────────────────────────────────── */
QMainWindow {{
    background-color: {COLORS["bg_primary"]};
}}
QWidget {{
    background-color: transparent;
    color: {COLORS["text_primary"]};
    font-family: "Inter", "SF Pro Display", "Segoe UI", system-ui, sans-serif;
    font-size: 13px;
}}

/* ── Menu Bar ────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {COLORS["bg_secondary"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 4px 8px;
    spacing: 4px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    border-radius: 6px;
    color: {COLORS["text_secondary"]};
}}
QMenuBar::item:selected {{
    background-color: {COLORS["bg_hover"]};
    color: {COLORS["text_primary"]};
}}
QMenu {{
    background-color: {COLORS["bg_tertiary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 28px 8px 16px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background-color: {COLORS["accent_dark"]};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background: {COLORS["border"]};
    margin: 4px 8px;
}}

/* ── Push Buttons ────────────────────────────────────────────── */
QPushButton {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: 500;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {COLORS["bg_hover"]};
    border-color: {COLORS["accent"]};
    color: {COLORS["accent_hover"]};
}}
QPushButton:pressed {{
    background-color: {COLORS["bg_active"]};
    border-color: {COLORS["accent_dark"]};
}}
QPushButton:disabled {{
    color: {COLORS["text_tertiary"]};
    border-color: {COLORS["border"]};
    background-color: {COLORS["bg_secondary"]};
}}

/* Accent button (primary action) */
QPushButton#accentButton {{
    background-color: {COLORS["accent_dark"]};
    border: 1px solid {COLORS["accent"]};
    color: white;
    font-weight: 600;
}}
QPushButton#accentButton:hover {{
    background-color: {COLORS["accent"]};
    border-color: {COLORS["accent_hover"]};
}}
QPushButton#accentButton:pressed {{
    background-color: {COLORS["accent_dark"]};
}}

/* ── Transport Control Buttons ───────────────────────────────── */
QPushButton#transportBtn {{
    background: transparent;
    border: none;
    border-radius: 22px;
    padding: 8px;
    font-size: 18px;
    min-width: 44px;
    min-height: 44px;
    color: {COLORS["text_secondary"]};
}}
QPushButton#transportBtn:hover {{
    background-color: {COLORS["bg_hover"]};
    color: {COLORS["text_primary"]};
}}

/* Play/Pause — glowing accent button */
QPushButton#playBtn {{
    background-color: {COLORS["accent"]};
    border: 2px solid {COLORS["accent_hover"]};
    border-radius: 24px;
    min-width: 48px;
    min-height: 48px;
    font-size: 20px;
    color: white;
}}
QPushButton#playBtn:hover {{
    background-color: {COLORS["accent_hover"]};
    border-color: white;
}}

/* ── Line Edits ──────────────────────────────────────────────── */
QLineEdit {{
    background-color: {COLORS["bg_surface"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 13px;
    selection-background-color: {COLORS["accent_dark"]};
}}
QLineEdit:focus {{
    border-color: {COLORS["accent"]};
    background-color: {COLORS["bg_tertiary"]};
}}
QLineEdit::placeholder {{
    color: {COLORS["text_tertiary"]};
}}

/* ── Sliders ─────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    background: {COLORS["slider_bg"]};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {COLORS["slider_handle"]};
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
    border: 2px solid {COLORS["accent"]};
}}
QSlider::handle:horizontal:hover {{
    background: white;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{
    background: {COLORS["accent"]};
    border-radius: 3px;
}}

/* ── Volume slider (vertical) ────────────────────────────────── */
QSlider::groove:vertical {{
    background: {COLORS["slider_bg"]};
    width: 6px;
    border-radius: 3px;
}}
QSlider::handle:vertical {{
    background: {COLORS["slider_handle"]};
    width: 14px;
    height: 14px;
    margin: 0 -4px;
    border-radius: 7px;
    border: 2px solid {COLORS["accent"]};
}}
QSlider::sub-page:vertical {{
    background: {COLORS["accent"]};
    border-radius: 3px;
}}

/* ── Combo Boxes ─────────────────────────────────────────────── */
QComboBox {{
    background-color: {COLORS["bg_surface"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 6px 14px;
    min-width: 80px;
    font-size: 12px;
}}
QComboBox:hover {{
    border-color: {COLORS["accent"]};
}}
QComboBox:focus {{
    border-color: {COLORS["accent"]};
    background-color: {COLORS["bg_tertiary"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS["bg_tertiary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {COLORS["accent_dark"]};
    selection-color: white;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 12px;
    border-radius: 4px;
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {COLORS["bg_hover"]};
}}

/* ── Labels ──────────────────────────────────────────────────── */
QLabel {{
    color: {COLORS["text_primary"]};
    background: transparent;
}}
QLabel#secondaryLabel {{
    color: {COLORS["text_secondary"]};
    font-size: 12px;
}}
QLabel#titleLabel {{
    font-size: 15px;
    font-weight: 600;
    color: {COLORS["text_primary"]};
    padding: 2px 0;
}}
QLabel#statusLabel {{
    color: {COLORS["accent"]};
    font-size: 12px;
    font-weight: 500;
}}
QLabel#nowPlaying {{
    color: {COLORS["accent_hover"]};
    font-size: 13px;
    font-weight: 500;
}}

/* ── Tab Widget ──────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    background: {COLORS["bg_secondary"]};
    margin-top: -1px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: {COLORS["bg_tertiary"]};
    color: {COLORS["text_secondary"]};
    border: 1px solid {COLORS["border"]};
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 10px 18px;
    margin-right: 2px;
    font-weight: 500;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background: {COLORS["bg_secondary"]};
    color: {COLORS["accent"]};
    border-color: {COLORS["accent"]};
    border-bottom: 2px solid {COLORS["bg_secondary"]};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    background: {COLORS["bg_hover"]};
    color: {COLORS["text_primary"]};
}}

/* ── Scroll Bars ─────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 4px 0;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS["border"]};
    border-radius: 3px;
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
    height: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS["border"]};
    border-radius: 3px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {COLORS["text_tertiary"]};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* ── Scroll Area ─────────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background: transparent;
}}

/* ── Group Box ───────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    margin-top: 16px;
    padding: 20px 16px 16px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    padding: 0 10px;
    color: {COLORS["accent"]};
}}

/* ── Status Bar ──────────────────────────────────────────────── */
QStatusBar {{
    background: {COLORS["bg_secondary"]};
    border-top: 1px solid {COLORS["border"]};
    color: {COLORS["text_secondary"]};
    font-size: 11px;
    padding: 4px 12px;
}}

/* ── Tool Tips ───────────────────────────────────────────────── */
QToolTip {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["accent"]};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}}

/* ── Frame Separator ─────────────────────────────────────────── */
QFrame#separator {{
    background-color: {COLORS["border"]};
    max-height: 1px;
    margin: 4px 0;
}}

/* ── Video Frame ─────────────────────────────────────────────── */
QFrame#videoFrame {{
    background-color: #000000;
    border: 2px solid {COLORS["border"]};
    /* No border-radius — VLC rendering breaks with clipped corners */
}}

/* ── Search Result Card ──────────────────────────────────────── */
QFrame#resultCard {{
    background-color: {COLORS["bg_tertiary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    padding: 14px;
}}
QFrame#resultCard:hover {{
    border-color: {COLORS["accent"]};
    background-color: {COLORS["bg_hover"]};
}}

/* ── Transport Bar Container ─────────────────────────────────── */
QWidget#transportBar {{
    background-color: {COLORS["bg_secondary"]};
    border-top: 1px solid {COLORS["border"]};
    padding: 8px 16px;
}}
"""
