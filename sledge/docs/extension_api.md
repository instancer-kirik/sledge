# Sledge Browser Extension API

## Overview

The Sledge Browser Extension API aims to provide compatibility with both Chrome and Firefox WebExtensions, allowing developers to port existing extensions and create new ones.

## API Implementation

### Core APIs

```python
class ExtensionAPI:
    """Base class for extension API implementation"""
    
    def __init__(self):
        self.tabs = TabAPI()
        self.windows = WindowAPI()
        self.runtime = RuntimeAPI()
        self.storage = StorageAPI()
        self.webRequest = WebRequestAPI()
        self.contextMenus = ContextMenuAPI()
```

### Supported Interfaces

#### 1. Tabs API
```javascript
browser.tabs.query(queryInfo)
browser.tabs.create(createProperties)
browser.tabs.update(tabId, updateProperties)
browser.tabs.remove(tabIds)
browser.tabs.sendMessage(tabId, message)
```

#### 2. Windows API
```javascript
browser.windows.create(createData)
browser.windows.get(windowId)
browser.windows.getAll(getInfo)
browser.windows.update(windowId, updateInfo)
```

#### 3. Runtime API
```javascript
browser.runtime.sendMessage(message)
browser.runtime.connect(extensionId)
browser.runtime.getManifest()
browser.runtime.onMessage.addListener(callback)
```

#### 4. Storage API
```javascript
browser.storage.local.get(keys)
browser.storage.local.set(items)
browser.storage.local.remove(keys)
browser.storage.local.clear()
```

## Extension Security

### Sandbox Implementation
```python
class ExtensionSandbox:
    """Isolated environment for extension execution"""
    
    def __init__(self, extension_id):
        self.id = extension_id
        self.permissions = []
        self.resources = ResourceMonitor()
```

### Permission System
```json
{
  "permissions": [
    "tabs",
    "storage",
    "webRequest",
    "<all_urls>"
  ],
  "optional_permissions": [
    "bookmarks",
    "history"
  ]
}
```

## Extension Development

### Creating an Extension

1. **Manifest File**
```json
{
  "manifest_version": 2,
  "name": "My Extension",
  "version": "1.0",
  "description": "Extension description",
  "permissions": ["tabs"],
  "background": {
    "scripts": ["background.js"]
  }
}
```

2. **Background Script**
```javascript
browser.tabs.onCreated.addListener((tab) => {
  console.log('New tab created:', tab.id);
});
```

### Testing Extensions

```python
def test_extension():
    # Load extension
    ext = Extension.load('path/to/extension')
    
    # Test API calls
    tabs = ext.api.tabs.query({})
    assert len(tabs) > 0
```

## Extension Management

### Installation Process
1. Verify extension package
2. Check permissions
3. Create sandbox
4. Load manifest
5. Initialize APIs

### Update Mechanism
1. Check for updates
2. Download new version
3. Verify package
4. Hot-reload if possible

## Best Practices

### Security
1. Always use permission system
2. Validate all extension inputs
3. Monitor resource usage
4. Implement CSP

### Performance
1. Use event pages over background pages
2. Minimize API calls
3. Cache data when possible
4. Use appropriate storage APIs

## Future Enhancements

### Planned Features
1. Native messaging support
2. Enhanced developer tools
3. Extension sync
4. Performance profiling

### API Extensions
1. Custom API endpoints
2. Enhanced security APIs
3. Sledge-specific features
4. Performance APIs 