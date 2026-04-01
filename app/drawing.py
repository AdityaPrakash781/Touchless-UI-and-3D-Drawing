"""
Drawing Canvas — Real-time 3D-like drawing using hand gestures.
"""

from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap


class DrawingCanvas(QFrame):
    """
    A 2D canvas that simulates 3D drawing using the depth (z) coordinate.
    Uses a QPixmap buffer to reduce latency and improve rendering performance.
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
        
        self._buffer = QPixmap(self.size())
        self._buffer.fill(Qt.GlobalColor.transparent)
        
    def add_point(self, x: float, y: float, z: float):
        """Add a new point to the drawing."""
        if self._is_drawing:
            # Map normalized 0-1 to pixel coords
            px = x * self.width()
            py = y * self.height()
            
            self._current_path.append((px, py, z))
            
            # Immediately draw just the new segment to the buffer for low latency
            if len(self._current_path) >= 2:
                p1 = self._current_path[-2]
                p2 = self._current_path[-1]
                self._draw_segment_to_buffer(p1, p2, is_active=True)
                
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
                # Redraw buffer so the finished stroke is painted with the inactive color
                self._redraw_buffer()
            self._current_path = []
            
        self.update()
        
    def clear(self):
        """Clear all drawings."""
        self._paths = []
        self._current_path = []
        self._buffer.fill(Qt.GlobalColor.transparent)
        self.update()
        
    def paintEvent(self, event):
        # Call super to draw the stylesheet background/border
        super().paintEvent(event)
        
        if self._buffer.isNull():
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw the pre-rendered buffer containing all strokes
        painter.drawPixmap(0, 0, self._buffer)
            
    def _draw_segment_to_buffer(self, p1: tuple, p2: tuple, is_active: bool):
        """Draw a single line segment directly onto the off-screen buffer."""
        if self._buffer.isNull():
            return
            
        painter = QPainter(self._buffer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # MediaPipe Z is the landmark depth relative to the wrist.
        # Typically ranges from -0.1 to 0.1 for hand movements.
        # We want smaller Z (closer) to be thicker.
        z_avg = (p1[2] + p2[2]) / 2.0
        
        # Robust mapping for Z to visuals.
        # Closer (smaller Z) -> thicker (10px), Farther (larger Z) -> thinner (2px)
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
        painter.end()
        
    def _redraw_buffer(self):
        """Re-render all saved inactive paths onto the buffer."""
        if self.width() <= 0 or self.height() <= 0:
            return
            
        self._buffer.fill(Qt.GlobalColor.transparent)
        for path in self._paths:
            if len(path) < 2:
                continue
            for i in range(len(path) - 1):
                self._draw_segment_to_buffer(path[i], path[i+1], is_active=False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.width() > 0 and self.height() > 0:
            self._buffer = QPixmap(self.size())
            self._redraw_buffer()
