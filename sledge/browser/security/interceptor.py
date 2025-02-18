from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt6.QtCore import QUrl
import re
import time
import hashlib

class RequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.blocked_schemes = {'file', 'ftp'}  # Removed data and javascript to allow media
        self.blocked_ports = {21, 22, 23, 25, 465, 587}  # Common dangerous ports
        
        # Extended WCO and video domains
        self.video_domains = {
            'wcostream.tv', 'www.wcostream.tv',
            'wcofun.net', 'www.wcofun.net',
            'wco.tv', 'www.wco.tv',
            'embed.wcostream.tv',
            'embed.wcofun.net',
            'embed.wco.tv',
            'cdn.watchanimesub.net',  # Added CDN domain
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
            'cdnjs.cloudflare.com',
            'ajax.googleapis.com',
            'vjs.zencdn.net',  # VideoJS CDN
            'player.vimeo.com',
            'fast.wistia.net',
            'bitmovin.com',
            'jwplayer.com'
        }
        
        # Extended video patterns
        self.video_patterns = {
            '.mp4', '.m3u8', '.ts', '.webm', '.mpd', '.m4s', '.mkv', '.avi', '.flv',
            'getvid', 'manifest', 'playlist', 'dash', 'segment', 'frag', 'chunk',
            'video', 'embed', 'stream', 'source', 'media', 'play', 'watch',
            'getvidlist', 'getm3u8', 'getVideo', 'getstream', 'getmanifest',
            'load.php', 'video.php', 'ajax.php', 'stream.php', 'embed.php',
            'recaptcha', 'player', 'videojs', 'jwplayer', 'bitmovin', 'vimeo'
        }
        
        self.video_urls = set()

    def interceptRequest(self, info):
        """Handle request interception"""
        url = info.requestUrl().toString()
        print(f"🌐 [REQUEST] Intercepting: {url}")
        
        # Set default CORS headers
        info.setHttpHeader(b"Access-Control-Allow-Origin", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Methods", b"GET, POST, OPTIONS")
        info.setHttpHeader(b"Access-Control-Allow-Headers", b"*")
        
        # Handle CDN video requests
        if 'cdn.watchanimesub.net' in url:
            print(f"🎥 [CDN] Processing CDN request: {url}")
            print(f"🎥 [CDN] Request method: {info.requestMethod()}")
            print(f"🎥 [CDN] First party URL: {info.firstPartyUrl().toString()}")
            
            # Set required headers for CDN
            headers = {
                b"User-Agent": b"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                b"Accept": b"video/webm,video/x-matroska,video/mp4,video/*;q=0.9,*/*;q=0.8",
                b"Accept-Language": b"en-US,en;q=0.9",
                b"Accept-Encoding": b"identity",
                b"Origin": b"https://embed.watchanimesub.net",
                b"Connection": b"keep-alive",
                b"Referer": b"https://embed.watchanimesub.net/",
                b"Sec-Fetch-Dest": b"video",
                b"Sec-Fetch-Mode": b"cors",
                b"Sec-Fetch-Site": b"cross-site",
                b"Range": b"bytes=0-",
                b"Access-Control-Allow-Origin": b"*",
                b"Access-Control-Allow-Methods": b"GET, POST, OPTIONS",
                b"Access-Control-Allow-Headers": b"*"
            }
            
            # Set all headers and log them
            for key, value in headers.items():
                info.setHttpHeader(key, value)
                print(f"🎥 [CDN] Setting header {key.decode()}: {value.decode()}")
            
            # Remove problematic headers
            remove_headers = [
                b"X-Frame-Options",
                b"Content-Security-Policy",
                b"Cross-Origin-Embedder-Policy",
                b"Cross-Origin-Opener-Policy",
                b"Cross-Origin-Resource-Policy"
            ]
            for header in remove_headers:
                info.setHttpHeader(header, b"")
                print(f"🎥 [CDN] Removing header: {header.decode()}")
            
            # Add timestamp and hash to URL if not present
            if 'getvid' in url:
                # Parse URL parameters
                base_url = url.split('?')[0]
                params = {}
                if '?' in url:
                    for param in url.split('?')[1].split('&'):
                        if '=' in param:
                            key, value = param.split('=')
                            params[key] = value
                            print(f"🎥 [CDN] Found parameter {key}: {value}")
                
                # Add or update timestamp
                current_time = int(time.time())
                params['t'] = str(current_time)
                print(f"🎥 [CDN] Using timestamp: {current_time}")
                
                # Add hash if we have evid
                if 'evid' in params:
                    video_id = params['evid']
                    timestamp = params['t']
                    hash_input = f"{video_id}{timestamp}watchanimesub".encode('utf-8')
                    hash_value = hashlib.md5(hash_input).hexdigest()
                    params['h'] = hash_value
                    print(f"🎥 [CDN] Generated hash for video {video_id}: {hash_value}")
                    print(f"🎥 [CDN] Hash input: {hash_input}")
                
                # Add embed parameter if not present
                if 'embed' not in params:
                    params['embed'] = 'neptun'
                
                # Reconstruct URL
                param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
                new_url = f"{base_url}?{param_str}"
                
                print(f"🎥 [CDN] Final URL: {new_url}")
                info.redirect(QUrl(new_url))
                self.video_urls.add(new_url)
                return
            
            # Store video URL
            print(f"🎥 [VIDEO URL] Found CDN video: {url}")
            self.video_urls.add(url)
            return
        
        # Set dark mode preference headers
        info.setHttpHeader(b"Sec-CH-Prefers-Color-Scheme", b"dark")
        info.setHttpHeader(b"Accept", b"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
        info.setHttpHeader(b"Accept-Language", b"en-US,en;q=0.9")
        
        # Set default security headers
        info.setHttpHeader(b"X-Content-Type-Options", b"nosniff")
        info.setHttpHeader(b"X-Frame-Options", b"SAMEORIGIN")
        info.setHttpHeader(b"X-XSS-Protection", b"1; mode=block")
        
        # Handle video source domains
        if any(domain in url for domain in [
            'cizgifilmlerizle.com',
            'watchanimesub.net',
            'wcofun.net',
            'fonts.gstatic.com'
        ]):
            # Add specific headers for video requests
            info.setHttpHeader(b"Origin", b"https://embed.watchanimesub.net")
            info.setHttpHeader(b"Referer", b"https://embed.watchanimesub.net/")
            info.setHttpHeader(b"Sec-Fetch-Site", b"cross-site")
            info.setHttpHeader(b"Sec-Fetch-Mode", b"cors")
            info.setHttpHeader(b"Sec-Fetch-Dest", b"empty")
            info.setHttpHeader(b"Accept", b"*/*")
            info.setHttpHeader(b"Accept-Language", b"en-US,en;q=0.9")
            info.setHttpHeader(b"Connection", b"keep-alive")
            info.setHttpHeader(b"Range", b"bytes=0-")
            
            # Remove problematic headers
            info.setHttpHeader(b"X-Frame-Options", b"")
            info.setHttpHeader(b"Content-Security-Policy", b"")
            info.setHttpHeader(b"Cross-Origin-Embedder-Policy", b"")
            info.setHttpHeader(b"Cross-Origin-Opener-Policy", b"")
            info.setHttpHeader(b"Cross-Origin-Resource-Policy", b"")
            
            # Store video URL if it matches patterns
            if any(pattern in url.lower() for pattern in ['.mp4', '.m3u8', '.ts', '.webm', 'getvid']):
                print(f"🎥 [VIDEO URL] Found video URL: {url}")
                self.video_urls.add(url)
        
        # Debug print for all requests
        print(f"🌐 [REQUEST] {url}")
        
        # Check if this is a video-related domain
        if any(domain in url for domain in self.video_domains):
            print(f"🎥 [VIDEO DOMAIN] Detected: {url}")
            
        # Check if this is a video-related pattern
        if any(pattern in url.lower() for pattern in self.video_patterns):
            print(f"🎥 [VIDEO PATTERN] Detected: {url}")
        
        # Handle WCO domains first
        if any(wco in url for wco in ['wcostream', 'wcofun', 'wco.tv']):
            print(f"🎬 [WCO] Processing WCO request: {url}")
            if 'embed' in url:
                print(f"🎬 [WCO] Found embed URL: {url}")
            if any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.ts', '.webm']):
                print(f"🎬 [WCO] Found direct video URL: {url}")
            self._handle_wco_request(info, url)
            return
            
        # Handle video and related requests
        if (any(domain in url for domain in self.video_domains) or 
            any(pattern in url.lower() for pattern in self.video_patterns)):
            print(f"🎥 [VIDEO] Processing video request: {url}")
            self._handle_video_request(info, url)
            return
            
        # Default handling for other requests
        self._handle_default_request(info)

    def _set_permissive_headers(self, info):
        """Set permissive headers for all requests"""
        # Remove restrictive headers
        info.setHttpHeader(b"Content-Security-Policy", b"default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; worker-src * 'unsafe-inline' 'unsafe-eval' data: blob:;")
        info.setHttpHeader(b"X-Frame-Options", b"ALLOWALL")
        info.setHttpHeader(b"X-Content-Type-Options", b"nosniff")
        
        # Set modern permissions policy
        info.setHttpHeader(b"Permissions-Policy", b"accelerometer=*, autoplay=*, camera=*, clipboard-read=*, clipboard-write=*, fullscreen=*, geolocation=*, gyroscope=*, magnetometer=*, microphone=*, payment=*, sync-xhr=*, usb=*, xr-spatial-tracking=*")
        
        # Set permissive CORS headers
        info.setHttpHeader(b"Access-Control-Allow-Origin", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Methods", b"GET, POST, OPTIONS, PUT, DELETE, HEAD")
        info.setHttpHeader(b"Access-Control-Allow-Headers", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Credentials", b"true")
        info.setHttpHeader(b"Access-Control-Expose-Headers", b"*")
        info.setHttpHeader(b"Access-Control-Max-Age", b"86400")
        
        # Set permissive security policies
        info.setHttpHeader(b"Cross-Origin-Resource-Policy", b"cross-origin")
        info.setHttpHeader(b"Cross-Origin-Embedder-Policy", b"unsafe-none")
        info.setHttpHeader(b"Cross-Origin-Opener-Policy", b"unsafe-none")
        
        # Set feature policies
        info.setHttpHeader(b"Feature-Policy", b"*")

    def _handle_wco_request(self, info, url):
        """Special handling for WCO requests"""
        print(f"🎬 [WCO] Setting WCO headers for: {url}")
        
        # Set minimal required headers
        info.setHttpHeader(b"Access-Control-Allow-Origin", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Methods", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Headers", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Credentials", b"true")
        
        # Remove ALL restrictive headers
        info.setHttpHeader(b"Content-Security-Policy", b"")
        info.setHttpHeader(b"X-Frame-Options", b"")
        info.setHttpHeader(b"Permissions-Policy", b"")
        info.setHttpHeader(b"Cross-Origin-Embedder-Policy", b"")
        info.setHttpHeader(b"Cross-Origin-Opener-Policy", b"")
        info.setHttpHeader(b"Cross-Origin-Resource-Policy", b"")
        
        # Set basic headers
        headers = {
            b"User-Agent": b"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            b"Accept": b"*/*",
            b"Accept-Language": b"en-US,en;q=0.9",
            b"Origin": b"https://www.wcofun.net",
            b"Referer": b"https://www.wcofun.net/",
            b"Sec-Fetch-Dest": b"empty",
            b"Sec-Fetch-Mode": b"cors",
            b"Sec-Fetch-Site": b"cross-site",
            b"Connection": b"keep-alive"
        }
        
        # Set headers
        for key, value in headers.items():
            info.setHttpHeader(key, value)
        
        # Handle video-js.php requests
        if 'video-js.php' in url:
            print(f"🎥 [VIDEO-JS] Processing video-js.php request: {url}")
            # Extract file parameter
            if 'file=' in url:
                file_param = re.search(r'file=([^&]+)', url).group(1)
                if '.flv' in file_param:
                    # Convert FLV path to direct CDN URL
                    video_id = re.search(r'pid=(\d+)', url)
                    if video_id:
                        pid = video_id.group(1)
                        quality = "1080p" if "fullhd=1" in url else "720p"
                        cdn_url = f"https://cdn.watchanimesub.net/getvid?evid={pid}&quality={quality}&t={int(time.time())}"
                        print(f"🎥 [VIDEO-JS] Redirecting to CDN URL: {cdn_url}")
                        info.redirect(QUrl(cdn_url))
                        self.video_urls.add(cdn_url)
                        return
            
        # Handle video requests
        if any(pattern in url.lower() for pattern in ['getvid', 'getVideo', 'load.php', '.mp4', '.m3u8', '.flv']):
            print(f"🎥 [VIDEO] Found video request: {url}")
            # Add video-specific headers
            info.setHttpHeader(b"Range", b"bytes=0-")
            info.setHttpHeader(b"Accept-Ranges", b"bytes")
            info.setHttpHeader(b"Accept", b"*/*")
            
            # Handle quality selection for video requests
            if '?' in url and any(p in url.lower() for p in ['getvid', 'getVideo', 'load.php']):
                base_url = url.split('?')[0]
                params = url.split('?')[1]
                
                # Extract video ID if present
                if 'evid=' in params:
                    print(f"🎥 [VIDEO] Found evid parameter in URL")
                    video_id = re.search(r'evid=([^&]+)', params).group(1)
                    # Construct direct video URL
                    if video_id:
                        new_url = f"https://cdn.watchanimesub.net/getvid?evid={video_id}&quality=1080p&t={int(time.time())}"
                        print(f"🎬 [WCO] Redirecting to direct video URL: {new_url}")
                        info.redirect(QUrl(new_url))
                        self.video_urls.add(new_url)
                        return
                
                # Clean up quality parameter
                params = re.sub(r'quality=[^&]*', '', params)
                params = params.rstrip('&') + '&quality=1080p'
                # Add timestamp to bypass cache
                params += f'&t={int(time.time())}'
                new_url = f"{base_url}?{params}"
                print(f"🎬 [WCO] Redirecting to: {new_url}")
                info.redirect(QUrl(new_url))
                
                # Store video URL
                print(f"🎥 [VIDEO URL] Storing: {new_url}")
                self.video_urls.add(new_url)
                return

            # Store direct video URLs
            print(f"🎥 [VIDEO URL] Storing direct: {url}")
            self.video_urls.add(url)
            
    def _handle_video_request(self, info, url):
        """Handle general video requests"""
        print(f"🎥 [VIDEO] Setting video headers for: {url}")
        
        # Set permissive CORS headers
        info.setHttpHeader(b"Access-Control-Allow-Origin", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Methods", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Headers", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Credentials", b"true")
        
        # Remove restrictive headers
        info.setHttpHeader(b"Content-Security-Policy", b"")
        info.setHttpHeader(b"X-Frame-Options", b"")
        info.setHttpHeader(b"Cross-Origin-Embedder-Policy", b"")
        info.setHttpHeader(b"Cross-Origin-Opener-Policy", b"")
        
        # Set video-specific headers
        headers = {
            b"Accept": b"*/*",
            b"Accept-Language": b"en-US,en;q=0.9",
            b"Accept-Encoding": b"gzip, deflate, br",
            b"Range": b"bytes=0-",
            b"Connection": b"keep-alive",
            b"Origin": b"https://www.wcofun.net",  # Use WCO origin
            b"Referer": b"https://www.wcofun.net/",  # Use WCO referer
            b"User-Agent": b"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            b"Sec-Fetch-Dest": b"video",
            b"Sec-Fetch-Mode": b"cors",
            b"Sec-Fetch-Site": b"cross-site"
        }
        
        # Set all headers
        for key, value in headers.items():
            info.setHttpHeader(key, value)
        
        # Add range support
        info.setHttpHeader(b"Accept-Ranges", b"bytes")
        
        # Handle different video formats with broader MIME type support
        if '.m3u8' in url.lower():
            print(f"🎥 [HLS] Found HLS stream: {url}")
            info.setHttpHeader(b"Accept", b"application/vnd.apple.mpegurl, application/x-mpegURL, application/x-mpegurl, */*")
        elif '.mpd' in url.lower():
            print(f"🎥 [DASH] Found DASH stream: {url}")
            info.setHttpHeader(b"Accept", b"application/dash+xml, video/mp4, */*")
        elif any(ext in url.lower() for ext in ['.mp4', '.webm', '.mkv', '.ts']):
            print(f"🎥 [DIRECT] Found direct video: {url}")
            info.setHttpHeader(b"Accept", b"video/*, application/x-mpegURL, */*")

        # Store video URL
        if 'getvid' in url or 'getVideo' in url or any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.webm']):
            print(f"🎥 [VIDEO URL] Storing: {url}")
            self.video_urls.add(url)

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
        url = info.requestUrl().toString()
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

    def get_video_url(self):
        """Get the most recent video URL"""
        url = next(iter(self.video_urls), None) if self.video_urls else None
        print(f"🎥 [VIDEO URL] Returning most recent: {url}")
        return url 