"""
Drawing Canvas — Real-time 3D-like drawing using hand gestures.
"""

from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush


class DrawingCanvas(QFrame):
    """
    A 2D canvas that simulates 3D drawing using the depth (z) coordinate.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("drawingCanvas")
        self.setMinimumSize(400, 400)
        # Use a thicker border and a distinct background
        self.setStyleSheet("""
            #drawingCanvas {
                background-color: #0d1117;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
        """)
        
        self._paths = [] 
        self._current_path = []
        self._is_drawing = False
        
    def add_point(self, x: float, y: float, z: float):
        """Add a new point to the drawing."""
        if self._is_drawing:
            # Map normalized 0-1 to pixel coords
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
            # Starting a new stroke
            self._current_path = []
        else:
            # Finishing a stroke
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
        # Call super to draw the stylesheet background/border
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Clip to the rounded corners of the frame
        # (Though border-radius in stylesheet doesn't always clip child painting)
        
        # Draw finished paths
        for path in self._paths:
            self._draw_path(painter, path, False)
            
        # Draw current active path
        if self._current_path:
            self._draw_path(painter, self._current_path, True)
            
    def _draw_path(self, painter: QPainter, path: list, is_active: bool):
        if len(path) < 2:
            return
            
        for i in range(len(path) - 1):
            p1 = path[i]
            p2 = path[i+1]
            
            # MediaPipe Z is the landmark depth relative to the wrist.
            # Typically ranges from -0.1 to 0.1 for hand movements.
            # We want smaller Z (closer) to be thicker.
            z_avg = (p1[2] + p2[2]) / 2.0
            
            # Robust mapping for Z to visuals.
            # Closer (smaller Z) -> thicker (10px), Farther (larger Z) -> thinner (2px)
            # Center it around 0.
            thickness = max(2.0, min(12.0, 6.0 - (z_avg * 40.0)))
            
            # Opacity: Closer is more opaque
            opacity = max(100, min(255, 220 - int(z_avg * 400)))
            
            if is_active:
                # Vibrant blue for active drawing
                color = QColor(88, 166, 255, opacity)
            else:
                # White/Grey for finished paths
                color = QColor(230, 237, 243, opacity)
            
            pen = QPen(color, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(QPointF(p1[0], p1[1]), QPointF(p2[0], p2[1]))
            
    def resizeEvent(self, event):
        # We might need to rescale points here if we wanted resolution independence,
        # but for now we stay with pixel-relative paths stored during capture.
        super().resizeEvent(event)
