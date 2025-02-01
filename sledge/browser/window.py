from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QSplitter, QStatusBar, QLineEdit, QPushButton)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon

from .webview import WebView
from .style_panel import StylePanel
from .theme import BrowserTheme

class BrowserWindow(QMainWindow):
    """Main browser window implementation"""
    
    DEFAULT_URL = "https://duckduckgo.com"
    
    def __init__(self):
        super().__init__()
        self.browser_theme = BrowserTheme()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle("Sledge Browser")
        self.setMinimumSize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create navigation bar
        nav_bar = QWidget()
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(4, 4, 4, 4)
        nav_layout.setSpacing(4)
        
        # Add URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or search...")
        self.url_bar.returnPressed.connect(self._handle_url_enter)
        nav_layout.addWidget(self.url_bar)
        
        # Add navigation buttons
        self.back_button = QPushButton("←")
        self.back_button.clicked.connect(self._handle_back)
        nav_layout.insertWidget(0, self.back_button)
        
        self.forward_button = QPushButton("→")
        self.forward_button.clicked.connect(self._handle_forward)
        nav_layout.insertWidget(1, self.forward_button)
        
        self.reload_button = QPushButton("↻")
        self.reload_button.clicked.connect(self._handle_reload)
        nav_layout.insertWidget(2, self.reload_button)
        
        main_layout.addWidget(nav_bar)
        
        # Create horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create left panel for browser
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Create and configure tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(False)  # Set to False to make tabs more visible
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self._handle_tab_change)
        
        # Debug: Ensure minimum size and visibility
        self.tab_widget.setMinimumSize(400, 300)
        print(f"TabWidget created: visible={self.tab_widget.isVisible()}, size={self.tab_widget.size()}")
        
        # Set tab bar style
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #2e3440;
            }
            QTabWidget::tab-bar {
                left: 0;
                alignment: left;
            }
            QTabBar::tab {
                background: #2e3440;
                color: #d8dee9;
                padding: 8px 20px;
                border: 1px solid #3b4252;
                border-bottom: none;
                margin-right: 2px;
                min-width: 150px;
                max-width: 300px;
            }
            QTabBar::tab:selected {
                background: #3b4252;
                color: #88c0d0;
                border: 1px solid #4c566a;
                border-bottom: 2px solid #88c0d0;
            }
            QTabBar::tab:hover:!selected {
                background: #434c5e;
            }
            QTabBar::close-button {
                image: url(close.png);
                subcontrol-position: right;
                margin: 2px;
            }
            QTabBar::close-button:hover {
                background: #bf616a;
                border-radius: 2px;
            }
        """)
        
        left_layout.addWidget(self.tab_widget)
        splitter.addWidget(left_panel)
        
        # Debug: Verify left panel setup
        left_panel.setMinimumSize(500, 400)
        print(f"Left panel: visible={left_panel.isVisible()}, size={left_panel.size()}")
        
        # Create right-side panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add style panel
        self.style_panel = StylePanel(self.browser_theme)
        self.style_panel.style_changed.connect(self.on_theme_changed)
        right_layout.addWidget(self.style_panel)
        
        splitter.addWidget(right_panel)
        
        # Add splitter to main layout
        main_layout.addWidget(splitter)
        
        # Set initial splitter sizes (80% for tabs, 20% for style panel)
        splitter.setMinimumSize(800, 500)  # Ensure splitter has minimum size
        # Wait until window is shown to set sizes
        self.show()  # Show window first
        splitter.setSizes([int(self.width() * 0.8), int(self.width() * 0.2)])
        print(f"Splitter: visible={splitter.isVisible()}, size={splitter.size()}")
        
        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Create initial tab
        self.add_new_tab()
        
        # Apply initial theme
        self.apply_theme()
        
    def _handle_url_enter(self):
        """Handle URL bar enter press"""
        url = self.url_bar.text()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            current_tab.setUrl(QUrl(url))
            
    def _handle_back(self):
        """Handle back button click"""
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            current_tab.back()
            
    def _handle_forward(self):
        """Handle forward button click"""
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            current_tab.forward()
            
    def _handle_reload(self):
        """Handle reload button click"""
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            current_tab.reload()
            
    def _handle_tab_change(self, index):
        """Handle tab change"""
        if index >= 0:
            current_tab = self.tab_widget.widget(index)
            if current_tab and hasattr(current_tab, 'url'):
                self.url_bar.setText(current_tab.url().toString())
                
    def add_new_tab(self, url=None):
        """Add a new browser tab"""
        if url is None:
            url = self.DEFAULT_URL
            
        web_view = WebView(self.browser_theme)
        web_view.url_changed.connect(self.update_tab)
        web_view.setUrl(QUrl(url))
        
        index = self.tab_widget.addTab(web_view, "Loading...")
        self.tab_widget.setCurrentIndex(index)
        return index
        
    def close_tab(self, index):
        """Close the tab at the given index"""
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)
        else:
            # Don't close the last tab, navigate to home instead
            web_view = self.tab_widget.widget(0)
            web_view.setUrl(QUrl(self.DEFAULT_URL))
            
    def update_tab(self, url):
        """Update tab title and icon"""
        web_view = self.sender()
        index = self.tab_widget.indexOf(web_view)
        if index != -1:
            title = web_view.page().title() or "New Tab"
            self.tab_widget.setTabText(index, title)
            
            # Update icon if available
            icon = web_view.page().icon()
            if not icon.isNull():
                self.tab_widget.setTabIcon(index, icon)
                
    def on_theme_changed(self, theme_name):
        """Handle theme changes"""
        self.browser_theme.set_theme(theme_name)
        self.apply_theme()
        
        # Update all web views
        for i in range(self.tab_widget.count()):
            web_view = self.tab_widget.widget(i)
            web_view.set_theme(theme_name)
            
    def apply_theme(self):
        """Apply the current theme to the window"""
        self.setStyleSheet(self.browser_theme.get_stylesheet())
        
    def update_status(self, message):
        """Update the status bar message"""
        self.status_bar.showMessage(message) 