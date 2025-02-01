from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QCheckBox, QLineEdit, QPushButton, QComboBox,
    QFileDialog, QGroupBox
)
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.settings = browser.settings
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        # Create tab widget
        tabs = QTabWidget()
        tabs.addTab(self.create_general_tab(), "General")
        tabs.addTab(self.create_privacy_tab(), "Privacy")
        tabs.addTab(self.create_appearance_tab(), "Appearance")
        tabs.addTab(self.create_downloads_tab(), "Downloads")

        layout.addWidget(tabs)

        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

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