from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
import time
import hashlib

class VideoPlayer(QWidget):
    """A dedicated video player component that handles various video formats and error cases"""
    
    error_occurred = pyqtSignal(str)  # Signal for error reporting
    playback_started = pyqtSignal()
    playback_ended = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_web_view()
        
    def init_ui(self):
        """Initialize the UI components"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)  # Remove spacing
        
        # Create container widget with dark background
        self.container = QWidget()
        self.container.setStyleSheet("background: #1a1a1a;")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Web view for video playback
        self.web_view = QWebEngineView(self)
        self.web_view.setStyleSheet("background: #1a1a1a;")
        container_layout.addWidget(self.web_view)
        
        # Loading indicator
        self.loading_bar = QProgressBar(self)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #2e3440;
                height: 2px;
            }
            QProgressBar::chunk {
                background: #88c0d0;
            }
        """)
        self.loading_bar.hide()
        container_layout.addWidget(self.loading_bar)
        
        # Error display
        self.error_label = QLabel(self)
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("""
            QLabel {
                color: #bf616a;
                background: #2e3440;
                padding: 8px;
                border-radius: 4px;
                margin: 8px;
            }
        """)
        self.error_label.hide()
        container_layout.addWidget(self.error_label)
        
        self.layout.addWidget(self.container)
        
    def setup_web_view(self):
        """Configure the web view with video-specific settings"""
        # Create dedicated profile for video playback
        self.profile = QWebEngineProfile(self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        
        # Create page with video-optimized settings
        self.page = QWebEnginePage(self.profile, self.web_view)
        settings = self.page.settings()
        
        # Essential settings for HTML5 video and JavaScript
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        
        # Media settings
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)  # Required for some video sources
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.SpatialNavigationEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        
        # Set default codec support
        self.profile.setHttpAcceptLanguage("en-US,en;q=0.9")
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Set up page and connect signals
        self.web_view.setPage(self.page)
        
        # Override the console message handler
        def handle_js_console(level, message, line, source_id):
            self._handle_console_message(level, message, line, source_id)
        self.page.javaScriptConsoleMessage = handle_js_console
        
        # Inject video handling script
        self.inject_video_handler()
        
    def _handle_console_message(self, level, message, line, source):
        """Handle JavaScript console messages"""
        print(f"JS [{level}] {message} (line {line})")  # Debug logging
        if "ERROR" in message and "MEDIA_ERR" in message:
            self.error_label.setText(f"Video Error: {message}")
            self.error_label.show()
            print(f"Video Error: {message}")  # Debug logging
        
    def inject_video_handler(self):
        """Inject JavaScript to handle video playback and errors"""
        js = """
        (function() {
            // Check for video format support
            function checkVideoSupport() {
                const testVideo = document.createElement('video');
                return {
                    mp4: testVideo.canPlayType('video/mp4; codecs="avc1.42E01E, mp4a.40.2"'),
                    webm: testVideo.canPlayType('video/webm; codecs="vp8, vorbis"'),
                    hls: testVideo.canPlayType('application/vnd.apple.mpegurl'),
                    dash: testVideo.canPlayType('application/dash+xml')
                };
            }

            // Wait for VideoJS to be available
            function waitForVideoJS(callback, maxAttempts = 10) {
                let attempts = 0;
                const check = () => {
                    attempts++;
                    if (window.videojs) {
                        callback();
                    } else if (attempts < maxAttempts) {
                        setTimeout(check, 500);
                    }
                };
                check();
            }
            
            // Initialize VideoJS with proper configuration
            waitForVideoJS(() => {
                // Configure VideoJS defaults
                videojs.options.techOrder = ['html5'];
                videojs.options.html5 = {
                    nativeTextTracks: true,
                    nativeAudioTracks: true,
                    nativeVideoTracks: true,
                    hls: {
                        overrideNative: !checkVideoSupport().hls,
                        enableLowInitialPlaylist: true,
                        smoothQualityChange: true,
                        allowSeeksWithinUnsafeLiveWindow: true,
                        handlePartialData: true
                    }
                };
                
                // Initialize all video-js players
                document.querySelectorAll('.video-js').forEach(player => {
                    if (!player.player) {
                        const vjsPlayer = videojs(player, {
                            controls: true,
                            autoplay: false,
                            preload: 'auto',
                            responsive: true,
                            fluid: true,
                            playbackRates: [0.5, 1, 1.25, 1.5, 2],
                            html5: {
                                vhs: {
                                    overrideNative: !checkVideoSupport().hls
                                }
                            }
                        });
                        
                        // Add error handling
                        vjsPlayer.on('error', function() {
                            const error = vjsPlayer.error();
                            console.log('❌ VideoJS error:', error.code, error.message);
                            
                            // Log request details
                            fetch('{url}', {{
                                method: 'HEAD',
                                headers: {{
                                    'Accept': '*/*',
                                    'Accept-Language': 'en-US,en;q=0.9',
                                    'Origin': 'https://embed.watchanimesub.net',
                                    'Referer': 'https://embed.watchanimesub.net/',
                                    'Range': 'bytes=0-'
                                }}
                            }}).then(function(response) {{
                                console.log('🎥 HEAD response:', {{
                                    ok: response.ok,
                                    status: response.status,
                                    statusText: response.statusText,
                                    headers: Object.fromEntries([...response.headers])
                                }});
                            }}).catch(function(error) {{
                                console.log('❌ HEAD request error:', error);
                            }});
                            
                            console.log('❌ VideoJS error, trying native player');
                            vjsPlayer.dispose();
                            var nativePlayer = document.getElementById('native-player');
                            nativePlayer.style.display = 'block';
                            
                            // Try to load the video directly
                            fetch('{url}', {{
                                method: 'GET',
                                headers: {{
                                    'Accept': '*/*',
                                    'Accept-Language': 'en-US,en;q=0.9',
                                    'Origin': 'https://embed.watchanimesub.net',
                                    'Referer': 'https://embed.watchanimesub.net/',
                                    'Range': 'bytes=0-'
                                }}
                            }}).then(function(response) {{
                                console.log('🎥 GET response:', {{
                                    ok: response.ok,
                                    status: response.status,
                                    statusText: response.statusText,
                                    headers: Object.fromEntries([...response.headers])
                                }});
                                if (response.ok) {{
                                    nativePlayer.play().catch(function(error) {{
                                        console.log('❌ Native player error:', error);
                                        document.querySelector('.error-message').style.display = 'block';
                                    }});
                                }} else {{
                                    console.log('❌ Network error:', response.status, response.statusText);
                                    document.querySelector('.error-message').style.display = 'block';
                                }}
                            }}).catch(function(error) {{
                                console.log('❌ Fetch error:', error);
                                document.querySelector('.error-message').style.display = 'block';
                            }});
                        });
                    }
                });
            });
            
            // Handle native video elements
            document.querySelectorAll('video').forEach(video => {
                if (!video.hasAttribute('data-handled')) {
                    video.setAttribute('data-handled', 'true');
                    video.setAttribute('playsinline', '');
                    video.setAttribute('webkit-playsinline', '');
                    video.setAttribute('crossorigin', 'anonymous');
                    
                    // Add all possible source types
                    const originalSrc = video.src;
                    if (originalSrc) {
                        video.removeAttribute('src');
                        const support = checkVideoSupport();
                        
                        // Add HLS source
                        if (support.hls) {
                            const hlsSource = document.createElement('source');
                            hlsSource.src = originalSrc.replace(/\.(mp4|webm)/, '.m3u8');
                            hlsSource.type = 'application/vnd.apple.mpegurl';
                            video.appendChild(hlsSource);
                        }
                        
                        // Add MP4 source
                        if (support.mp4) {
                            const mp4Source = document.createElement('source');
                            mp4Source.src = originalSrc.replace(/\.(m3u8|webm)/, '.mp4');
                            mp4Source.type = 'video/mp4';
                            video.appendChild(mp4Source);
                        }
                        
                        // Add WebM source
                        if (support.webm) {
                            const webmSource = document.createElement('source');
                            webmSource.src = originalSrc.replace(/\.(mp4|m3u8)/, '.webm');
                            webmSource.type = 'video/webm';
                            video.appendChild(webmSource);
                        }
                    }
                    
                    // Add error recovery
                    video.addEventListener('error', (e) => {
                        const error = e.target.error;
                        console.log('Video error:', error.code, error.message);
                        
                        // Try next source if available
                        const sources = Array.from(video.getElementsByTagName('source'));
                        const currentSource = sources.find(s => s.src === video.currentSrc);
                        const nextSource = sources[sources.indexOf(currentSource) + 1];
                        
                        if (nextSource) {
                            video.src = nextSource.src;
                            video.load();
                            video.play();
                        }
                    });
                    
                    // Monitor playback events
                    video.addEventListener('playing', () => {
                        window.qt.notify('playback_started');
                    });
                    
                    video.addEventListener('ended', () => {
                        window.qt.notify('playback_ended');
                    });
                }
            });
            
            // Watch for dynamic content
            new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) {  // Element node
                            if (node.matches('video, .video-js')) {
                                initializeVideo(node);
                            }
                        }
                    });
                });
            }).observe(document.body, {
                childList: true,
                subtree: true
            });
        })();
        """
        self.page.runJavaScript(js)
        
    def load_video(self, url):
        """Load a video from the given URL"""
        print(f"🎥 [VIDEO PLAYER] Loading video URL: {url}")  # Debug log
        self.error_label.hide()
        self.loading_bar.show()
        self.loading_bar.setValue(0)
        
        # Extract video ID and quality if present
        video_id = None
        quality = "1080p"
        if "?" in url:
            base_url = url.split("?")[0]
            params = url.split("?")[1].split("&")
            for param in params:
                if "evid=" in param:
                    video_id = param.split("=")[1]
                elif "quality=" in param:
                    quality = param.split("=")[1]
        
        # If we have a video ID, construct the direct CDN URL
        if video_id:
            current_time = int(time.time())
            hash_input = f"{video_id}{current_time}watchanimesub".encode('utf-8')
            hash_value = hashlib.md5(hash_input).hexdigest()
            url = f"https://cdn.watchanimesub.net/getvid?evid={video_id}&quality={quality}&t={current_time}&h={hash_value}&embed=neptun"
            print(f"🎥 [VIDEO PLAYER] Constructed CDN URL: {url}")
            print(f"🎥 [VIDEO PLAYER] Hash input: {hash_input}")
            print(f"🎥 [VIDEO PLAYER] Generated hash: {hash_value}")
        
        # Create video element with proper setup
        html = f"""
        <!DOCTYPE html>
        <html style="background: #1a1a1a;">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                    background: #1a1a1a !important;
                }}
                html, body {{
                    width: 100%;
                    height: 100vh;
                    background: #1a1a1a !important;
                    color: #d8dee9;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                }}
                #video-container {{
                    flex: 1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: #1a1a1a !important;
                    position: relative;
                    min-height: 0;
                    width: 100%;
                    height: 100%;
                }}
                #loading-container {{
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: #1a1a1a !important;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 2;
                }}
                .loading-message {{
                    color: #88c0d0;
                    text-align: center;
                    background: rgba(46, 52, 64, 0.9);
                    padding: 1rem 2rem;
                    border-radius: 4px;
                }}
                .error-message {{
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: rgba(46, 52, 64, 0.9);
                    color: #bf616a;
                    padding: 1rem 2rem;
                    border-radius: 4px;
                    text-align: center;
                    z-index: 1000;
                    display: none;
                    border: 1px solid #bf616a;
                }}
                #native-player {{
                    width: 100%;
                    height: 100%;
                    background: #1a1a1a !important;
                    display: none;
                }}
                #player {{
                    width: 100%;
                    height: 100%;
                    background: #1a1a1a !important;
                }}
                .video-js {{
                    width: 100% !important;
                    height: 100% !important;
                    background-color: #1a1a1a !important;
                }}
            </style>
            <link href="https://vjs.zencdn.net/8.3.0/video-js.css" rel="stylesheet" />
            <script src="https://vjs.zencdn.net/8.3.0/video.min.js"></script>
        </head>
        <body>
            <div id="video-container">
                <div id="loading-container">
                    <div class="loading-message">Loading video...</div>
                </div>
                <div class="error-message">Error loading video. Please try again.</div>
                
                <!-- Native video player as fallback -->
                <video id="native-player" controls playsinline crossorigin="anonymous">
                    <source src="{url}" type="video/mp4">
                    <source src="{url}" type="application/x-mpegURL">
                    <source src="{url}" type="video/webm">
                    <p style="color: #d8dee9;">
                        Your browser doesn't support HTML5 video
                    </p>
                </video>
                
                <!-- VideoJS player -->
                <video id="player" 
                       class="video-js vjs-default-skin vjs-big-play-centered"
                       controls 
                       preload="auto"
                       crossorigin="anonymous"
                       data-setup='{{"fluid": true, "playbackRates": [0.5, 1, 1.25, 1.5, 2]}}'>
                    <source src="{url}" type="video/mp4">
                    <source src="{url}" type="application/x-mpegURL">
                    <source src="{url}" type="video/webm">
                </video>
            </div>
            
            <script>
                // Initialize video player
                document.addEventListener('DOMContentLoaded', function() {{
                    console.log('🎥 Initializing video player...');
                    
                    // Ensure dark background
                    document.documentElement.style.background = '#1a1a1a';
                    document.body.style.background = '#1a1a1a';
                    
                    function initializePlayer() {{
                        if (typeof videojs === 'undefined') {{
                            console.log('❌ VideoJS not loaded, falling back to native player');
                            document.getElementById('native-player').style.display = 'block';
                            document.getElementById('loading-container').style.display = 'none';
                            return;
                        }}
                        
                        console.log('✅ VideoJS loaded, initializing player');
                        var player = videojs('player', {{
                            controls: true,
                            autoplay: false,
                            preload: 'auto',
                            fluid: true,
                            playbackRates: [0.5, 1, 1.25, 1.5, 2],
                            html5: {{
                                vhs: {{
                                    overrideNative: true,
                                    fastQualityChange: true,
                                    useDevicePixelRatio: true
                                }},
                                nativeVideoTracks: false,
                                nativeAudioTracks: false,
                                nativeTextTracks: false
                            }},
                            sources: [
                                {{ src: "{url}", type: "video/mp4" }},
                                {{ src: "{url}", type: "application/x-mpegURL" }},
                                {{ src: "{url}", type: "video/webm" }}
                            ]
                        }});
                        
                        player.ready(function() {{
                            console.log('🎥 Player ready');
                            document.getElementById('loading-container').style.display = 'none';
                            
                            // Add error handling
                            player.on('error', function() {{
                                const error = player.error();
                                console.log('❌ VideoJS error:', error.code, error.message);
                                
                                // Log request details
                                fetch('{url}', {{
                                    method: 'HEAD',
                                    headers: {{
                                        'Accept': '*/*',
                                        'Accept-Language': 'en-US,en;q=0.9',
                                        'Origin': 'https://embed.watchanimesub.net',
                                        'Referer': 'https://embed.watchanimesub.net/',
                                        'Range': 'bytes=0-'
                                    }}
                                }}).then(function(response) {{
                                    console.log('🎥 HEAD response:', {{
                                        ok: response.ok,
                                        status: response.status,
                                        statusText: response.statusText,
                                        headers: Object.fromEntries([...response.headers])
                                    }});
                                }}).catch(function(error) {{
                                    console.log('❌ HEAD request error:', error);
                                }});
                                
                                console.log('❌ VideoJS error, trying native player');
                                player.dispose();
                                var nativePlayer = document.getElementById('native-player');
                                nativePlayer.style.display = 'block';
                                
                                // Try to load the video directly
                                fetch('{url}', {{
                                    method: 'GET',
                                    headers: {{
                                        'Accept': '*/*',
                                        'Accept-Language': 'en-US,en;q=0.9',
                                        'Origin': 'https://embed.watchanimesub.net',
                                        'Referer': 'https://embed.watchanimesub.net/',
                                        'Range': 'bytes=0-'
                                    }}
                                }}).then(function(response) {{
                                    console.log('🎥 GET response:', {{
                                        ok: response.ok,
                                        status: response.status,
                                        statusText: response.statusText,
                                        headers: Object.fromEntries([...response.headers])
                                    }});
                                    if (response.ok) {{
                                        nativePlayer.play().catch(function(error) {{
                                            console.log('❌ Native player error:', error);
                                            document.querySelector('.error-message').style.display = 'block';
                                        }});
                                    }} else {{
                                        console.log('❌ Network error:', response.status, response.statusText);
                                        document.querySelector('.error-message').style.display = 'block';
                                    }}
                                }}).catch(function(error) {{
                                    console.log('❌ Fetch error:', error);
                                    document.querySelector('.error-message').style.display = 'block';
                                }});
                            }});
                            
                            // Add source error handling
                            player.on('sourceset', function() {{
                                console.log('🎥 Source set:', player.currentSource());
                            }});
                            
                            // Add quality switching
                            player.on('loadedmetadata', function() {{
                                console.log('🎥 Video metadata loaded');
                                if (player.qualityLevels && player.qualityLevels().length > 0) {{
                                    console.log('🎥 Available quality levels:', player.qualityLevels().length);
                                }}
                            }});
                        }});
                    }}
                    
                    // Try to initialize player with retry
                    let attempts = 0;
                    function tryInitialize() {{
                        if (typeof videojs !== 'undefined' || attempts >= 5) {{
                            initializePlayer();
                        }} else {{
                            attempts++;
                            setTimeout(tryInitialize, 1000);
                        }}
                    }}
                    tryInitialize();
                }});
            </script>
        </body>
        </html>
        """
        self.web_view.setHtml(html)
        
    def handle_error(self, error_msg):
        """Display error message"""
        self.error_label.setText(error_msg)
        self.error_label.show()
        self.loading_bar.hide()
        self.error_occurred.emit(error_msg)
        
    def play(self):
        """Start video playback"""
        self.page.runJavaScript("document.querySelector('video').play();")
        
    def pause(self):
        """Pause video playback"""
        self.page.runJavaScript("document.querySelector('video').pause();")
        
    def seek(self, seconds):
        """Seek to specific time in seconds"""
        self.page.runJavaScript(f"document.querySelector('video').currentTime = {seconds};")
        
    def set_volume(self, volume):
        """Set volume (0.0 to 1.0)"""
        self.page.runJavaScript(f"document.querySelector('video').volume = {volume};") 