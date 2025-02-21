from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QTabWidget, QWidget, QLabel, QLineEdit, QCheckBox,
                           QSpinBox, QComboBox, QFormLayout, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

class SettingsDialog(QDialog):
    """Dialog for managing application settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.explorer = parent
        self.settings_manager = parent.settings_manager if parent else None
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the UI components"""
        self.setWindowTitle("Settings")
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # General settings tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        # Theme settings
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout(theme_group)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "System"])
        theme_layout.addRow("Theme:", self.theme_combo)
        general_layout.addWidget(theme_group)
        
        # View settings
        view_group = QGroupBox("View")
        view_layout = QFormLayout(view_group)
        self.show_hidden_check = QCheckBox()
        view_layout.addRow("Show Hidden Files:", self.show_hidden_check)
        self.show_preview_check = QCheckBox()
        view_layout.addRow("Show Preview Panel:", self.show_preview_check)
        
        # Icon settings
        self.icon_size_spin = QSpinBox()
        self.icon_size_spin.setRange(16, 256)
        self.icon_size_spin.setSingleStep(8)
        view_layout.addRow("Icon Size:", self.icon_size_spin)
        
        self.grid_spacing_spin = QSpinBox()
        self.grid_spacing_spin.setRange(0, 50)
        self.grid_spacing_spin.setSingleStep(2)
        view_layout.addRow("Grid Spacing:", self.grid_spacing_spin)
        
        general_layout.addWidget(view_group)
        
        # Add general tab
        self.tabs.addTab(general_tab, "General")
        
        # Launch settings tab
        launch_tab = QWidget()
        launch_layout = QVBoxLayout(launch_tab)
        
        # Terminal settings
        terminal_group = QGroupBox("Terminal")
        terminal_layout = QFormLayout(terminal_group)
        self.terminal_cmd = QLineEdit()
        terminal_layout.addRow("Terminal Command:", self.terminal_cmd)
        launch_layout.addWidget(terminal_group)
        
        # Project detection
        project_group = QGroupBox("Project Detection")
        project_layout = QFormLayout(project_group)
        self.auto_detect_check = QCheckBox()
        project_layout.addRow("Auto-detect Projects:", self.auto_detect_check)
        launch_layout.addWidget(project_group)
        
        # Add launch tab
        self.tabs.addTab(launch_tab, "Launch")
        
        # Preview settings tab
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        
        preview_group = QGroupBox("Preview")
        preview_form = QFormLayout(preview_group)
        
        self.syntax_highlight_check = QCheckBox()
        preview_form.addRow("Syntax Highlighting:", self.syntax_highlight_check)
        
        self.word_wrap_check = QCheckBox()
        preview_form.addRow("Word Wrap:", self.word_wrap_check)
        
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setRange(0, 10240)  # 0-10MB
        self.max_size_spin.setSingleStep(64)
        self.max_size_spin.setSuffix(" KB")
        preview_form.addRow("Max Preview Size:", self.max_size_spin)
        
        preview_layout.addWidget(preview_group)
        
        # Add preview tab
        self.tabs.addTab(preview_tab, "Preview")
        
        # Add tabs to layout
        layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Reset buttons
        reset_section_btn = QPushButton("Reset Section")
        reset_section_btn.clicked.connect(self.reset_current_section)
        button_layout.addWidget(reset_section_btn)
        
        reset_all_btn = QPushButton("Reset All")
        reset_all_btn.clicked.connect(self.reset_all_settings)
        button_layout.addWidget(reset_all_btn)
        
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Load current settings
        self.load_settings()
        
    def load_settings(self):
        """Load current settings into UI"""
        if not self.settings_manager:
            return
            
        # General settings
        general = self.settings_manager.get_section('general')
        self.theme_combo.setCurrentText(general.get('theme', 'System'))
        self.show_hidden_check.setChecked(general.get('show_hidden_files', False))
        self.show_preview_check.setChecked(general.get('show_preview_panel', True))
        
        # View settings
        view = self.settings_manager.get_section('view')
        self.icon_size_spin.setValue(view.get('icon_size', 48))
        self.grid_spacing_spin.setValue(view.get('grid_spacing', 10))
        
        # Launch settings
        launch = self.settings_manager.get_section('launch')
        self.terminal_cmd.setText(launch.get('terminal_command', 'x-terminal-emulator'))
        self.auto_detect_check.setChecked(launch.get('auto_detect_projects', True))
        
        # Preview settings
        preview = self.settings_manager.get_section('preview')
        self.syntax_highlight_check.setChecked(preview.get('syntax_highlighting', True))
        self.word_wrap_check.setChecked(preview.get('word_wrap', True))
        self.max_size_spin.setValue(preview.get('max_text_size', 1024) // 1024)  # Convert to KB
        
    def save_settings(self):
        """Save settings from UI"""
        if not self.settings_manager:
            return
            
        # General settings
        self.settings_manager.set_setting('general', 'theme', self.theme_combo.currentText())
        self.settings_manager.set_setting('general', 'show_hidden_files', self.show_hidden_check.isChecked())
        self.settings_manager.set_setting('general', 'show_preview_panel', self.show_preview_check.isChecked())
        
        # View settings
        self.settings_manager.set_setting('view', 'icon_size', self.icon_size_spin.value())
        self.settings_manager.set_setting('view', 'grid_spacing', self.grid_spacing_spin.value())
        
        # Launch settings
        self.settings_manager.set_setting('launch', 'terminal_command', self.terminal_cmd.text())
        self.settings_manager.set_setting('launch', 'auto_detect_projects', self.auto_detect_check.isChecked())
        
        # Preview settings
        self.settings_manager.set_setting('preview', 'syntax_highlighting', self.syntax_highlight_check.isChecked())
        self.settings_manager.set_setting('preview', 'word_wrap', self.word_wrap_check.isChecked())
        self.settings_manager.set_setting('preview', 'max_text_size', self.max_size_spin.value() * 1024)  # Convert to bytes
        
        # Apply settings
        if self.explorer:
            self.explorer.apply_settings()
            
        self.accept()
        
    def reset_current_section(self):
        """Reset current tab's settings to defaults"""
        if not self.settings_manager:
            return
            
        current_tab = self.tabs.currentWidget()
        if current_tab == self.tabs.widget(0):  # General tab
            self.settings_manager.reset_section('general')
            self.settings_manager.reset_section('view')
        elif current_tab == self.tabs.widget(1):  # Launch tab
            self.settings_manager.reset_section('launch')
        elif current_tab == self.tabs.widget(2):  # Preview tab
            self.settings_manager.reset_section('preview')
            
        self.load_settings()
        
    def reset_all_settings(self):
        """Reset all settings to defaults"""
        if not self.settings_manager:
            return
            
        self.settings_manager.reset_all()
        self.load_settings() 