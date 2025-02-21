from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTreeWidgetItem, 
                           QHBoxLayout, QSplitter, QLabel, QPushButton, QTreeWidget, QGroupBox, QTabWidget)
from PyQt6.QtCore import Qt, QDir, QSize, QThread, pyqtSignal, QFileSystemWatcher
from PyQt6.QtGui import QFileSystemModel, QIcon
from ..tools.settings_manager import SettingsManager
import asyncio
from qasync import QEventLoop

class EExplorer(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialize managers and tools
        self.build_manager = BuildManager(self)
        self.vcs_manager = VCSManager(self)
        self.file_ops = FileOperations(self)
        self.test_tool = TestTool(self)
        self.duplicate_finder = DuplicateFinder(self)
        self.command_manager = CommandManager(self)
        self.launch_manager = LaunchManager(self)
        self.settings_manager = SettingsManager(self)
        
        # Initialize state
        self.smelt_monitor_thread = None
        self.clipboard_files = []
        self.clipboard_operation = None
        self.current_view_mode = 'list'
        
        # Setup UI
        self.setup_ui()
        setup_theme(self)
        
        # Apply initial settings
        self.apply_settings()
        
        # Setup async event loop
        self.loop = QEventLoop()
        asyncio.set_event_loop(self.loop)

    def show_launch_manager(self, path):
        """Show launch configuration manager"""
        from .launch_dialog import LaunchDialog
        dialog = LaunchDialog(self, path)
        dialog.exec()

    def show_settings(self):
        """Show settings dialog"""
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()

    def show_command_manager(self, initial_path=None):
        """Show command manager dialog"""
        from .command_dialog import CommandDialog
        dialog = CommandDialog(self)
        if initial_path:
            dialog.add_command()  # Start with add command dialog if path provided
        dialog.exec()

    def toggle_hidden_files(self, checked):
        """Toggle visibility of hidden files"""
        # Update settings
        self.settings_manager.set_setting('general', 'show_hidden_files', checked)
        
        # Update file filter
        self.model.setFilter(
            QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot |
            (QDir.Filter.Hidden if checked else QDir.Filter.NoFilter)
        )
        
        # Update button state
        self.hidden_files_btn.setChecked(checked)

    def apply_settings(self):
        """Apply current settings to the UI"""
        # Apply view settings
        view_settings = self.settings_manager.get_section('view')
        self.switch_view_mode(view_settings.get('default_view_mode', 'list'))
        
        # Update icon size and grid spacing
        icon_size = view_settings.get('icon_size', 48)
        grid_spacing = view_settings.get('grid_spacing', 10)
        self.list_view.setIconSize(QSize(icon_size, icon_size))
        self.list_view.setGridSize(QSize(icon_size + 20, icon_size + 30))
        self.list_view.setSpacing(grid_spacing)
        
        # Apply general settings
        general_settings = self.settings_manager.get_section('general')
        
        # Show/hide hidden files
        show_hidden = general_settings.get('show_hidden_files', False)
        self.model.setFilter(
            QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot |
            (QDir.Filter.Hidden if show_hidden else QDir.Filter.NoFilter)
        )
        
        # Show/hide preview panel
        show_preview = general_settings.get('show_preview_panel', True)
        if show_preview != self.preview_tabs.isVisible():
            self.toggle_preview()
            
        # Apply preview settings
        preview_settings = self.settings_manager.get_section('preview')
        for i in range(self.preview_tabs.count()):
            tab = self.preview_tabs.widget(i)
            if hasattr(tab, 'apply_settings'):
                tab.apply_settings(preview_settings) 