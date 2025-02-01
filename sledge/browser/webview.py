from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, pyqtSignal

class WebView(QWebEngineView):
    """Custom WebView implementation with dark mode support"""
    
    url_changed = pyqtSignal(str)  # Signal emitted when URL changes
    
    def __init__(self, browser_theme, parent=None):
        super().__init__(parent)
        self.browser_theme = browser_theme
        self.init_view()
        
    def init_view(self):
        """Initialize the web view"""
        # Set default page
        self.setUrl(QUrl("about:blank"))
        
        # Connect signals
        self.urlChanged.connect(self._on_url_changed)
        self.loadFinished.connect(self._on_load_finished)
        
    def _on_url_changed(self, url):
        """Handle URL changes"""
        self.url_changed.emit(url.toString())
        
    def _on_load_finished(self, ok):
        """Handle page load completion"""
        if ok:
            # Inject theme styles
            url = self.url()
            css, js = self.browser_theme.inject_style(url)
            
            # Inject CSS
            js_css = f"""
                (function() {{
                    const style = document.createElement('style');
                    style.textContent = `{css}`;
                    document.head.appendChild(style);
                }})();
            """
            self.page().runJavaScript(js_css)
            
            # Inject theme enforcement JavaScript
            self.page().runJavaScript(js)
            
    def set_theme(self, theme_name):
        """Update the theme"""
        self.browser_theme.set_theme(theme_name)
        self._on_load_finished(True)  # Re-apply styles 