from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor

class RequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.blocked_schemes = {'file', 'ftp', 'data', 'javascript'}
        self.blocked_ports = {21, 22, 23, 25, 465, 587}  # Common dangerous ports
        
    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        scheme = info.requestUrl().scheme()
        port = info.requestUrl().port()
        
        # Block dangerous schemes if enabled
        if self.browser.settings.get('security', 'block_dangerous_schemes'):
            if scheme in self.blocked_schemes:
                info.block(True)
                return
        
        # Block dangerous ports if enabled
        if self.browser.settings.get('security', 'block_dangerous_ports'):
            if port in self.blocked_ports:
                info.block(True)
                return
        
        # Add security headers
        info.setHttpHeader(b"Content-Security-Policy", 
            b"default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: *; "
            b"frame-ancestors 'self'; "
            b"form-action 'self'; "
            b"upgrade-insecure-requests; "
            b"block-all-mixed-content")
        
        # Add DNT header if enabled
        if self.browser.settings.get('privacy', 'do_not_track'):
            info.setHttpHeader(b"DNT", b"1")
            
        info.setHttpHeader(b"X-Content-Type-Options", b"nosniff")
        info.setHttpHeader(b"X-Frame-Options", b"SAMEORIGIN")
        info.setHttpHeader(b"Referrer-Policy", b"strict-origin-when-cross-origin")
        info.setHttpHeader(b"Permissions-Policy", 
            b"geolocation=(), microphone=(), camera=(), payment=(), "
            b"usb=(), serial=(), bluetooth=(), midi=()")
            
        # Handle CORS based on settings
        if self.browser.settings.get('security', 'strict_cors') and not self.browser.settings.get('security', 'dev_mode'):
            # Strict CORS mode
            info.setHttpHeader(b"Access-Control-Allow-Origin", b"null")
            info.setHttpHeader(b"Cross-Origin-Opener-Policy", b"same-origin")
            info.setHttpHeader(b"Cross-Origin-Embedder-Policy", b"require-corp")
        else:
            # Development mode - relaxed CORS
            origin = info.firstPartyUrl().toString().split('://')[1].split('/')[0] if '://' in info.firstPartyUrl().toString() else '*'
            info.setHttpHeader(b"Access-Control-Allow-Origin", b"*")
            info.setHttpHeader(b"Access-Control-Allow-Methods", b"GET, POST, OPTIONS, PUT, DELETE, HEAD")
            info.setHttpHeader(b"Access-Control-Allow-Headers", b"*")
            info.setHttpHeader(b"Access-Control-Allow-Credentials", b"true")
        
        # Check for suspicious patterns
        if self._is_suspicious_request(url):
            # Log suspicious request
            print(f"Suspicious request detected: {url}")
            # Could block or warn here
            
    def _is_suspicious_request(self, url):
        """Check for potentially suspicious request patterns"""
        suspicious_patterns = [
            'eval=', 'exec=', 'system=',  # Command injection
            '../', '..%2F',  # Path traversal
            '<script', '%3Cscript',  # XSS attempts
            'union+select', 'union%20select'  # SQL injection
        ]
        return any(pattern in url.lower() for pattern in suspicious_patterns) 