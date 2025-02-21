from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QLineEdit, QPushButton, QComboBox,
    QFileDialog, QGroupBox, QDialogButtonBox, QGridLayout
)
from PyQt6.QtCore import Qt, QUrl
from ..security import SecurityPanel

class SettingsDialog(QDialog):
    """Browser settings dialog"""
    
    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.settings = browser.settings
        self.setWindowTitle("Settings")
        self.resize(600, 400)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Tab widget for different settings sections
        tabs = QTabWidget()
        
        # Security settings
        security_panel = SecurityPanel(browser.settings)
        tabs.addTab(security_panel, "Security")
        
        # Theme settings
        from ..ui.widgets import StyleAdjusterPanel
        theme_panel = StyleAdjusterPanel(browser.theme)
        tabs.addTab(theme_panel, "Theme")
        
        layout.addWidget(tabs)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def create_general_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Startup group
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout()
        
        self.restore_session = QCheckBox("Restore previous session")
        self.restore_session.setChecked(self.settings.get('startup', 'restore_session'))
        
        home_layout = QHBoxLayout()
        home_layout.addWidget(QLabel("Homepage:"))
        self.homepage = QLineEdit(self.settings.get('startup', 'home_page'))
        home_layout.addWidget(self.homepage)

        startup_layout.addWidget(self.restore_session)
        startup_layout.addLayout(home_layout)
        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)
        
        layout.addStretch()
        return tab

    def create_privacy_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.do_not_track = QCheckBox("Send Do Not Track request")
        self.do_not_track.setChecked(self.settings.get('privacy', 'do_not_track'))
        
        self.block_cookies = QCheckBox("Block third-party cookies")
        self.block_cookies.setChecked(self.settings.get('privacy', 'block_third_party_cookies'))
        
        self.clear_exit = QCheckBox("Clear browsing data on exit")
        self.clear_exit.setChecked(self.settings.get('privacy', 'clear_on_exit'))

        layout.addWidget(self.do_not_track)
        layout.addWidget(self.block_cookies)
        layout.addWidget(self.clear_exit)
        layout.addStretch()
        return tab

    def create_appearance_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.dark_mode = QCheckBox("Dark mode")
        self.dark_mode.setChecked(self.settings.get('appearance', 'dark_mode'))
        
        tab_pos_layout = QHBoxLayout()
        tab_pos_layout.addWidget(QLabel("Tab position:"))
        self.tab_position = QComboBox()
        self.tab_position.addItems(["Top", "Bottom"])
        self.tab_position.setCurrentText(
            self.settings.get('appearance', 'tab_position').capitalize()
        )
        tab_pos_layout.addWidget(self.tab_position)

        self.show_bookmarks = QCheckBox("Show bookmarks bar")
        self.show_bookmarks.setChecked(self.settings.get('appearance', 'show_bookmarks_bar'))

        layout.addWidget(self.dark_mode)
        layout.addLayout(tab_pos_layout)
        layout.addWidget(self.show_bookmarks)
        layout.addStretch()
        return tab

    def create_downloads_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Download location:"))
        self.download_path = QLineEdit(self.settings.get('downloads', 'default_path'))
        path_layout.addWidget(self.download_path)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_download_path)
        path_layout.addWidget(browse_btn)

        self.ask_location = QCheckBox("Always ask where to save files")
        self.ask_location.setChecked(self.settings.get('downloads', 'ask_for_location'))

        layout.addLayout(path_layout)
        layout.addWidget(self.ask_location)
        layout.addStretch()
        return tab

    def browse_download_path(self):
        path = QFileDialog.getExistingDirectory(
            self, "Choose Download Location",
            self.download_path.text()
        )
        if path:
            self.download_path.setText(path)

    def accept(self):
        # Save all settings
        self.settings.set('startup', 'restore_session', self.restore_session.isChecked())
        self.settings.set('startup', 'home_page', self.homepage.text())
        
        self.settings.set('privacy', 'do_not_track', self.do_not_track.isChecked())
        self.settings.set('privacy', 'block_third_party_cookies', self.block_cookies.isChecked())
        self.settings.set('privacy', 'clear_on_exit', self.clear_exit.isChecked())
        
        self.settings.set('appearance', 'dark_mode', self.dark_mode.isChecked())
        self.settings.set('appearance', 'tab_position', self.tab_position.currentText().lower())
        self.settings.set('appearance', 'show_bookmarks_bar', self.show_bookmarks.isChecked())
        
        self.settings.set('downloads', 'default_path', self.download_path.text())
        self.settings.set('downloads', 'ask_for_location', self.ask_location.isChecked())
        
        super().accept()

class PortGridDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Ports")
        self.setModal(True)
        
        layout = QGridLayout(self)
        layout.setSpacing(4)
        
        # Common development ports
        ports = [
            ("Django", 8000),
            ("React", 3000),
            ("Vue", 8080),
            ("Flask", 5000),
            ("Node", 3001),
            ("Webpack", 8081),
            ("Gleam", 8002),
            ("Custom", None)
        ]
        
        # Create grid of port buttons
        for i, (name, port) in enumerate(ports):
            row, col = divmod(i, 3)
            btn = QPushButton(f"{name}\n:{port}" if port else "Custom")
            btn.setMinimumWidth(100)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px;
                    background: #3b4252;
                    border: none;
                    border-radius: 4px;
                    color: #d8dee9;
                }
                QPushButton:hover {
                    background: #434c5e;
                }
            """)
            if port:
                btn.clicked.connect(lambda checked, p=port: self.use_port(p))
            else:
                btn.clicked.connect(self.custom_port)
            layout.addWidget(btn, row, col)

    def use_port(self, port):
        try:
            navbar = self.parent()
            current_url = navbar.url_bar.text()
            url = QUrl(current_url)
            
            # Default to http://localhost if no URL
            if not url.isValid() or not url.host():
                new_url = f"http://localhost:{port}"
            else:
                new_url = f"{url.scheme() or 'http'}://{url.host() or 'localhost'}:{port}{url.path()}"
            
            navbar.url_bar.setText(new_url)
            if hasattr(navbar.parent(), 'navigate_to_url'):
                navbar.parent().navigate_to_url(new_url)
        except Exception as e:
            print(f"Error updating port: {e}")
        self.close()

    def custom_port(self):
        # Implement custom port functionality
        pass 