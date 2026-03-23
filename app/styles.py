"""
GestureVLC — Obsidian Cinematic Theme

Designed with Stitch MCP — ultra-deep charcoal surfaces with warm amber/gold
accents, frosted glass layering, and editorial Inter typography.

Creative North Star: "The Obsidian Conductor"
Luxury hardware feel — carved from dark glass, lit by warm internal glow.
"""

# ── Design Tokens (Stitch MCP — Obsidian Cinematic) ──────────────

COLORS = {
    # Backgrounds — obsidian depth layering
    "bg_base":        "#08090d",   # Ultra-deep void
    "bg_primary":     "#0d0e12",   # Main window background
    "bg_secondary":   "#121317",   # Panels / sidebar
    "bg_tertiary":    "#1a1b20",   # Cards / elevated surfaces
    "bg_surface":     "#1e1f24",   # Input fields / combo boxes
    "bg_hover":       "#292a2e",   # Hover state
    "bg_active":      "#343439",   # Active/pressed state

    # Borders — ghost borders (translucent)
    "border":         "rgba(255, 255, 255, 0.06)",   # Ultra-subtle glass edge
    "border_visible": "#2a2c32",                      # Slightly more visible
    "border_focus":   "#f0a030",                      # Amber focus ring

    # Text
    "text_primary":   "#e3e2e8",   # Main text (high contrast)
    "text_secondary": "#8b8d96",   # Muted
    "text_tertiary":  "#555760",   # Disabled / hint
    "text_accent":    "#ffc176",   # Warm amber text

    # Accent — warm amber/gold
    "accent":         "#f0a030",   # Primary amber
    "accent_hover":   "#ffc176",   # Lighter amber
    "accent_dark":    "#c47e1a",   # Darker amber
    "accent_glow":    "rgba(240, 160, 48, 0.15)",  # Ambient glow

    # Secondary — soft violet
    "violet":         "#d0bcff",
    "violet_dark":    "#571bc1",
    "violet_muted":   "#8b5cf6",

    # Semantic
    "success":        "#3fb950",
    "warning":        "#f0a030",
    "danger":         "#f85149",

    # Slider
    "slider_bg":      "rgba(52, 52, 57, 0.4)",   # 40% opacity
    "slider_handle":  "#f0a030",
}

STYLESHEET = f"""
/* ═══════════════════════════════════════════════════════════════
   GestureVLC — Obsidian Cinematic Theme (Stitch MCP)
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
    letter-spacing: 0.01em;
}}

/* ── Menu Bar ────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {COLORS["bg_secondary"]};
    border-bottom: 1px solid {COLORS["border"]};
    padding: 6px 12px;
    spacing: 4px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    border-radius: 8px;
    color: {COLORS["text_secondary"]};
    letter-spacing: 0.02em;
}}
QMenuBar::item:selected {{
    background-color: {COLORS["bg_hover"]};
    color: {COLORS["text_accent"]};
}}
QMenu {{
    background-color: {COLORS["bg_tertiary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    padding: 8px;
}}
QMenu::item {{
    padding: 8px 28px 8px 16px;
    border-radius: 8px;
}}
QMenu::item:selected {{
    background-color: {COLORS["accent_dark"]};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background: {COLORS["border"]};
    margin: 6px 12px;
}}

/* ── Push Buttons ────────────────────────────────────────────── */
QPushButton {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    padding: 10px 20px;
    font-weight: 500;
    font-size: 13px;
    letter-spacing: 0.01em;
}}
QPushButton:hover {{
    background-color: {COLORS["bg_hover"]};
    border-color: {COLORS["accent"]};
    color: {COLORS["text_accent"]};
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

/* Accent button — warm amber glow */
QPushButton#accentButton {{
    background-color: {COLORS["accent"]};
    border: 1px solid {COLORS["accent_hover"]};
    color: #2b1700;
    font-weight: 700;
    letter-spacing: 0.02em;
}}
QPushButton#accentButton:hover {{
    background-color: {COLORS["accent_hover"]};
    border-color: #ffe0a0;
    color: #1a0e00;
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
    background-color: rgba(240, 160, 48, 0.08);
    color: {COLORS["text_accent"]};
}}

/* Play/Pause — glowing amber cinematic button */
QPushButton#playBtn {{
    background-color: {COLORS["accent"]};
    border: 2px solid {COLORS["accent_hover"]};
    border-radius: 26px;
    min-width: 52px;
    min-height: 52px;
    font-size: 22px;
    color: #2b1700;
    font-weight: 700;
}}
QPushButton#playBtn:hover {{
    background-color: {COLORS["accent_hover"]};
    border-color: #ffe0a0;
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
    selection-color: white;
}}
QLineEdit:focus {{
    border-color: {COLORS["accent"]};
    background-color: {COLORS["bg_tertiary"]};
}}
QLineEdit::placeholder {{
    color: {COLORS["text_tertiary"]};
    letter-spacing: 0.02em;
}}

/* ── Sliders — amber seek with precision ─────────────────────── */
QSlider::groove:horizontal {{
    background: {COLORS["slider_bg"]};
    height: 5px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {COLORS["accent"]};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: 2px solid {COLORS["accent_hover"]};
}}
QSlider::handle:horizontal:hover {{
    background: {COLORS["accent_hover"]};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 2px solid #ffe0a0;
}}
QSlider::sub-page:horizontal {{
    background: {COLORS["accent"]};
    border-radius: 2px;
}}

/* ── Volume slider (vertical) ────────────────────────────────── */
QSlider::groove:vertical {{
    background: {COLORS["slider_bg"]};
    width: 5px;
    border-radius: 2px;
}}
QSlider::handle:vertical {{
    background: {COLORS["accent"]};
    width: 14px;
    height: 14px;
    margin: 0 -5px;
    border-radius: 7px;
    border: 2px solid {COLORS["accent_hover"]};
}}
QSlider::sub-page:vertical {{
    background: {COLORS["accent"]};
    border-radius: 2px;
}}

/* ── Combo Boxes ─────────────────────────────────────────────── */
QComboBox {{
    background-color: {COLORS["bg_surface"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 7px 14px;
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
    border: 1px solid {COLORS["border_visible"]};
    border-radius: 10px;
    padding: 6px;
    selection-background-color: {COLORS["accent_dark"]};
    selection-color: white;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 8px 14px;
    border-radius: 6px;
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
    letter-spacing: 0.01em;
}}
QLabel#titleLabel {{
    font-size: 14px;
    font-weight: 600;
    color: {COLORS["text_accent"]};
    padding: 2px 0;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}
QLabel#sectionTitle {{
    font-size: 18px;
    font-weight: 700;
    color: {COLORS["text_primary"]};
    letter-spacing: -0.02em;
}}
QLabel#statusLabel {{
    color: {COLORS["accent"]};
    font-size: 12px;
    font-weight: 500;
}}
QLabel#nowPlaying {{
    color: {COLORS["text_accent"]};
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.01em;
}}
QLabel#timeLabel {{
    font-family: "JetBrains Mono", "Cascadia Code", "Consolas", monospace;
    color: {COLORS["text_secondary"]};
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.05em;
}}
QLabel#brandLabel {{
    color: {COLORS["accent"]};
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}}

/* ── Tab Widget — icon-based navigation ──────────────────────── */
QTabWidget::pane {{
    border: 1px solid {COLORS["border"]};
    border-radius: 16px;
    background: {COLORS["bg_secondary"]};
    margin-top: -1px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {COLORS["text_tertiary"]};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 16px;
    margin-right: 4px;
    font-weight: 500;
    font-size: 12px;
    letter-spacing: 0.03em;
}}
QTabBar::tab:selected {{
    color: {COLORS["accent"]};
    border-bottom: 2px solid {COLORS["accent"]};
    font-weight: 700;
}}
QTabBar::tab:hover:!selected {{
    color: {COLORS["text_secondary"]};
    border-bottom: 2px solid {COLORS["bg_hover"]};
}}

/* ── Scroll Bars — minimal obsidian ──────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 5px;
    margin: 4px 0;
    border-radius: 2px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS["border_visible"]};
    border-radius: 2px;
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
    height: 5px;
    border-radius: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS["border_visible"]};
    border-radius: 2px;
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
    border-radius: 16px;
    margin-top: 16px;
    padding: 20px 16px 16px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    padding: 0 12px;
    color: {COLORS["accent"]};
    letter-spacing: 0.04em;
}}

/* ── Status Bar — minimal cinematic ──────────────────────────── */
QStatusBar {{
    background: {COLORS["bg_base"]};
    border-top: 1px solid {COLORS["border"]};
    color: {COLORS["text_tertiary"]};
    font-size: 11px;
    padding: 3px 16px;
    letter-spacing: 0.02em;
}}

/* ── Tool Tips ───────────────────────────────────────────────── */
QToolTip {{
    background-color: {COLORS["bg_tertiary"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["accent"]};
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 12px;
}}

/* ── Frame Separator — replaced with spacing where possible ─── */
QFrame#separator {{
    background-color: {COLORS["border"]};
    max-height: 1px;
    margin: 6px 0;
}}

/* ── Video Frame — infinite window, no rounded corners ───────── */
QFrame#videoFrame {{
    background-color: #0d0e12;
    border: 1px solid {COLORS["border_visible"]};
}}

/* ── Search Result Card — obsidian glass card ────────────────── */
QFrame#resultCard {{
    background-color: {COLORS["bg_tertiary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 14px;
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
    padding: 6px 20px;
}}
"""
