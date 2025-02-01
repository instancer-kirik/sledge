from typing import Any, Dict, List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from ..storage import ExtensionStorage

class BaseAPI(QObject):
    """Base class for extension APIs"""
    
    def __init__(self, runtime):
        super().__init__()
        self.runtime = runtime
        self.browser = runtime.browser

class TabAPI(BaseAPI):
    """Implementation of the chrome.tabs.* API"""
    
    tab_created = pyqtSignal(dict)
    tab_updated = pyqtSignal(int, dict, dict)
    tab_removed = pyqtSignal(int, dict)
    
    def query(self, query_info: Dict[str, Any]) -> List[dict]:
        """Query for tabs that match the criteria"""
        tabs = []
        for i in range(self.browser.tabs.count()):
            tab = self.browser.tabs.widget(i)
            if self._matches_query(tab, query_info):
                tabs.append(self._tab_to_dict(tab, i))
        return tabs
    
    def create(self, create_properties: Dict[str, Any]) -> dict:
        """Create a new tab"""
        url = create_properties.get('url')
        active = create_properties.get('active', True)
        index = create_properties.get('index', -1)
        
        tab_id = self.browser.add_new_tab(url, active=active, index=index)
        return self._tab_to_dict(self.browser.tabs.widget(tab_id), tab_id)
    
    def update(self, tab_id: int, update_properties: Dict[str, Any]) -> dict:
        """Update the properties of a tab"""
        tab = self.browser.tabs.widget(tab_id)
        if not tab:
            raise ValueError(f"No tab with id {tab_id}")
            
        if 'url' in update_properties:
            tab.setUrl(update_properties['url'])
        if 'active' in update_properties and update_properties['active']:
            self.browser.tabs.setCurrentIndex(tab_id)
            
        return self._tab_to_dict(tab, tab_id)
    
    def remove(self, tab_ids: List[int]):
        """Close one or more tabs"""
        if isinstance(tab_ids, int):
            tab_ids = [tab_ids]
            
        for tab_id in tab_ids:
            self.browser.tabs.removeTab(tab_id)
    
    def _matches_query(self, tab, query_info: Dict[str, Any]) -> bool:
        """Check if a tab matches the query criteria"""
        if 'active' in query_info and tab.isActiveWindow() != query_info['active']:
            return False
        if 'url' in query_info and query_info['url'] not in tab.url().toString():
            return False
        return True
    
    def _tab_to_dict(self, tab, tab_id: int) -> dict:
        """Convert a tab to a dictionary format"""
        return {
            'id': tab_id,
            'index': tab_id,
            'url': tab.url().toString(),
            'title': self.browser.tabs.tabText(tab_id),
            'active': self.browser.tabs.currentIndex() == tab_id,
            'status': 'complete' if tab.loadProgress() == 100 else 'loading'
        }

class WindowAPI(BaseAPI):
    """Implementation of the chrome.windows.* API"""
    
    def get(self, window_id: int) -> dict:
        """Get details about a window"""
        return self._window_to_dict(self.browser)
    
    def getAll(self, get_info: Dict[str, Any] = None) -> List[dict]:
        """Get all windows"""
        return [self._window_to_dict(self.browser)]
    
    def create(self, create_data: Dict[str, Any]) -> dict:
        """Create a new window"""
        # TODO: Implement multiple windows
        return self._window_to_dict(self.browser)
    
    def _window_to_dict(self, window) -> dict:
        """Convert a window to a dictionary format"""
        return {
            'id': 1,  # TODO: Proper window ID management
            'focused': window.isActiveWindow(),
            'top': window.y(),
            'left': window.x(),
            'width': window.width(),
            'height': window.height(),
            'tabs': [self.runtime.apis['tabs']._tab_to_dict(window.tabs.widget(i), i)
                    for i in range(window.tabs.count())]
        }

class StorageAPI(BaseAPI):
    """Implementation of the chrome.storage.* API"""
    
    storage_changed = pyqtSignal(dict)  # Changes dictionary
    
    def __init__(self, runtime):
        super().__init__(runtime)
        self.storage = self.browser.extension_manager.storage_manager.get_storage(
            self.runtime.extension_id
        )
        self.areas = {
            'local': self._create_area('local'),
            'sync': self._create_area('sync'),
            'managed': self._create_area('managed', read_only=True)
        }
        
    def _create_area(self, name: str, read_only: bool = False) -> Dict[str, Any]:
        """Create a storage area proxy"""
        return {
            'get': lambda keys=None: self.get(keys, name),
            'set': (lambda _: None) if read_only else lambda items: self.set(items, name),
            'remove': (lambda _: None) if read_only else lambda keys: self.remove(keys, name),
            'clear': (lambda: None) if read_only else lambda: self.clear(name),
            'getBytesInUse': lambda keys=None: self.get_bytes_in_use(keys, name)
        }
    
    def get(self, keys: Optional[List[str]] = None, area: str = 'local') -> Dict[str, Any]:
        """Get one or more items from storage"""
        try:
            return self.storage.get(keys, area)
        except Exception as e:
            print(f"Error getting storage items: {e}")
            return {}
    
    def set(self, items: Dict[str, Any], area: str = 'local'):
        """Set one or more items in storage"""
        try:
            # Get old values for change detection
            old_values = self.storage.get(list(items.keys()), area)
            
            # Set new values
            self.storage.set(items, area)
            
            # Emit changes
            changes = {
                key: {
                    'oldValue': old_values.get(key),
                    'newValue': value
                }
                for key, value in items.items()
                if old_values.get(key) != value
            }
            if changes:
                self.storage_changed.emit(changes)
                
        except Exception as e:
            print(f"Error setting storage items: {e}")
    
    def remove(self, keys: List[str], area: str = 'local'):
        """Remove one or more items from storage"""
        try:
            # Get old values for change detection
            old_values = self.storage.get(keys, area)
            
            # Remove items
            self.storage.remove(keys, area)
            
            # Emit changes
            changes = {
                key: {
                    'oldValue': value,
                    'newValue': None
                }
                for key, value in old_values.items()
            }
            if changes:
                self.storage_changed.emit(changes)
                
        except Exception as e:
            print(f"Error removing storage items: {e}")
    
    def clear(self, area: str = 'local'):
        """Remove all items from storage"""
        try:
            # Get all items for change detection
            old_values = self.storage.get(None, area)
            
            # Clear storage
            self.storage.clear(area)
            
            # Emit changes
            changes = {
                key: {
                    'oldValue': value,
                    'newValue': None
                }
                for key, value in old_values.items()
            }
            if changes:
                self.storage_changed.emit(changes)
                
        except Exception as e:
            print(f"Error clearing storage: {e}")
    
    def get_bytes_in_use(self, keys: Optional[List[str]] = None, area: str = 'local') -> int:
        """Get the amount of storage space used"""
        try:
            quota = self.storage.get_quota()
            return quota['usage'].get(area, 0)
        except Exception as e:
            print(f"Error getting storage usage: {e}")
            return 0

class WebRequestAPI(BaseAPI):
    """Implementation of the chrome.webRequest.* API"""
    
    def addListener(self, event_name: str, callback: Callable, filter_dict: Dict[str, Any]):
        """Add a web request event listener"""
        # TODO: Implement request filtering and callbacks
        pass

class ContextMenuAPI(BaseAPI):
    """Implementation of the chrome.contextMenus.* API"""
    
    def create(self, properties: Dict[str, Any]) -> int:
        """Create a new context menu item"""
        # TODO: Implement context menu creation
        pass
    
    def remove(self, menu_item_id: int):
        """Remove a context menu item"""
        # TODO: Implement context menu removal
        pass 