from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QComboBox, 
                             QLabel, QScrollArea)
from PyQt6.QtCore import pyqtSignal

class StylePanel(QWidget):
    """Panel for adjusting style and theme settings"""
    
    style_changed = pyqtSignal(str)  # Signal emitted when style changes
    
    def __init__(self, browser_theme, parent=None):
        super().__init__(parent)
        self.browser_theme = browser_theme
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Create content widget
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Theme Selection Group
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout()
        
        # Theme Selector
        theme_label = QLabel("Select Theme:")
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            'Dark',
            'Light', 
            'Sepia',
            'Nord',
            'Solarized'
        ])
        
        # Set current theme
        current_theme = self.browser_theme.current_theme
        index = self.theme_combo.findText(current_theme.capitalize())
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
            
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        
        # Theme description
        self.theme_desc = QLabel()
        self.update_theme_description()
        theme_layout.addWidget(self.theme_desc)
        
        theme_group.setLayout(theme_layout)
        content_layout.addWidget(theme_group)
        
        # Add stretch at the bottom
        content_layout.addStretch()
        
        # Set content widget to scroll area
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
    def on_theme_changed(self, theme_name):
        """Handle theme selection changes"""
        theme = theme_name.lower()
        self.browser_theme.set_theme(theme)
        self.update_theme_description()
        self.style_changed.emit(theme)
        
    def update_theme_description(self):
        """Update the theme description text"""
        descriptions = {
            'dark': "Dark theme optimized for low-light environments",
            'light': "Clean light theme for daytime use",
            'sepia': "Warm sepia tones for comfortable reading",
            'nord': "Cool arctic color palette",
            'solarized': "Precision colors for machines and people"
        }
        
        current = self.theme_combo.currentText().lower()
        self.theme_desc.setText(descriptions.get(current, "")) 