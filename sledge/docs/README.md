# Sledge Browser Documentation

Sledge is a secure, modern web browser built with PyQt6 and QtWebEngine, featuring advanced tab management, security features, and future integration with Fonce security application.

## Project Structure

```
sledge/
├── browser/              # Main browser module
│   ├── components/      # Reusable browser components
│   ├── security/        # Security features and Fonce integration
│   │   ├── defense/    # Fonce security application integration
│   │   ├── interceptor.py  # Request interception and security headers
│   │   └── panel.py    # Security settings UI
│   ├── tabs/           # Tab management system
│   └── ui/             # User interface components
├── utils/              # Utility functions
└── icons/              # Browser icons and assets
```

## Core Components

### Browser Security

The browser implements multiple layers of security:

1. **Request Interception**
   - CORS policy management
   - Dangerous scheme/port blocking
   - Security headers injection
   - Mixed content blocking

2. **Security Panel**
   - Developer mode toggle
   - CORS policy settings
   - Content security settings
   - Port and scheme blocking

3. **Fonce Integration** (Planned)
   - Advanced security monitoring
   - Event handling system
   - Browser security policies

### Tab Management

Advanced tab management system featuring:
- Tab groups
- Memory management
- State preservation
- Ring menu navigation

### User Interface

Modern UI components including:
- Custom styled dialogs
- Theme support
- Bookmark management
- Download handling

## Configuration

Security settings are managed through the Settings dialog and stored using QSettings:
- Security mode (Normal/Developer)
- CORS policies
- Content security
- Privacy features

## Development

### Requirements
- Python 3.12+
- PyQt6
- QtWebEngine

### Setup
1. Install dependencies:
```bash
poetry install
```

2. Run the browser:
```bash
poetry run sledge
```

### Security Development

When working on security features:
1. Use the Security Panel for testing CORS and content security
2. Developer Mode can be enabled for testing cross-origin requests
3. Monitor the console for suspicious request logging

## Future Integration

The `defense` module is prepared for future integration with Fonce security application:
- Event monitoring
- Security policy enforcement
- Content security analysis 