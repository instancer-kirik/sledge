# Sledge Browser Roadmap

## 1. Core Features (Current Phase)

### Style System (✓ Completed)
- [x] Dark mode support
- [x] Custom style injection
- [x] Site-specific overrides
- [x] Dynamic content handling
- [x] Font and readability controls
- [x] Mutation observer for dynamic sites

### Tab Management (Partially Complete)
- [x] Basic tab groups
- [x] Tab navigation
- [x] Tab state management
- [ ] Tab suspension for inactive tabs
- [ ] Memory usage optimization
- [ ] Visual tab grouping improvements

### Security Features (In Progress)
- [x] CORS policy enforcement
- [x] Mixed content blocking
- [x] Dangerous port/scheme blocking
- [x] Dev mode warnings
- [ ] Certificate management
- [ ] Advanced tracking protection

## 2. Extension System (High Priority)

### Extension API
- [ ] WebExtensions API compatibility layer
- [ ] Support for Chrome extensions (.crx)
- [ ] Extension sandbox environment
- [ ] Extension permissions system

#### API Endpoints to Implement
```javascript
// Core Extension APIs
browser.tabs.*          // Tab management
browser.windows.*       // Window management
browser.runtime.*       // Extension lifecycle
browser.storage.*       // Extension storage
browser.webRequest.*    // Request interception
browser.contextMenus.*  // Context menu items
```

### Extension Security
- [ ] Isolated extension processes
- [ ] Permission-based access control
- [ ] Resource usage monitoring
- [ ] Extension signature verification

### Extension Management
- [ ] Extension installation UI
- [ ] Extension settings panel
- [ ] Extension updates system
- [ ] Extension store integration

## 3. Performance Improvements

### Resource Management (High Priority)
- [ ] Process-per-site architecture
- [ ] Intelligent cache management
- [ ] Network resource prioritization
- [ ] Service worker support

### Memory Optimization
- [ ] Background tab throttling
- [ ] Tab state serialization
- [ ] Resource cleanup
- [ ] Memory leak prevention

## 4. User Interface Enhancements

### UI Customization (In Progress)
- [x] Style adjustment panel
- [x] Dark/Light mode switching
- [ ] Custom theme engine
- [ ] Gesture navigation
- [ ] Custom keyboard shortcuts

### Navigation Features
- [x] Enhanced navigation buttons
- [x] Keyboard shortcuts
- [x] Tab search
- [ ] History management improvements
- [ ] Bookmark enhancements

## 5. Developer Tools

### Enhanced DevTools (Medium Priority)
- [x] Basic developer tools
- [ ] Custom DevTools panels
- [ ] Network request inspector
- [ ] Security audit tools
- [ ] Performance profiling

### Development Mode
- [x] Developer mode toggle
- [ ] Advanced debugging tools
- [ ] Extension development tools
- [ ] Security testing tools
- [ ] Network simulation

## 6. Privacy Features

### Enhanced Privacy (High Priority)
- [x] Basic tracking protection
- [ ] Advanced fingerprint resistance
- [ ] Container tabs
- [ ] Privacy reports
- [ ] Enhanced cookie controls

### Data Management
- [x] Download management
- [x] Basic bookmark system
- [ ] Site data manager
- [ ] Privacy-focused sync
- [ ] Secure data storage

## Implementation Priority

### Phase 1 (Current)
1. ✓ Core style system
2. ✓ Basic security features
3. → Extension API foundations
4. → Performance optimization

### Phase 2 (Next)
1. Extension management UI
2. Advanced privacy features
3. DevTools enhancements
4. UI customization improvements

### Phase 3 (Future)
1. Container tabs
2. Advanced security features
3. Custom theme engine
4. Sync system

## Known Issues to Address
1. Process list refresh implementation
2. System tray integration
3. Compromise reporting system
4. Platform-specific features
5. Memory optimization

## Contributing

### Development Guidelines
1. Write tests for new features
2. Document API changes
3. Follow security best practices
4. Maintain performance standards

### Testing Requirements
- Unit tests for new features
- Extension compatibility tests
- Security validation
- Performance benchmarks
- Cross-platform testing 