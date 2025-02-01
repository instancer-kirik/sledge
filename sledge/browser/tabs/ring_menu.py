import math
from PyQt6.QtCore import Qt, QPointF,QRectF, QSize, QTimer, QEvent, QPropertyAnimation
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton

class RingMenu(QWidget):
    """Ring-shaped menu that appears around the cursor or touch point"""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.actions = []
        self.radius = 150  # Increased radius for touch
        self.current_hover = -1
        self.min_touch_size = 80  # Minimum touch target size
        
        # Touch gesture tracking
        self.touch_start = None
        self.touch_tracking = False
        
        # Enable touch and mouse tracking
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.setMouseTracking(True)

    def add_action(self, text, callback, icon=None):
        """Add an action to the ring menu with optional icon"""
        self.actions.append((text, callback, icon))

    def show_at(self, pos):
        """Show menu centered at position"""
        # Make sure the menu is large enough for touch
        size = QSize(self.radius * 2 + 80, self.radius * 2 + 80)
        self.resize(size)
        
        # Center on touch/cursor point
        self.move(pos.x() - size.width()//2, 
                 pos.y() - size.height()//2)
        
        # Add fade-in animation
        self.setWindowOpacity(0)
        self.show()
        
        # Animate opacity
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(150)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.start()

    def paintEvent(self, event):
        """Paint the ring menu with touch-optimized design"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = QPointF(self.width() / 2, self.height() / 2)
        
        num_actions = len(self.actions)
        if num_actions == 0:
            return
            
        # Draw segments with larger touch areas
        angle_step = 360.0 / num_actions
        for i, (text, _, icon) in enumerate(self.actions):
            path = QPainterPath()
            start_angle = i * angle_step
            
            # Create segment path with rounded corners
            path.moveTo(center)
            path.arcTo(center.x() - self.radius, 
                      center.y() - self.radius,
                      self.radius * 2, self.radius * 2,
                      start_angle, angle_step)
            path.lineTo(center)
            
            # Fill segment with touch feedback
            if i == self.current_hover:
                gradient = QLinearGradient(
                    path.boundingRect().topLeft(),
                    path.boundingRect().bottomRight()
                )
                gradient.setColorAt(0, QColor(80, 80, 80))
                gradient.setColorAt(1, QColor(60, 60, 60))
                painter.fillPath(path, gradient)
            else:
                gradient = QLinearGradient(
                    path.boundingRect().topLeft(),
                    path.boundingRect().bottomRight()
                )
                gradient.setColorAt(0, QColor(50, 50, 50))
                gradient.setColorAt(1, QColor(40, 40, 40))
                painter.fillPath(path, gradient)
            
            # Draw icon if available
            if icon:
                icon_angle = start_angle + angle_step/2
                icon_radius = self.radius * 0.6
                icon_pos = QPointF(
                    center.x() + icon_radius * math.cos(math.radians(icon_angle)),
                    center.y() + icon_radius * math.sin(math.radians(icon_angle))
                )
                icon_size = QSize(32, 32)  # Larger icons for touch
                icon_rect = QRectF(
                    icon_pos.x() - icon_size.width()/2,
                    icon_pos.y() - icon_size.height()/2,
                    icon_size.width(),
                    icon_size.height()
                )
                icon.paint(painter, icon_rect.toRect())
            
            # Draw text below icon
            text_angle = start_angle + angle_step/2
            text_radius = self.radius * 0.8
            text_pos = QPointF(
                center.x() + text_radius * math.cos(math.radians(text_angle)),
                center.y() + text_radius * math.sin(math.radians(text_angle))
            )
            
            # Use larger, more readable font
            font = painter.font()
            font.setPointSize(12)
            painter.setFont(font)
            
            # Draw text with background for better readability
            text_rect = painter.boundingRect(
                QRectF(text_pos.x() - 60, text_pos.y() - 15, 120, 30),
                Qt.AlignmentFlag.AlignCenter,
                text
            )
            
            # Draw text shadow for depth
            painter.setPen(QColor(0, 0, 0, 100))
            painter.drawText(text_rect.translated(1, 1), Qt.AlignmentFlag.AlignCenter, text)
            
            # Draw actual text
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def event(self, event):
        """Handle touch events"""
        if event.type() == QEvent.Type.TouchBegin:
            # Get the first touch point
            touch_point = event.points()[0]
            self.touch_start = touch_point.position()
            return True
            
        elif event.type() == QEvent.Type.TouchEnd:
            if self.touch_start is not None:
                touch_point = event.points()[0]
                touch_end = touch_point.position()
                
                # Calculate movement
                delta = touch_end - self.touch_start
                
                # If minimal movement, treat as click
                if delta.manhattanLength() < 20:
                    self._handle_click(touch_end)
                
                self.touch_start = None
            return True
            
        elif event.type() == QEvent.Type.TouchUpdate:
            if self.touch_start is not None:
                touch_point = event.points()[0]
                current_pos = touch_point.position()
                self._update_hover(current_pos)
            return True
            
        return super().event(event)

    def mouseMoveEvent(self, event):
        """Track mouse movement for non-touch interaction"""
        self._update_hover(event.pos())

    def mouseReleaseEvent(self, event):
        """Handle mouse release for non-touch interaction"""
        self._handle_release(event.pos())

    def _handle_click(self, pos):
        """Handle click/tap at position"""
        for i, (rect, action) in enumerate(self.action_rects):
            if rect.contains(pos.toPoint()):
                self.hide()
                action.trigger()
                break

    def _update_hover(self, pos):
        """Update hover state based on position"""
        for i, (rect, _) in enumerate(self.action_rects):
            if rect.contains(pos.toPoint()):
                if self.hover_index != i:
                    self.hover_index = i
                    self.update()
                break

    def _handle_release(self, pos):
        """Handle touch/click release"""
        if self.current_hover >= 0:
            _, callback, _ = self.actions[self.current_hover]
            
            # Add haptic feedback if available
            if hasattr(self, 'feedback'):
                self.feedback.play()
            
            # Hide with fade-out animation
            animation = QPropertyAnimation(self, b"windowOpacity")
            animation.setDuration(150)
            animation.setStartValue(1)
            animation.setEndValue(0)
            animation.finished.connect(self.hide)
            animation.finished.connect(callback)
            animation.start()