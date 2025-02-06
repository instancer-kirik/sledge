from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QCheckBox, 
    QPushButton, QLabel, QHBoxLayout
)
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
import re

class SecurityPanel(QWidget):
    """Security settings panel"""
    
    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.layout = QVBoxLayout(self)
        
        # Security settings group
        security_group = QGroupBox("Security Settings")
        security_layout = QVBoxLayout(security_group)
        
        # CORS settings
        self.strict_cors = QCheckBox("Strict CORS Policy")
        self.strict_cors.setChecked(True)
        self.strict_cors.toggled.connect(self._update_security)
        security_layout.addWidget(self.strict_cors)
        
        # Mixed content settings
        self.block_mixed = QCheckBox("Block Mixed Content")
        self.block_mixed.setChecked(True)
        self.block_mixed.toggled.connect(self._update_security)
        security_layout.addWidget(self.block_mixed)
        
        # Dangerous content settings
        self.block_dangerous = QCheckBox("Block Dangerous Content")
        self.block_dangerous.setChecked(True)
        self.block_dangerous.toggled.connect(self._update_security)
        security_layout.addWidget(self.block_dangerous)
        
        self.layout.addWidget(security_group)
        
        # Network settings group
        network_group = QGroupBox("Network Settings")
        network_layout = QVBoxLayout(network_group)
        
        # DNS prefetch
        self.dns_prefetch = QCheckBox("Enable DNS Prefetching")
        self.dns_prefetch.setChecked(True)
        self.dns_prefetch.toggled.connect(self._update_network)
        network_layout.addWidget(self.dns_prefetch)
        
        # Cache settings
        self.disk_cache = QCheckBox("Enable Disk Cache")
        self.disk_cache.setChecked(True)
        self.disk_cache.toggled.connect(self._update_network)
        network_layout.addWidget(self.disk_cache)
        
        self.layout.addWidget(network_group)
        
        # Privacy settings group
        privacy_group = QGroupBox("Privacy Settings")
        privacy_layout = QVBoxLayout(privacy_group)
        
        # Do Not Track
        self.do_not_track = QCheckBox("Send Do Not Track")
        self.do_not_track.setChecked(True)
        self.do_not_track.toggled.connect(self._update_privacy)
        privacy_layout.addWidget(self.do_not_track)
        
        # Third-party cookies
        self.block_third_party = QCheckBox("Block Third-Party Cookies")
        self.block_third_party.setChecked(True)
        self.block_third_party.toggled.connect(self._update_privacy)
        privacy_layout.addWidget(self.block_third_party)
        
        self.layout.addWidget(privacy_group)
        
        # Add stretch at the end
        self.layout.addStretch()
        
    def _update_security(self):
        """Update security settings"""
        profile = self.browser.profile
        settings = profile.settings()
        
        # Update CORS settings
        if hasattr(profile, 'setUrlRequestInterceptor'):
            interceptor = RequestInterceptor(self.browser)
            profile.setUrlRequestInterceptor(interceptor)
            
    def _update_network(self):
        """Update network settings"""
        profile = self.browser.profile
        settings = profile.settings()
        
        # Update DNS prefetch
        if hasattr(settings, 'setAttribute'):
            settings.setAttribute(
                settings.WebAttribute.DnsPrefetchEnabled,
                self.dns_prefetch.isChecked()
            )
            
        # Update cache settings
        if hasattr(profile, 'setHttpCacheType'):
            cache_type = (
                profile.HttpCacheType.DiskHttpCache 
                if self.disk_cache.isChecked() 
                else profile.HttpCacheType.MemoryHttpCache
            )
            profile.setHttpCacheType(cache_type)
            
    def _update_privacy(self):
        """Update privacy settings"""
        profile = self.browser.profile
        
        # Update Do Not Track
        if hasattr(profile, 'setHttpUserAgent'):
            ua = profile.httpUserAgent()
            if self.do_not_track.isChecked():
                if 'DNT=1' not in ua:
                    ua += ' DNT=1'
            else:
                ua = ua.replace('DNT=1', '').strip()
            profile.setHttpUserAgent(ua)
            
        # Update third-party cookies
        if hasattr(profile, 'setPersistentCookiesPolicy'):
            policy = (
                profile.PersistentCookiesPolicy.BlockThirdPartyCookies
                if self.block_third_party.isChecked()
                else profile.PersistentCookiesPolicy.AllowPersistentCookies
            )
            profile.setPersistentCookiesPolicy(policy)

class RequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Intercepts and modifies web requests"""
    
    def __init__(self, browser):
        super().__init__()
        self.browser = browser
    
    def interceptRequest(self, info):
        """Handle request interception"""
        # Set default security headers
        info.setHttpHeader(b"X-Content-Type-Options", b"nosniff")
        info.setHttpHeader(b"X-Frame-Options", b"SAMEORIGIN")
        info.setHttpHeader(b"X-XSS-Protection", b"1; mode=block")
        
        # Set default CORS headers
        info.setHttpHeader(b"Access-Control-Allow-Origin", b"*")
        info.setHttpHeader(b"Access-Control-Allow-Methods", b"GET, POST, OPTIONS")
        info.setHttpHeader(b"Access-Control-Allow-Headers", b"*")
        
        # Set dark mode preference
        info.setHttpHeader(b"Sec-CH-Prefers-Color-Scheme", b"dark")
        
        # Handle video source domains
        url = info.requestUrl().toString()
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
                
        # Block dangerous ports if enabled
        if self.block_dangerous:
            port = info.requestUrl().port()
            if port in self.dangerous_ports:
                info.block(True)
                return
                
        # Block mixed content if enabled
        if self.block_mixed:
            if info.requestUrl().scheme() == 'http' and info.firstPartyUrl().scheme() == 'https':
                info.block(True)
                return 