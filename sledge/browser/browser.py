import sys
import os
from PyQt6.QtCore import QUrl, Qt, QSize
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit, QProgressBar, 
    QStatusBar, QTabWidget, QMenu, QWidget
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEngineSettings
)
from PyQt6.QtGui import QAction, QIcon, QColor

from sledge.browser.theme import Theme
from sledge.browser.security import RequestInterceptor

# class TabWidget(QTabWidget):
#     """Enhanced tab widget with tab management features"""
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setDocumentMode(True)
#         self.setTabsClosable(True)
#         self.setMovable(True)
#         self.setTabBarAutoHide(False)
        
#         # Style the tab bar
#         self.setStyleSheet("""
#             QTabBar::tab {
#                 background: #2e3440;
#                 color: #d8dee9;
#                 padding: 8px 20px;
#                 border: none;
#                 min-width: 150px;
#                 max-width: 300px;
#             }
#             QTabBar::tab:selected {
#                 background: #3b4252;
#                 border-bottom: 2px solid #88c0d0;
#             }
#             QTabBar::tab:hover {
#                 background: #434c5e;
#             }
#         """)

class BrowserWindow(QMainWindow):
    def __init__(self, app=None):
        super().__init__()
        self.app = app
        
        # Initialize core components
        self.theme = Theme()
        
        # Set up the web profile
        self.profile = QWebEngineProfile.defaultProfile()
        
        # Configure web settings
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ErrorPageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        
        # Set up request interceptor
        self.profile.setUrlRequestInterceptor(RequestInterceptor(self))
        
        # Set up the main UI
        self.setWindowTitle('Sledge Browser')
        self.setGeometry(100, 100, 1280, 800)
        
        # Create tab widget
        self.tabs = TabWidget()
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)
        
        # Create toolbar
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(self.toolbar)
        
        # Add navigation buttons
        back_btn = QAction(QIcon.fromTheme('go-previous'), 'Back', self)
        back_btn.setShortcut('Alt+Left')
        back_btn.triggered.connect(lambda: self.current_tab().back())
        self.toolbar.addAction(back_btn)
        
        forward_btn = QAction(QIcon.fromTheme('go-next'), 'Forward', self)
        forward_btn.setShortcut('Alt+Right')
        forward_btn.triggered.connect(lambda: self.current_tab().forward())
        self.toolbar.addAction(forward_btn)
        
        reload_btn = QAction(QIcon.fromTheme('view-refresh'), 'Reload', self)
        reload_btn.setShortcut('F5')
        reload_btn.triggered.connect(lambda: self.current_tab().reload())
        self.toolbar.addAction(reload_btn)
        
        # Add New Tab button
        new_tab_btn = QAction(QIcon.fromTheme('tab-new'), 'New Tab', self)
        new_tab_btn.setShortcut('Ctrl+T')
        new_tab_btn.triggered.connect(lambda: self.add_new_tab())
        self.toolbar.addAction(new_tab_btn)
        
        self.toolbar.addSeparator()
        
        # Add URL bar
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_bar)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(120)
        self.toolbar.addWidget(self.progress_bar)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Apply theme
        self.theme.apply_to_window(self)
        
        # Add initial tab
        self.add_new_tab(QUrl('https://duckduckgo.com'))

    def add_new_tab(self, qurl=None, label="New Tab"):
        """Add new browser tab"""
        if qurl is None:
            qurl = QUrl('https://duckduckgo.com')
            
        browser = QWebEngineView()
        browser.setUrl(qurl)
        
        # Connect signals
        browser.urlChanged.connect(lambda url, browser=browser: 
            self.update_urlbar(url, browser))
        browser.loadProgress.connect(self.update_progress)
        browser.titleChanged.connect(lambda title, browser=browser:
            self.tabs.setTabText(self.tabs.indexOf(browser), title))
        
        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)
        return browser

    def close_tab(self, i):
        """Close tab at given index"""
        if self.tabs.count() < 2:  # Keep at least one tab
            return
        self.tabs.removeTab(i)

    def current_tab(self):
        """Get current tab widget"""
        return self.tabs.currentWidget()

    def navigate_to_url(self):
        """Navigate to URL in url bar"""
        q = QUrl(self.url_bar.text())
        if q.scheme() == "":
            q.setScheme("http")
        self.current_tab().setUrl(q)

    def update_urlbar(self, q, browser=None):
        """Update URL bar with current URL"""
        if browser != self.current_tab():
            return
        self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0)

    def update_progress(self, progress):
        """Update progress bar"""
        self.progress_bar.setValue(progress)
        if progress == 100:
            self.status_bar.showMessage('Ready')
        else:
            self.status_bar.showMessage('Loading...')

def main(argv=None):
    """Main entry point for the browser"""
    if argv is None:
        argv = []
        
    app = QApplication(argv)
    window = BrowserWindow(app)
    window.show()
    return app.exec()

if __name__ == '__main__':
    main() 