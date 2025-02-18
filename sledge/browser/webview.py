from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings, QWebEngineUrlRequestInterceptor
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, pyqtSignal
import re

class RequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Intercepts and modifies web requests"""
    
    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        
        # Set default CORS headers
        info.setHttpHeader(b"Access-Control-Allow-Origin", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Methods", b"GET, POST, OPTIONS")
        info.setHttpHeader(b"Access-Control-Allow-Headers", b"*")
        
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
            
            # Remove problematic headers
            info.setHttpHeader(b"X-Frame-Options", b"")
            info.setHttpHeader(b"Content-Security-Policy", b"")
            
        # Handle video source URLs
        if 'getvid' in url:
            # Convert URL parameters to a format the server expects
            if '?' in url:
                base_url = url.split('?')[0]
                params = url.split('?')[1]
                # Clean up the parameters
                params = re.sub(r'([^=&])%([^=&])', r'\1\2', params)
                url = f"{base_url}?{params}"
                info.redirect(QUrl(url))

class WebView(QWebEngineView):
    """Custom web view with enhanced features"""
    
    titleChanged = pyqtSignal(str)
    urlChanged = pyqtSignal(QUrl)
    
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.parent = parent
        
        # Create page with our profile
        self.setPage(QWebEnginePage(self.profile, self))
        
        # Configure page settings
        settings = self.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        
        # Configure web settings
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.XSSAuditingEnabled, False)
        
        # Configure profile settings
        profile = self.page().profile()
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        profile.setPersistentStoragePath("./cache")
        profile.setCachePath("./cache")
        
        # Add request interceptor for CORS
        self.interceptor = RequestInterceptor()
        profile.setUrlRequestInterceptor(self.interceptor)
        
        # Connect signals
        self.page().titleChanged.connect(self.titleChanged)
        self.page().urlChanged.connect(self.urlChanged)
        self.loadFinished.connect(self._on_load_finished)
        
    def _on_load_finished(self, ok):
        """Handle page load finished"""
        if ok:
            url = self.url()
            if url.scheme() not in ("about", "chrome", "qrc"):
                # Initialize VideoJS and HLS support
                js = """
                    // Initialize VideoJS if present
                    if (window.videojs) {
                        // Configure VideoJS defaults
                        videojs.options.autoplay = false;
                        videojs.options.controls = true;
                        videojs.options.html5 = {
                            vhs: {
                                overrideNative: true,
                                fastQualityChange: true,
                                useDevicePixelRatio: true
                            },
                            nativeAudioTracks: false,
                            nativeVideoTracks: false,
                            nativeTextTracks: false
                        };
                        
                        // Add HLS support
                        const players = document.getElementsByClassName('video-js');
                        for (const player of players) {
                            if (!player.player) {
                                videojs(player, {
                                    techOrder: ['html5'],
                                    playbackRates: [0.5, 1, 1.5, 2],
                                    responsive: true,
                                    fluid: true
                                });
                            }
                        }
                        
                        // Add error recovery
                        videojs.hook('error', function(player) {
                            const error = player.error();
                            if (error && error.code === 4) {
                                // Try alternative format
                                const sources = player.currentSources();
                                if (sources && sources.length > 0) {
                                    const currentSrc = sources[0].src;
                                    if (currentSrc) {
                                        // Try switching between HLS and MP4
                                        const newSrc = currentSrc.includes('.m3u8') 
                                            ? currentSrc.replace('.m3u8', '.mp4')
                                            : currentSrc.replace('.mp4', '.m3u8');
                                        player.src(newSrc);
                                        player.play();
                                    }
                                }
                            }
                        });
                    }
                    
                    // Handle native video elements
                    const videos = document.getElementsByTagName('video');
                    for (const video of videos) {
                        video.setAttribute('playsinline', '');
                        video.setAttribute('webkit-playsinline', '');
                        
                        // Add error recovery
                        video.addEventListener('error', (e) => {
                            if (e.target.error.code === 4) {
                                const currentSrc = e.target.src;
                                if (currentSrc) {
                                    const newSrc = currentSrc.includes('.m3u8')
                                        ? currentSrc.replace('.m3u8', '.mp4')
                                        : currentSrc.replace('.mp4', '.m3u8');
                                    e.target.src = newSrc;
                                    e.target.load();
                                }
                            }
                        });
                    }
                """
                self.page().runJavaScript(js)
                
    def createWindow(self, type):
        """Handle new window requests"""
        if self.parent and hasattr(self.parent, 'add_new_tab'):
            return self.parent.add_new_tab()
        return None 