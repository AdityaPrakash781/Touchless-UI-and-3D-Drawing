"""
Drawing Canvas — Obsidian Cinematic 3D drawing using hand gestures.

Performance-optimised: uses QPainterPath for batched rendering,
point interpolation for smoothness, and path-level selection for
the grab-and-move feature.
"""

import math
from PyQt6.QtWidgets import QFrame, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QPainterPath, QKeySequence,
    QShortcut, QCursor, QMouseEvent,
)


class DrawingPath:
    """Stores a single continuous stroke with its points."""
    __slots__ = ("points", "offset_x", "offset_y")

    def __init__(self):
        self.points: list[tuple[float, float, float]] = []
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0

    def bounding_rect(self) -> QRectF:
        if not self.points:
            return QRectF()
        xs = [p[0] + self.offset_x for p in self.points]
        ys = [p[1] + self.offset_y for p in self.points]
        margin = 12  # account for line thickness
        return QRectF(
            min(xs) - margin, min(ys) - margin,
            max(xs) - min(xs) + 2 * margin,
            max(ys) - min(ys) + 2 * margin,
        )

    def contains(self, px: float, py: float, tolerance: float = 18.0) -> bool:
        """Check if a point is close to any segment in this path."""
        for i in range(len(self.points) - 1):
            ax = self.points[i][0] + self.offset_x
            ay = self.points[i][1] + self.offset_y
            bx = self.points[i + 1][0] + self.offset_x
            by = self.points[i + 1][1] + self.offset_y
            dist = _point_to_segment_dist(px, py, ax, ay, bx, by)
            if dist <= tolerance:
                return True
        return False


def _point_to_segment_dist(px, py, ax, ay, bx, by) -> float:
    """Distance from point (px,py) to line segment (ax,ay)-(bx,by)."""
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-8:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return math.hypot(px - proj_x, py - proj_y)


class DrawingCanvas(QFrame):
    """
    High-performance 2D canvas simulating 3D drawing via hand gestures.
    Supports batched rendering, grab-and-move, and fullscreen mode.
    """

    # Signal emitted when user wants fullscreen drawing
    fullscreen_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("drawingCanvas")
        self.setMinimumSize(300, 300)
        self.setStyleSheet("""
            #drawingCanvas {
                background-color: #0d0e12;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 16px;
            }
        """)
        self.setMouseTracking(True)

        self._paths: list[DrawingPath] = []
        self._current_path: DrawingPath | None = None
        self._is_drawing = False

        # ── Grab-and-move state ──
        self._move_mode = False
        self._selected_path: DrawingPath | None = None
        self._drag_start: QPointF | None = None
        self._drag_offset_start = (0.0, 0.0)

        # ── Performance: batch paint updates ──
        self._paint_dirty = False
        self._paint_timer = QTimer(self)
        self._paint_timer.setInterval(16)  # ~60 fps cap
        self._paint_timer.timeout.connect(self._flush_paint)
        self._paint_timer.start()

        # ── Interpolation state ──
        self._last_point: tuple[float, float, float] | None = None

    # ── Public API ───────────────────────────────────────────────────

    def add_point(self, x: float, y: float, z: float):
        """Add a new point to the active stroke (gesture input, normalised 0-1)."""
        if not self._is_drawing or self._current_path is None:
            return

        px = x * self.width()
        py = y * self.height()

        # Interpolate between last point and new point for smoothness
        if self._last_point is not None:
            lx, ly, lz = self._last_point
            dist = math.hypot(px - lx, py - ly)
            # If the jump is large, insert intermediate points
            if dist > 6.0:
                steps = int(dist / 4.0)
                for s in range(1, steps):
                    t = s / steps
                    ix = lx + (px - lx) * t
                    iy = ly + (py - ly) * t
                    iz = lz + (z - lz) * t
                    self._current_path.points.append((ix, iy, iz))

        self._current_path.points.append((px, py, z))
        self._last_point = (px, py, z)
        self._paint_dirty = True

    def set_drawing(self, active: bool):
        """Enable or disable the drawing stroke."""
        if active == self._is_drawing:
            return

        self._is_drawing = active
        if active:
            self._current_path = DrawingPath()
            self._last_point = None
        else:
            if self._current_path and len(self._current_path.points) > 1:
                self._paths.append(self._current_path)
            self._current_path = None
            self._last_point = None
        self._paint_dirty = True

    def set_move_mode(self, enabled: bool):
        """Toggle grab-and-move mode for selecting and dragging drawings."""
        self._move_mode = enabled
        self.setCursor(
            Qt.CursorShape.OpenHandCursor if enabled
            else Qt.CursorShape.ArrowCursor
        )
        self._selected_path = None
        self._paint_dirty = True

    def clear(self):
        """Clear all drawings."""
        self._paths.clear()
        self._current_path = None
        self._last_point = None
        self._selected_path = None
        self._paint_dirty = True

    def undo(self):
        """Remove the last completed stroke."""
        if self._paths:
            self._paths.pop()
            self._paint_dirty = True

    def get_all_paths(self) -> list:
        """Return a reference to all completed paths (for fullscreen sync)."""
        return self._paths

    def set_all_paths(self, paths: list):
        """Replace paths (for fullscreen sync)."""
        self._paths = paths
        self._paint_dirty = True

    # ── Mouse events for grab-and-move ──────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if not self._move_mode:
            return super().mousePressEvent(event)

        pos = event.position()
        # Find the topmost path that contains this click
        for path in reversed(self._paths):
            if path.contains(pos.x(), pos.y()):
                self._selected_path = path
                self._drag_start = pos
                self._drag_offset_start = (path.offset_x, path.offset_y)
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self._paint_dirty = True
                return

        self._selected_path = None
        self._paint_dirty = True

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self._move_mode or self._selected_path is None or self._drag_start is None:
            return super().mouseMoveEvent(event)

        pos = event.position()
        dx = pos.x() - self._drag_start.x()
        dy = pos.y() - self._drag_start.y()
        self._selected_path.offset_x = self._drag_offset_start[0] + dx
        self._selected_path.offset_y = self._drag_offset_start[1] + dy
        self._paint_dirty = True

    def mouseReleaseEvent(self, event: QMouseEvent):
        if not self._move_mode:
            return super().mouseReleaseEvent(event)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_start = None

    # ── Rendering ───────────────────────────────────────────────────

    def _flush_paint(self):
        """Only repaint if data changed — avoids redundant redraws."""
        if self._paint_dirty:
            self._paint_dirty = False
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw completed paths
        for path in self._paths:
            is_selected = (path is self._selected_path)
            self._draw_path(painter, path, is_active=False, is_selected=is_selected)

        # Draw active stroke
        if self._current_path and self._current_path.points:
            self._draw_path(painter, self._current_path, is_active=True)

        painter.end()

    def _draw_path(self, painter: QPainter, path: DrawingPath,
                   is_active: bool, is_selected: bool = False):
        pts = path.points
        if len(pts) < 2:
            return

        ox, oy = path.offset_x, path.offset_y

        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i + 1]

            z_avg = (p1[2] + p2[2]) / 2.0
            thickness = max(2.0, min(12.0, 6.0 - (z_avg * 40.0)))
            opacity = max(100, min(255, 220 - int(z_avg * 400)))

            if is_selected:
                color = QColor(208, 188, 255, opacity)  # Violet for selected
            elif is_active:
                color = QColor(240, 160, 48, opacity)    # Amber for active
            else:
                color = QColor(255, 193, 118, int(opacity * 0.8))  # Gold for finished

            pen = QPen(color, thickness, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(
                QPointF(p1[0] + ox, p1[1] + oy),
                QPointF(p2[0] + ox, p2[1] + oy),
            )

        # Draw selection bounding box
        if is_selected:
            rect = path.bounding_rect()
            pen = QPen(QColor(208, 188, 255, 80), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 8, 8)

    def resizeEvent(self, event):
        super().resizeEvent(event)


class FullscreenDrawingWindow(QWidget):
    """
    A fullscreen overlay window for immersive 3D drawing.
    Shares the same path data with the main canvas.
    """
    closed = pyqtSignal()

    def __init__(self, source_canvas: DrawingCanvas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GestureVLC — Fullscreen Drawing")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
        )
        self.setStyleSheet("background-color: #08090d;")
        self._source = source_canvas

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet("background: rgba(13,14,18,0.92);")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(20, 6, 20, 6)

        title = QLabel("FULLSCREEN DRAWING")
        title.setStyleSheet("color: #f0a030; font-weight: 700; font-size: 14px; letter-spacing: 0.06em;")
        tb_layout.addWidget(title)

        tb_layout.addStretch()

        btn_move = QPushButton("Move Mode")
        btn_move.setCheckable(True)
        btn_move.setStyleSheet(self._btn_style())
        btn_move.toggled.connect(self._fs_canvas.set_move_mode if hasattr(self, '_fs_canvas') else lambda v: None)
        tb_layout.addWidget(btn_move)

        btn_undo = QPushButton("Undo")
        btn_undo.setStyleSheet(self._btn_style())
        tb_layout.addWidget(btn_undo)

        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet(self._btn_style())
        tb_layout.addWidget(btn_clear)

        btn_close = QPushButton("✕ Exit")
        btn_close.setStyleSheet(self._btn_style("#f85149"))
        btn_close.clicked.connect(self._exit_fullscreen)
        tb_layout.addWidget(btn_close)

        layout.addWidget(toolbar)

        # Fullscreen canvas — shares paths with source
        self._fs_canvas = DrawingCanvas()
        self._fs_canvas.setStyleSheet("background-color: #08090d; border: none; border-radius: 0px;")
        self._fs_canvas.set_all_paths(source_canvas.get_all_paths())
        layout.addWidget(self._fs_canvas, stretch=1)

        # Wire buttons after canvas is created
        btn_move.toggled.connect(self._fs_canvas.set_move_mode)
        btn_undo.clicked.connect(self._fs_canvas.undo)
        btn_clear.clicked.connect(self._fs_canvas.clear)

        # Esc to close
        esc = QShortcut(QKeySequence("Escape"), self)
        esc.activated.connect(self._exit_fullscreen)

    @property
    def canvas(self) -> DrawingCanvas:
        return self._fs_canvas

    def _exit_fullscreen(self):
        # Sync paths back to source
        self._source.set_all_paths(self._fs_canvas.get_all_paths())
        self.closed.emit()
        self.close()

    def showEvent(self, event):
        super().showEvent(event)
        self.showFullScreen()

    def _btn_style(self, color: str = "#f0a030") -> str:
        return f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {color};
                border-radius: 8px;
                color: {color};
                padding: 6px 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: rgba(240, 160, 48, 0.12);
            }}
            QPushButton:checked {{
                background: {color};
                color: #0d0e12;
            }}
        """
