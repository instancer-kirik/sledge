from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtCore import QObject, QUrl
from pathlib import Path
import json

class BackgroundScript(QObject):
    """Handler for extension background scripts"""
    
    def __init__(self, extension_id: str, manifest: dict, runtime):
        super().__init__()
        self.extension_id = extension_id
        self.manifest = manifest
        self.runtime = runtime
        
        # Create hidden web view for script execution
        self.web_view = QWebEngineView()
        self.web_view.hide()
        
        # Create isolated profile
        self.profile = QWebEngineProfile(self)
        self.profile.setHttpUserAgent(self.profile.httpUserAgent() + f" Extension/{extension_id}")
        
        # Create page with isolated profile
        self.page = QWebEnginePage(self.profile, self)
        self.web_view.setPage(self.page)
        
        # Initialize background script
        self._init_background()
    
    def _init_background(self):
        """Initialize background script environment"""
        # Inject extension APIs
        self.page.runJavaScript("""
            const chrome = {};
            const browser = {};
            
            // Create message passing system
            chrome.runtime = {
                onMessage: {
                    addListener: (callback) => window.sledgeBridge.register_message_listener(callback),
                    removeListener: (callback) => window.sledgeBridge.unregister_message_listener(callback)
                },
                sendMessage: (message) => window.sledgeBridge.send_message(message),
                getManifest: () => window.sledgeBridge.get_manifest()
            };
            browser.runtime = chrome.runtime;
        """)
        
        # Load background scripts
        self._load_scripts()
    
    def _load_scripts(self):
        """Load and execute background scripts"""
        if 'background' in self.manifest:
            if 'scripts' in self.manifest['background']:
                for script_path in self.manifest['background']['scripts']:
                    self._load_script(script_path)
            elif 'page' in self.manifest['background']:
                self._load_background_page(self.manifest['background']['page'])
    
    def _load_script(self, script_path: str):
        """Load and execute a background script"""
        full_path = Path(self.runtime.context.get_url(script_path))
        if full_path.exists():
            try:
                with open(full_path) as f:
                    script = f.read()
                self.page.runJavaScript(script)
            except Exception as e:
                print(f"Error loading background script {script_path}: {e}")
    
    def _load_background_page(self, page_path: str):
        """Load a background page"""
        full_path = Path(self.runtime.context.get_url(page_path))
        if full_path.exists():
            self.page.setUrl(QUrl.fromLocalFile(str(full_path)))
    
    def handle_message(self, message, sender=None):
        """Handle a message sent to the background script"""
        # Create sender object
        sender_obj = json.dumps(sender) if sender else 'null'
        
        # Forward message to background script
        js = f"""
            const message = {json.dumps(message)};
            const sender = {sender_obj};
            
            // Notify all listeners
            chrome.runtime._messageListeners.forEach(listener => {{
                try {{
                    listener(message, sender);
                }} catch (e) {{
                    console.error('Error in message listener:', e);
                }}
            }});
        """
        self.page.runJavaScript(js)
    
    def cleanup(self):
        """Clean up background script resources"""
        self.web_view.deleteLater()
        self.page.deleteLater()
        self.profile.deleteLater()

class BackgroundScriptManager:
    """Manages background scripts for all extensions"""
    
    def __init__(self):
        self.scripts = {}
    
    def load_background_script(self, extension_id: str, manifest: dict, runtime):
        """Load background script for an extension"""
        if 'background' in manifest:
            script = BackgroundScript(extension_id, manifest, runtime)
            self.scripts[extension_id] = script
    
    def unload_background_script(self, extension_id: str):
        """Unload background script for an extension"""
        if extension_id in self.scripts:
            script = self.scripts.pop(extension_id)
            script.cleanup()
    
    def handle_message(self, extension_id: str, message, sender=None):
        """Handle a message for a specific extension"""
        if extension_id in self.scripts:
            self.scripts[extension_id].handle_message(message, sender)
    
    def cleanup(self):
        """Clean up all background scripts"""
        for extension_id in list(self.scripts.keys()):
            self.unload_background_script(extension_id) 