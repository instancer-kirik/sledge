from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt6.QtCore import QUrl
import re
import time

class RequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.blocked_schemes = {'file', 'ftp', 'data', 'javascript'}
        self.blocked_ports = {21, 22, 23, 25, 465, 587}  # Common dangerous ports
        
        # Extended WCO and video domains
        self.video_domains = {
            'wcostream.tv', 'www.wcostream.tv',
            'wcofun.net', 'www.wcofun.net',
            'wco.tv', 'www.wco.tv',
            'embed.wcostream.tv',
            'embed.wcofun.net',
            'embed.wco.tv',
            'vidstreaming.io',
            'gogocdn.net',
            'gogo-cdn.com',
            'streamani.net',
            'fonts.gstatic.com',
            'google.com',
            'gstatic.com',
            'googleapis.com',
            'cloudflare.com',
            'jsdelivr.net',
            'cdnjs.cloudflare.com'
        }
        
        # Extended video patterns
        self.video_patterns = {
            '.mp4', '.m3u8', '.ts', '.webm', '.mpd', '.m4s',
            'getvid', 'manifest', 'playlist',
            'video', 'embed', 'stream', 'source',
            'getvidlist', 'getm3u8', 'getVideo',
            'load.php', 'video.php', 'ajax.php',
            'recaptcha', 'player', 'videojs'
        }
        
    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        host = info.requestUrl().host()
        
        # Debug print for all requests
        print(f"🌐 [REQUEST] {url}")
        
        # Set permissive headers for all requests
        self._set_permissive_headers(info)
        
        # Special handling for WCO domains
        if any(wco in host for wco in ['wcostream', 'wcofun', 'wco.tv']):
            print(f"🎬 [WCO] Handling WCO request: {url}")
            self._handle_wco_request(info, url)
            return
            
        # Handle video and related requests
        if (any(domain in url for domain in self.video_domains) or 
            any(pattern in url.lower() for pattern in self.video_patterns)):
            print(f"🎥 [VIDEO] Handling video request: {url}")
            self._handle_video_request(info, url)
            return
            
        # Default handling for other requests
        self._handle_default_request(info)

    def _set_permissive_headers(self, info):
        """Set permissive headers for all requests"""
        # Remove restrictive headers
        info.setHttpHeader(b"Content-Security-Policy", b"")
        info.setHttpHeader(b"X-Frame-Options", b"")
        info.setHttpHeader(b"X-Content-Type-Options", b"")
        info.setHttpHeader(b"Strict-Transport-Security", b"")
        info.setHttpHeader(b"Permissions-Policy", b"")
        
        # Set permissive CORS headers
        info.setHttpHeader(b"Access-Control-Allow-Origin", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Methods", b"GET, POST, OPTIONS, HEAD")
        info.setHttpHeader(b"Access-Control-Allow-Headers", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Credentials", b"true")
        info.setHttpHeader(b"Access-Control-Expose-Headers", b"*")
        info.setHttpHeader(b"Cross-Origin-Resource-Policy", b"cross-origin")
        info.setHttpHeader(b"Cross-Origin-Embedder-Policy", b"credentialless")
        info.setHttpHeader(b"Cross-Origin-Opener-Policy", b"same-origin")

    def _handle_wco_request(self, info, url):
        """Special handling for WCO requests"""
        print(f"🎬 [WCO] Setting WCO headers for: {url}")
        
        # Base headers for WCO
        headers = {
            b"User-Agent": b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            b"Accept": b"*/*",
            b"Accept-Language": b"en-US,en;q=0.9",
            b"Accept-Encoding": b"gzip, deflate, br",
            b"Origin": b"https://www.wcostream.tv",
            b"Connection": b"keep-alive",
            b"Referer": b"https://www.wcostream.tv/",
            b"Range": b"bytes=0-",
            b"Cache-Control": b"no-cache",
            b"Sec-Fetch-Dest": b"empty",
            b"Sec-Fetch-Mode": b"cors",
            b"Sec-Fetch-Site": b"same-origin"
        }
        
        # Set all headers
        for key, value in headers.items():
            info.setHttpHeader(key, value)
        
        # Handle video quality selection
        if any(pattern in url.lower() for pattern in ['getvid', 'getVideo', 'load.php']):
            if '?' in url:
                base_url = url.split('?')[0]
                params = url.split('?')[1]
                # Clean up quality parameter
                params = re.sub(r'quality=[^&]*', '', params)
                params = params.rstrip('&') + '&quality=1080p'
                # Add timestamp to bypass cache
                params += f'&t={int(time.time())}'
                new_url = f"{base_url}?{params}"
                print(f"🎬 [WCO] Redirecting to: {new_url}")
                info.redirect(QUrl(new_url))

    def _handle_video_request(self, info, url):
        """Handle general video requests"""
        print(f"🎥 [VIDEO] Setting video headers for: {url}")
        
        # Set video-specific headers
        headers = {
            b"Accept": b"*/*",
            b"Accept-Language": b"en-US,en;q=0.9",
            b"Accept-Encoding": b"gzip, deflate, br",
            b"Range": b"bytes=0-",
            b"Connection": b"keep-alive",
            b"Origin": b"https://www.wcostream.tv",
            b"Referer": b"https://www.wcostream.tv/",
            b"User-Agent": b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            b"Sec-Fetch-Dest": b"video",
            b"Sec-Fetch-Mode": b"cors",
            b"Sec-Fetch-Site": b"cross-site"
        }
        
        # Set all headers
        for key, value in headers.items():
            info.setHttpHeader(key, value)
        
        # Add range support
        info.setHttpHeader(b"Accept-Ranges", b"bytes")
        
        # Handle m3u8 playlists
        if '.m3u8' in url.lower():
            info.setHttpHeader(b"Accept", b"application/vnd.apple.mpegurl")

    def _handle_default_request(self, info):
        """Handle non-video requests"""
        # Block dangerous schemes/ports if enabled
        if self.browser.settings.get('security', 'block_dangerous_schemes'):
            if info.requestUrl().scheme() in self.blocked_schemes:
                info.block(True)
                return
                
        if self.browser.settings.get('security', 'block_dangerous_ports'):
            if info.requestUrl().port() in self.blocked_ports:
                info.block(True)
                return

    def _add_security_headers(self, info):
        """Add security headers for non-video requests"""
        if self.browser.settings.get('privacy', 'do_not_track'):
            info.setHttpHeader(b"DNT", b"1")
            
        info.setHttpHeader(b"X-Content-Type-Options", b"nosniff")
        info.setHttpHeader(b"Referrer-Policy", b"strict-origin-when-cross-origin")
        
    def _handle_cors(self, info):
        """Handle CORS headers"""
        if self.browser.settings.get('security', 'strict_cors'):
            origin = info.firstPartyUrl().toString().split('://')[1].split('/')[0] if '://' in info.firstPartyUrl().toString() else '*'
            info.setHttpHeader(b"Access-Control-Allow-Origin", origin.encode())
        else:
            info.setHttpHeader(b"Access-Control-Allow-Origin", b"*")
            info.setHttpHeader(b"Access-Control-Allow-Methods", b"*")
            info.setHttpHeader(b"Access-Control-Allow-Headers", b"*")
        
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