"""
Drawing Canvas — Obsidian Cinematic 3D drawing using hand gestures.
"""

from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QLinearGradient


class DrawingCanvas(QFrame):
    """
    A 2D canvas that simulates 3D drawing using the depth (z) coordinate.
    Styled with obsidian cinematic theme — amber strokes on dark glass.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("drawingCanvas")
        self.setMinimumSize(400, 400)
        self.setStyleSheet("""
            #drawingCanvas {
                background-color: #0d0e12;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 16px;
            }
        """)
        
        self._paths = [] 
        self._current_path = []
        self._is_drawing = False
        
    def add_point(self, x: float, y: float, z: float):
        """Add a new point to the drawing."""
        if self._is_drawing:
            px = x * self.width()
            py = y * self.height()
            self._current_path.append((px, py, z))
            self.update()
            
    def set_drawing(self, active: bool):
        """Enable or disable drawing."""
        if active == self._is_drawing:
            return
            
        self._is_drawing = active
        if active:
            self._current_path = []
        else:
            if len(self._current_path) > 1:
                self._paths.append(self._current_path)
            self._current_path = []
        self.update()
        
    def clear(self):
        """Clear all drawings."""
        self._paths = []
        self._current_path = []
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw finished paths — warm amber/gold
        for path in self._paths:
            self._draw_path(painter, path, False)
            
        # Draw current active path — bright amber glow
        if self._current_path:
            self._draw_path(painter, self._current_path, True)
            
    def _draw_path(self, painter: QPainter, path: list, is_active: bool):
        if len(path) < 2:
            return
            
        for i in range(len(path) - 1):
            p1 = path[i]
            p2 = path[i+1]
            
            z_avg = (p1[2] + p2[2]) / 2.0
            thickness = max(2.0, min(12.0, 6.0 - (z_avg * 40.0)))
            opacity = max(100, min(255, 220 - int(z_avg * 400)))
            
            if is_active:
                # Vivid amber for active drawing
                color = QColor(240, 160, 48, opacity)
            else:
                # Soft warm gold for finished paths
                color = QColor(255, 193, 118, int(opacity * 0.8))
            
            pen = QPen(color, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(QPointF(p1[0], p1[1]), QPointF(p2[0], p2[1]))
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
