import os
import json
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from .storage import StorageManager
from .background import BackgroundScriptManager
from .html_handler import ExtensionPopup, ExtensionOptions

class CRXParser:
    """Parser for Chrome extension files (.crx)"""
    
    MAGIC_NUMBERS = {
        'CRX2': b'Cr24',
        'CRX3': b'Cr24' + bytes([3, 0, 0, 0])
    }

    def __init__(self, crx_path: str):
        self.crx_path = crx_path
        self.version = None
        self.header_size = None
        self.public_key = None
        self.signature = None

    def parse(self) -> bytes:
        """Parse CRX file and return the ZIP content"""
        with open(self.crx_path, 'rb') as f:
            magic = f.read(4)
            if magic == self.MAGIC_NUMBERS['CRX2']:
                return self._parse_crx2(f)
            elif magic == self.MAGIC_NUMBERS['CRX3']:
                return self._parse_crx3(f)
            raise ValueError(f'Invalid CRX format: {magic}')

    def _parse_crx2(self, f) -> bytes:
        """Parse CRX2 format"""
        version = int.from_bytes(f.read(4), 'little')
        pubkey_len = int.from_bytes(f.read(4), 'little')
        sig_len = int.from_bytes(f.read(4), 'little')
        self.public_key = f.read(pubkey_len)
        self.signature = f.read(sig_len)
        return f.read()  # Return ZIP content

    def _parse_crx3(self, f) -> bytes:
        """Parse CRX3 format"""
        header_length = int.from_bytes(f.read(4), 'little')
        metadata = f.read(header_length)
        # TODO: Parse CRX3 metadata when needed
        return f.read()  # Return ZIP content

class ExtensionManager(QObject):
    """Manages Chrome extensions"""
    
    extension_installed = pyqtSignal(str)  # Emits extension ID
    extension_uninstalled = pyqtSignal(str)  # Emits extension ID
    extension_enabled = pyqtSignal(str)  # Emits extension ID
    extension_disabled = pyqtSignal(str)  # Emits extension ID

    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.extensions: Dict[str, dict] = {}
        self.extension_dir = Path.home() / '.sledge' / 'extensions'
        self.extension_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize managers
        self.storage_manager = StorageManager()
        self.background_manager = BackgroundScriptManager()
        
        # Track active popups and options pages
        self.active_popups: Dict[str, ExtensionPopup] = {}
        self.active_options: Dict[str, ExtensionOptions] = {}
        
        self._load_installed_extensions()

    def _load_installed_extensions(self):
        """Load all installed extensions"""
        for ext_dir in self.extension_dir.iterdir():
            if ext_dir.is_dir():
                manifest_path = ext_dir / 'manifest.json'
                if manifest_path.exists():
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                        ext_id = ext_dir.name
                        self.extensions[ext_id] = {
                            'manifest': manifest,
                            'path': ext_dir,
                            'enabled': True  # TODO: Load from settings
                        }
                        # Initialize storage
                        self.storage_manager.get_storage(ext_id)
                        
                        # Load background script if enabled
                        if self.extensions[ext_id]['enabled']:
                            self._load_background_script(ext_id)

    def install_extension(self, crx_path: str) -> str:
        """Install a Chrome extension from .crx file"""
        # Parse CRX file
        parser = CRXParser(crx_path)
        zip_content = parser.parse()

        # Create temp file and extract
        with open('temp.zip', 'wb') as f:
            f.write(zip_content)

        # Read manifest to get extension ID
        with zipfile.ZipFile('temp.zip') as z:
            manifest = json.loads(z.read('manifest.json').decode())
            ext_id = manifest.get('key', os.path.basename(crx_path))
            ext_dir = self.extension_dir / ext_id
            
            # Extract extension
            z.extractall(ext_dir)

        # Clean up
        os.remove('temp.zip')

        # Register extension
        self.extensions[ext_id] = {
            'manifest': manifest,
            'path': ext_dir,
            'enabled': True
        }
        
        # Initialize storage
        self.storage_manager.get_storage(ext_id)
        
        # Load background script
        self._load_background_script(ext_id)

        self.extension_installed.emit(ext_id)
        return ext_id

    def uninstall_extension(self, ext_id: str):
        """Uninstall an extension"""
        if ext_id in self.extensions:
            # Close any open windows
            self._close_extension_windows(ext_id)
            
            # Unload background script
            self.background_manager.unload_background_script(ext_id)
            
            # Clean up storage
            self.storage_manager.cleanup_storage(ext_id)
            
            # Remove extension files
            ext_path = self.extensions[ext_id]['path']
            import shutil
            shutil.rmtree(ext_path)
            
            # Remove from registry
            del self.extensions[ext_id]
            self.extension_uninstalled.emit(ext_id)

    def enable_extension(self, ext_id: str):
        """Enable an extension"""
        if ext_id in self.extensions:
            self.extensions[ext_id]['enabled'] = True
            self._load_background_script(ext_id)
            self.extension_enabled.emit(ext_id)

    def disable_extension(self, ext_id: str):
        """Disable an extension"""
        if ext_id in self.extensions:
            self.extensions[ext_id]['enabled'] = False
            self._close_extension_windows(ext_id)
            self.background_manager.unload_background_script(ext_id)
            self.extension_disabled.emit(ext_id)

    def get_extension_info(self, ext_id: str) -> Optional[dict]:
        """Get extension information"""
        return self.extensions.get(ext_id)

    def get_active_extensions(self) -> List[str]:
        """Get list of enabled extension IDs"""
        return [ext_id for ext_id, ext in self.extensions.items() 
                if ext['enabled']]
                
    def get_storage_usage(self) -> Dict[str, Dict[str, int]]:
        """Get storage usage for all extensions"""
        usage = {}
        for ext_id in self.extensions:
            storage = self.storage_manager.get_storage(ext_id)
            usage[ext_id] = storage.get_quota()
        return usage
    
    def show_popup(self, ext_id: str, anchor_widget=None):
        """Show extension popup"""
        if ext_id not in self.extensions or not self.extensions[ext_id]['enabled']:
            return
            
        # Close existing popup if any
        if ext_id in self.active_popups:
            self.active_popups[ext_id].close()
            
        # Create new popup
        manifest = self.extensions[ext_id]['manifest']
        runtime = self.browser.get_extension_runtime(ext_id)
        popup = ExtensionPopup(ext_id, manifest, runtime)
        
        # Position relative to anchor if provided
        if anchor_widget:
            pos = anchor_widget.mapToGlobal(anchor_widget.rect().bottomLeft())
            popup.move(pos)
            
        # Show and track popup
        popup.load_popup()
        popup.show()
        self.active_popups[ext_id] = popup
    
    def show_options(self, ext_id: str):
        """Show extension options page"""
        if ext_id not in self.extensions or not self.extensions[ext_id]['enabled']:
            return
            
        # Show existing options if already open
        if ext_id in self.active_options:
            self.active_options[ext_id].raise_()
            self.active_options[ext_id].activateWindow()
            return
            
        # Create new options page
        manifest = self.extensions[ext_id]['manifest']
        runtime = self.browser.get_extension_runtime(ext_id)
        options = ExtensionOptions(ext_id, manifest, runtime)
        
        # Show and track options page
        options.load_options()
        options.show()
        self.active_options[ext_id] = options
    
    def _load_background_script(self, ext_id: str):
        """Load background script for an extension"""
        if ext_id in self.extensions and self.extensions[ext_id]['enabled']:
            manifest = self.extensions[ext_id]['manifest']
            runtime = self.browser.get_extension_runtime(ext_id)
            self.background_manager.load_background_script(ext_id, manifest, runtime)
    
    def _close_extension_windows(self, ext_id: str):
        """Close all windows for an extension"""
        # Close popup if open
        if ext_id in self.active_popups:
            self.active_popups[ext_id].close()
            del self.active_popups[ext_id]
            
        # Close options if open
        if ext_id in self.active_options:
            self.active_options[ext_id].close()
            del self.active_options[ext_id]
    
    def cleanup(self):
        """Clean up all extension resources"""
        # Close all windows
        for ext_id in list(self.active_popups.keys()):
            self._close_extension_windows(ext_id)
            
        # Clean up background scripts
        self.background_manager.cleanup() 