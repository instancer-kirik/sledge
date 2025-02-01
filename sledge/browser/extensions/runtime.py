from typing import Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from .api import TabAPI, WindowAPI, StorageAPI, WebRequestAPI, ContextMenuAPI
from .js_engine import JSEngine

class ExtensionRuntime(QObject):
    """Runtime environment for extensions"""
    
    message_received = pyqtSignal(str, object)  # extension_id, message
    
    def __init__(self, extension_id: str, manifest: dict, browser):
        super().__init__()
        self.extension_id = extension_id
        self.manifest = manifest
        self.browser = browser
        
        # Initialize APIs based on permissions
        self.apis = self._create_apis()
        
        # Initialize JS engine
        self.js_engine = JSEngine(self)
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        
        # Extension context
        self.context = ExtensionContext(extension_id, manifest)

    def _create_apis(self) -> dict:
        """Create API instances based on permissions"""
        permissions = self.manifest.get('permissions', [])
        apis = {}

        # Map permissions to API classes
        api_mapping = {
            'tabs': TabAPI,
            'windows': WindowAPI,
            'storage': StorageAPI,
            'webRequest': WebRequestAPI,
            'contextMenus': ContextMenuAPI
        }

        for permission, api_class in api_mapping.items():
            if permission in permissions:
                apis[permission] = api_class(self)

        return apis

    def execute_script(self, script: str, context: Dict[str, Any] = None):
        """Execute extension script in isolated environment"""
        return self.js_engine.execute_script(script, context)

    def handle_message(self, message: Any, sender: Dict[str, Any] = None):
        """Handle messages sent to the extension"""
        for handler in self.message_handlers.values():
            try:
                handler(message, sender)
            except Exception as e:
                print(f"Error in message handler: {e}")

    def add_message_listener(self, handler: Callable):
        """Add a message listener"""
        handler_id = id(handler)
        self.message_handlers[handler_id] = handler
        return handler_id

    def remove_message_listener(self, handler_id: int):
        """Remove a message listener"""
        if handler_id in self.message_handlers:
            del self.message_handlers[handler_id]

    def send_message(self, message: Any, target_id: str = None):
        """Send a message to another extension or the browser"""
        if target_id:
            # Send to specific extension
            self.browser.extension_manager.send_message(
                self.extension_id, target_id, message
            )
        else:
            # Broadcast message
            self.message_received.emit(self.extension_id, message)

class ExtensionContext:
    """Context object for extension execution"""
    
    def __init__(self, extension_id: str, manifest: dict):
        self.id = extension_id
        self.manifest = manifest
        self.permissions = manifest.get('permissions', [])
        
    def check_permission(self, permission: str) -> bool:
        """Check if extension has a specific permission"""
        return permission in self.permissions
        
    def get_url(self, path: str) -> str:
        """Get extension resource URL"""
        return f'chrome-extension://{self.id}/{path}' 