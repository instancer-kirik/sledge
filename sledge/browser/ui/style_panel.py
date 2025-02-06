from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QComboBox, 
                             QLabel, QScrollArea, QSlider, QCheckBox)
from PyQt6.QtCore import pyqtSignal, Qt

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

class StyleAdjusterPanel(QWidget):
    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Theme Selection
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Dark', 'Light', 'Sepia', 'Nord', 'Solarized'])
        self.theme_combo.setCurrentText('Dark')  # Default theme
        self.theme_combo.currentTextChanged.connect(self._update_style)
        theme_layout.addWidget(QLabel("Theme"))
        theme_layout.addWidget(self.theme_combo)
        
        # Force Dark Mode
        self.force_dark = QCheckBox("Force Dark Mode")
        self.force_dark.setChecked(True)
        self.force_dark.stateChanged.connect(self._update_style)
        theme_layout.addWidget(self.force_dark)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Font size control
        font_group = QGroupBox("Font")
        font_layout = QVBoxLayout()
        
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setMinimum(8)
        self.font_size_slider.setMaximum(24)
        self.font_size_slider.setValue(14)  # Default font size
        self.font_size_slider.valueChanged.connect(self._update_style)
        font_layout.addWidget(QLabel("Size"))
        font_layout.addWidget(self.font_size_slider)
        
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)
        
        # Line height control
        spacing_group = QGroupBox("Spacing")
        spacing_layout = QVBoxLayout()
        
        self.line_height_slider = QSlider(Qt.Orientation.Horizontal)
        self.line_height_slider.setMinimum(10)
        self.line_height_slider.setMaximum(30)
        self.line_height_slider.setValue(15)  # Default line height (1.5)
        self.line_height_slider.valueChanged.connect(self._update_style)
        spacing_layout.addWidget(QLabel("Line Height"))
        spacing_layout.addWidget(self.line_height_slider)
        
        spacing_group.setLayout(spacing_layout)
        layout.addWidget(spacing_group)
        
        # Width control
        width_group = QGroupBox("Width")
        width_layout = QVBoxLayout()
        
        self.max_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_width_slider.setMinimum(400)
        self.max_width_slider.setMaximum(2000)
        self.max_width_slider.setValue(800)  # Default max width
        self.max_width_slider.valueChanged.connect(self._update_style)
        width_layout.addWidget(QLabel("Maximum Width"))
        width_layout.addWidget(self.max_width_slider)
        
        width_group.setLayout(width_layout)
        layout.addWidget(width_group)
        
        # Content toggles
        toggle_group = QGroupBox("Content")
        toggle_layout = QVBoxLayout()
        
        self.hide_images = QCheckBox("Hide Images")
        self.hide_images.stateChanged.connect(self._update_style)
        toggle_layout.addWidget(self.hide_images)
        
        self.hide_ads = QCheckBox("Hide Ads")
        self.hide_ads.setChecked(True)  # Default to hiding ads
        self.hide_ads.stateChanged.connect(self._update_style)
        toggle_layout.addWidget(self.hide_ads)
        
        self.justify_text = QCheckBox("Justify Text")
        self.justify_text.stateChanged.connect(self._update_style)
        toggle_layout.addWidget(self.justify_text)
        
        self.use_dyslexic_font = QCheckBox("Use OpenDyslexic Font")
        self.use_dyslexic_font.stateChanged.connect(self._update_style)
        toggle_layout.addWidget(self.use_dyslexic_font)
        
        toggle_group.setLayout(toggle_layout)
        layout.addWidget(toggle_group)
        
        # Add stretch at the bottom
        layout.addStretch()
        
    def _update_style(self):
        """Update the page style based on current settings"""
        # Update browser settings
        self.browser.theme.current_theme = self.theme_combo.currentText().lower()
        self.browser.theme.force_dark = self.force_dark.isChecked()
        self.browser.theme.font_size = self.font_size_slider.value()
        self.browser.theme.line_height = self.line_height_slider.value() / 10
        self.browser.theme.max_width = self.max_width_slider.value()
        self.browser.theme.hide_images = self.hide_images.isChecked()
        self.browser.theme.hide_ads = self.hide_ads.isChecked()
        self.browser.theme.justify_text = self.justify_text.isChecked()
        self.browser.theme.use_dyslexic_font = self.use_dyslexic_font.isChecked()
        
        # Apply theme to current tab
        current_tab = self.browser.current_tab()
        if current_tab and hasattr(current_tab, 'page'):
            css, js = self.browser.theme.inject_style(current_tab.url())
            current_tab.page().runJavaScript(js)
            
        # Update application stylesheet
        self.browser.setStyleSheet(self.browser.theme.get_stylesheet()) 