# Development Guide

## Setup Development Environment

1. **Prerequisites**
   - Python 3.12+
   - Poetry for dependency management
   - Qt development tools

2. **Installation**
   ```bash
   git clone https://github.com/yourusername/sledge.git
   cd sledge
   poetry install
   ```

3. **Run Development Version**
   ```bash
   poetry run sledge
   ```

## Project Structure

### Core Modules

1. **Browser Core** (`browser/core.py`)
   - Main browser window
   - Profile management
   - Settings handling

2. **Tab System** (`browser/tabs/`)
   - Tab management
   - Group handling
   - State preservation

3. **Security** (`browser/security/`)
   - Request interception
   - Security settings
   - Fonce integration (planned)

4. **UI Components** (`browser/ui/`)
   - Custom widgets
   - Dialogs
   - Theme management

## Development Guidelines

### Code Style
- Follow PEP 8
- Use type hints
- Document all public methods
- Keep methods focused and small

### Security Development
1. **Request Interceptor**
   - Test all security headers
   - Verify CORS handling
   - Check blocked schemes/ports

2. **Security Panel**
   - Test all toggles
   - Verify settings persistence
   - Check developer mode

3. **Defense Module**
   - Keep Fonce integration modular
   - Test event handling
   - Document security events

### Testing

1. **Manual Testing**
   - Security features
   - Tab management
   - UI responsiveness

2. **Future Automated Tests**
   ```python
   def test_security_headers():
       # Test security header injection
       pass

   def test_cors_policy():
       # Test CORS handling
       pass

   def test_tab_management():
       # Test tab operations
       pass
   ```

## Common Tasks

### Adding New Features

1. **Plan**
   - Document requirements
   - Consider security implications
   - Design UI if needed

2. **Implement**
   - Write modular code
   - Add security checks
   - Update documentation

3. **Test**
   - Manual testing
   - Security verification
   - UI/UX review

### Debugging

1. **Security Issues**
   - Check console logs
   - Review request headers
   - Test in developer mode

2. **UI Issues**
   - Use Qt Developer tools
   - Check widget hierarchy
   - Verify styles

## Future Development

### Planned Features

1. **Security**
   - Full Fonce integration
   - Enhanced monitoring
   - Certificate management

2. **UI/UX**
   - Improved tab groups
   - Better dark mode
   - Custom themes

3. **Performance**
   - Tab suspension
   - Memory optimization
   - Startup improvements 