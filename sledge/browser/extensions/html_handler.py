from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QUrl, Qt
from pathlib import Path

class ExtensionWebView(QWebEngineView):
    """Web view for extension HTML content"""
    
    def __init__(self, extension_id: str, manifest: dict, runtime, parent=None):
        super().__init__(parent)
        self.extension_id = extension_id
        self.manifest = manifest
        self.runtime = runtime
        
        # Create isolated profile for extension
        self.profile = QWebEngineProfile(self)
        self.profile.setHttpUserAgent(self.profile.httpUserAgent() + f" Extension/{extension_id}")
        
        # Create page with isolated profile
        self.page = QWebEnginePage(self.profile, self)
        self.setPage(self.page)
        
        # Inject extension APIs
        self._inject_apis()
        
    def _inject_apis(self):
        """Inject extension APIs into the page"""
        # Add bridge object
        self.page.runJavaScript("""
            const chrome = window.chrome || {};
            const browser = window.browser || {};
        """)
        
        # Inject API proxies
        apis = {
            'runtime': ['sendMessage', 'connect', 'getManifest'],
            'storage': ['local.get', 'local.set', 'local.remove', 'local.clear'],
            'tabs': ['query', 'create', 'update', 'remove'],
            'windows': ['get', 'getAll', 'create']
        }
        
        for api_name, methods in apis.items():
            for method in methods:
                self._inject_api_method(api_name, method)
    
    def _inject_api_method(self, api_name: str, method: str):
        """Inject a single API method"""
        parts = method.split('.')
        if len(parts) > 1:
            # Nested method (e.g. storage.local.get)
            js = f"""
                if (!chrome.{api_name}) chrome.{api_name} = {{}};
                if (!chrome.{api_name}.{parts[0]}) chrome.{api_name}.{parts[0]} = {{}};
                chrome.{api_name}.{parts[0]}.{parts[1]} = (...args) => 
                    window.sledgeBridge.invoke_api('{api_name}', '{method}', ...args);
                browser.{api_name}.{parts[0]}.{parts[1]} = chrome.{api_name}.{parts[0]}.{parts[1]};
            """
        else:
            # Top-level method
            js = f"""
                if (!chrome.{api_name}) chrome.{api_name} = {{}};
                chrome.{api_name}.{method} = (...args) => 
                    window.sledgeBridge.invoke_api('{api_name}', '{method}', ...args);
                browser.{api_name}.{method} = chrome.{api_name}.{method};
            """
        self.page.runJavaScript(js)

class ExtensionPopup(QWidget):
    """Widget for extension popup content"""
    
    def __init__(self, extension_id: str, manifest: dict, runtime, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.extension_id = extension_id
        self.manifest = manifest
        self.runtime = runtime
        
        # Set up layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create web view
        self.web_view = ExtensionWebView(extension_id, manifest, runtime, self)
        layout.addWidget(self.web_view)
        
        # Set size
        if 'browser_action' in manifest:
            width = manifest['browser_action'].get('default_width', 400)
            height = manifest['browser_action'].get('default_height', 600)
            self.resize(width, height)
    
    def load_popup(self):
        """Load popup content"""
        if 'browser_action' in self.manifest:
            popup_path = self.manifest['browser_action'].get('default_popup')
            if popup_path:
                full_path = Path(self.runtime.context.get_url(popup_path))
                if full_path.exists():
                    self.web_view.setUrl(QUrl.fromLocalFile(str(full_path)))

class ExtensionOptions(QWidget):
    """Widget for extension options page"""
    
    def __init__(self, extension_id: str, manifest: dict, runtime, parent=None):
        super().__init__(parent)
        self.extension_id = extension_id
        self.manifest = manifest
        self.runtime = runtime
        
        # Set up layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create web view
        self.web_view = ExtensionWebView(extension_id, manifest, runtime, self)
        layout.addWidget(self.web_view)
        
        self.setWindowTitle(f"{manifest.get('name', 'Extension')} Options")
        self.resize(800, 600)
    
    def load_options(self):
        """Load options page content"""
        if 'options_page' in self.manifest:
            options_path = self.manifest['options_page']
            full_path = Path(self.runtime.context.get_url(options_path))
            if full_path.exists():
                self.web_view.setUrl(QUrl.fromLocalFile(str(full_path))) 