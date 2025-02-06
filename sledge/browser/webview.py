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
                # Inject dark mode preference
                js = """
                    document.documentElement.style.colorScheme = 'dark';
                    if (!document.getElementById('dark-mode-css')) {
                        const style = document.createElement('style');
                        style.id = 'dark-mode-css';
                        style.textContent = `
                            @media (prefers-color-scheme: dark) {
                                :root {
                                    color-scheme: dark;
                                    forced-color-adjust: none;
                                }
                                
                                html {
                                    background: #2e3440 !important;
                                    color: #d8dee9 !important;
                                }
                                
                                body {
                                    background: #2e3440 !important;
                                    color: #d8dee9 !important;
                                }
                                
                                a {
                                    color: #88c0d0 !important;
                                }
                                
                                input, textarea, select {
                                    background: #3b4252 !important;
                                    color: #d8dee9 !important;
                                    border: 1px solid #434c5e !important;
                                }
                                
                                button {
                                    background: #3b4252 !important;
                                    color: #d8dee9 !important;
                                    border: 1px solid #434c5e !important;
                                }
                                
                                button:hover {
                                    background: #4c566a !important;
                                    border-color: #88c0d0 !important;
                                }
                            }
                        `;
                        document.head.appendChild(style);
                    }
                """
                self.page().runJavaScript(js)
                
    def createWindow(self, type):
        """Handle new window requests"""
        if self.parent and hasattr(self.parent, 'add_new_tab'):
            return self.parent.add_new_tab()
        return None 