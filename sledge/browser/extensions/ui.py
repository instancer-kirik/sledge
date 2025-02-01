from PyQt6.QtWidgets import (
    QWidget, QToolButton, QMenu, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog,
    QScrollArea, QGridLayout, QFrame, QCheckBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from pathlib import Path

class ExtensionButton(QToolButton):
    """Toolbar button for extension actions"""
    
    clicked = pyqtSignal(str)  # extension_id
    
    def __init__(self, extension_id: str, manifest: dict, parent=None):
        super().__init__(parent)
        self.extension_id = extension_id
        self.manifest = manifest
        
        # Set up button
        self.setIcon(self._get_icon())
        self.setToolTip(manifest.get('name', 'Extension'))
        self.clicked.connect(lambda: self.clicked.emit(extension_id))
        
        # Set up popup (if defined in manifest)
        if 'browser_action' in manifest:
            self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            self.setMenu(ExtensionPopup(extension_id, manifest, parent))
    
    def _get_icon(self) -> QIcon:
        """Get extension icon"""
        icon_path = None
        if 'browser_action' in self.manifest:
            icon_path = self.manifest['browser_action'].get('default_icon')
        elif 'icons' in self.manifest:
            # Use largest icon available
            sizes = sorted(map(int, self.manifest['icons'].keys()))
            if sizes:
                icon_path = self.manifest['icons'][str(sizes[-1])]
        
        if icon_path:
            full_path = Path(self.extension_id) / icon_path
            if full_path.exists():
                return QIcon(str(full_path))
        
        return QIcon.fromTheme('application-x-addon')

class ExtensionPopup(QMenu):
    """Popup menu for extension actions"""
    
    def __init__(self, extension_id: str, manifest: dict, parent=None):
        super().__init__(parent)
        self.extension_id = extension_id
        self.manifest = manifest
        
        # Load popup content from extension
        if 'browser_action' in manifest:
            popup = manifest['browser_action'].get('default_popup')
            if popup:
                # TODO: Load HTML popup content
                pass

class ExtensionCard(QFrame):
    """Card widget for displaying extension information"""
    
    def __init__(self, extension_id: str, extension_info: dict, manager, parent=None):
        super().__init__(parent)
        self.extension_id = extension_id
        self.extension_info = extension_info
        self.manager = manager
        
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            ExtensionCard {
                background: #2e3440;
                border-radius: 8px;
                padding: 12px;
                margin: 4px;
            }
            QLabel {
                color: #d8dee9;
            }
            QPushButton {
                background: #3b4252;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                color: #d8dee9;
            }
            QPushButton:hover {
                background: #434c5e;
            }
            QCheckBox {
                color: #d8dee9;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        name = QLabel(f"<b>{extension_info['manifest'].get('name', 'Unknown Extension')}</b>")
        name.setStyleSheet("font-size: 14px;")
        header.addWidget(name)
        
        enabled = QCheckBox("Enabled")
        enabled.setChecked(extension_info['enabled'])
        enabled.stateChanged.connect(self._toggle_enabled)
        header.addWidget(enabled)
        layout.addLayout(header)
        
        # Description
        desc = QLabel(extension_info['manifest'].get('description', ''))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #81a1c1;")
        layout.addWidget(desc)
        
        # Version
        version = QLabel(f"Version: {extension_info['manifest'].get('version', 'Unknown')}")
        version.setStyleSheet("color: #81a1c1; font-size: 11px;")
        layout.addWidget(version)
        
        # Buttons
        buttons = QHBoxLayout()
        
        if 'options_page' in extension_info['manifest']:
            options_btn = QPushButton("Options")
            options_btn.clicked.connect(self._show_options)
            buttons.addWidget(options_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_extension)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: #bf616a;
            }
            QPushButton:hover {
                background: #d08770;
            }
        """)
        buttons.addWidget(remove_btn)
        
        buttons.addStretch()
        layout.addLayout(buttons)
    
    def _toggle_enabled(self, state):
        if state == Qt.CheckState.Checked:
            self.manager.browser.extension_manager.enable_extension(self.extension_id)
        else:
            self.manager.browser.extension_manager.disable_extension(self.extension_id)
    
    def _show_options(self):
        self.manager.browser.extension_manager.show_options(self.extension_id)
    
    def _remove_extension(self):
        self.manager.browser.extension_manager.uninstall_extension(self.extension_id)
        self.manager.load_extensions()

class ExtensionManager(QDialog):
    """Dialog for managing extensions"""
    
    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.setWindowTitle("Extensions")
        self.setMinimumSize(700, 600)
        
        self.setStyleSheet("""
            QDialog {
                background: #2e3440;
            }
            QPushButton {
                background: #5e81ac;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                color: #eceff4;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #81a1c1;
            }
            QLineEdit {
                background: #3b4252;
                border: 1px solid #4c566a;
                border-radius: 4px;
                padding: 8px;
                color: #eceff4;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #5e81ac;
            }
            QLabel {
                color: #eceff4;
                font-size: 13px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        header.setSpacing(16)
        
        # Title and stats
        title_section = QVBoxLayout()
        title = QLabel("<h2>Extensions</h2>")
        title.setStyleSheet("color: #eceff4; font-size: 24px; margin-bottom: 4px;")
        title_section.addWidget(title)
        
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #81a1c1; font-size: 13px;")
        title_section.addWidget(self.stats_label)
        header.addLayout(title_section)
        
        header.addStretch()
        
        # Install button
        install_btn = QPushButton("Load Extension...")
        install_btn.setIcon(QIcon.fromTheme('list-add'))
        install_btn.clicked.connect(self.install_extension)
        header.addWidget(install_btn)
        
        layout.addLayout(header)
        
        # Search bar
        search_container = QHBoxLayout()
        search_container.setSpacing(8)
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("color: #4c566a; font-size: 16px;")
        search_container.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search extensions...")
        self.search_input.textChanged.connect(self.filter_extensions)
        search_container.addWidget(self.search_input)
        
        layout.addLayout(search_container)
        
        # Scroll area for extension cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #3b4252;
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4c566a;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:vertical {
                height: 0px;
            }
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.extensions_widget = QWidget()
        self.extensions_layout = QVBoxLayout(self.extensions_widget)
        self.extensions_layout.setSpacing(12)
        self.extensions_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.extensions_widget)
        layout.addWidget(scroll)
        
        # Load extensions
        self.load_extensions()
        
        # Update stats
        self.update_stats()
    
    def load_extensions(self):
        """Load installed extensions into grid"""
        # Clear existing cards
        for i in reversed(range(self.extensions_layout.count())):
            widget = self.extensions_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Add extension cards
        for ext_id, ext_info in self.browser.extension_manager.extensions.items():
            card = ExtensionCard(ext_id, ext_info, self)
            self.extensions_layout.addWidget(card)
        
        # Add stretch at the end
        self.extensions_layout.addStretch()
        
        # Update stats
        self.update_stats()
    
    def filter_extensions(self, search_text):
        """Filter extensions based on search text"""
        search_text = search_text.lower()
        
        for i in range(self.extensions_layout.count()):
            widget = self.extensions_layout.itemAt(i).widget()
            if isinstance(widget, ExtensionCard):
                name = widget.extension_info['manifest'].get('name', '').lower()
                desc = widget.extension_info['manifest'].get('description', '').lower()
                
                if search_text in name or search_text in desc:
                    widget.show()
                else:
                    widget.hide()
    
    def update_stats(self):
        """Update extension statistics"""
        total = len(self.browser.extension_manager.extensions)
        enabled = sum(1 for ext in self.browser.extension_manager.extensions.values() 
                     if ext['enabled'])
        
        self.stats_label.setText(f"{total} extension{'s' if total != 1 else ''} installed • "
                               f"{enabled} enabled")
    
    def install_extension(self):
        """Show dialog to install a new extension"""
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Load Extension")
        file_dialog.setNameFilter("Chrome Extensions (*.crx);;All Files (*)")
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            if files:
                try:
                    self.browser.extension_manager.install_extension(files[0])
                    self.load_extensions()
                except Exception as e:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(
                        self,
                        "Installation Error",
                        f"Failed to install extension:\n{str(e)}",
                        QMessageBox.StandardButton.Ok
                    )

class ExtensionConfig(QDialog):
    """Dialog for configuring an extension"""
    
    def __init__(self, extension_id: str, extension_info: dict, browser, parent=None):
        super().__init__(parent)
        self.extension_id = extension_id
        self.extension_info = extension_info
        self.browser = browser
        
        self.setWindowTitle(f"Configure {extension_info['manifest'].get('name', 'Extension')}")
        
        layout = QVBoxLayout(self)
        
        # Extension info
        info_layout = QVBoxLayout()
        name = QLabel(f"<b>{extension_info['manifest'].get('name', 'Unknown Extension')}</b>")
        version = QLabel(f"Version: {extension_info['manifest'].get('version', 'Unknown')}")
        desc = QLabel(extension_info['manifest'].get('description', ''))
        desc.setWordWrap(True)
        
        info_layout.addWidget(name)
        info_layout.addWidget(version)
        info_layout.addWidget(desc)
        layout.addLayout(info_layout)
        
        # Permissions
        if 'permissions' in extension_info['manifest']:
            perm_label = QLabel("<b>Permissions:</b>")
            perm_list = QLabel("\n".join(f"• {p}" for p in extension_info['manifest']['permissions']))
            layout.addWidget(perm_label)
            layout.addWidget(perm_list)
        
        # Controls
        controls = QHBoxLayout()
        
        enable_btn = QPushButton(
            "Disable" if extension_info['enabled'] else "Enable"
        )
        enable_btn.clicked.connect(self.toggle_extension)
        
        uninstall_btn = QPushButton("Uninstall")
        uninstall_btn.clicked.connect(self.uninstall_extension)
        
        controls.addWidget(enable_btn)
        controls.addWidget(uninstall_btn)
        layout.addLayout(controls)
        
        # Options page
        if 'options_page' in extension_info['manifest']:
            options_btn = QPushButton("Extension Options")
            options_btn.clicked.connect(self.show_options)
            layout.addWidget(options_btn)
    
    def toggle_extension(self):
        """Toggle extension enabled state"""
        if self.extension_info['enabled']:
            self.browser.extension_manager.disable_extension(self.extension_id)
        else:
            self.browser.extension_manager.enable_extension(self.extension_id)
        self.accept()
    
    def uninstall_extension(self):
        """Uninstall the extension"""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            f"Are you sure you want to uninstall this extension?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.browser.extension_manager.uninstall_extension(self.extension_id)
            self.accept()
    
    def show_options(self):
        """Show extension options page"""
        # TODO: Implement options page display
        pass 