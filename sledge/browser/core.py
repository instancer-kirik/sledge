import sys
import os
from PyQt6.QtCore import QUrl, Qt, QSize, QFileInfo, QPoint, QSettings, QStandardPaths, QTimer, QEvent
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit, QProgressBar, 
    QStatusBar, QMenu, QDialog, QVBoxLayout, QPushButton, QFileDialog,
    QDockWidget, QWidget, QLabel, QListWidget, QListWidgetItem, QComboBox, QHBoxLayout, QGroupBox, QCheckBox, QTabWidget
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineScript,
    QWebEngineSettings
)
from PyQt6.QtGui import QAction, QIcon, QColor
import json

from .tabs.widgets import TabWidget
from .ui.widgets import HTMLViewerWidget, BookmarkWidget, DownloadWidget, StyleAdjusterPanel
from .ui.styles import BrowserTheme, apply_dark_mode_js
from .history import HistoryManager
from .ui.dialogs import SettingsDialog
from .security import SecurityPanel, RequestInterceptor

class ExtensionManager:
    def __init__(self, browser):
        self.browser = browser
        self.extensions = {}
        self.extension_dir = os.path.expanduser('~/.sledge/extensions')
        os.makedirs(self.extension_dir, exist_ok=True)
        
        # Create Firefox and Chrome extension directories
        self.firefox_dir = os.path.join(self.extension_dir, 'firefox')
        self.chrome_dir = os.path.join(self.extension_dir, 'chrome')
        os.makedirs(self.firefox_dir, exist_ok=True)
        os.makedirs(self.chrome_dir, exist_ok=True)

    def load_extensions(self):
        """Load both Firefox and Chrome extensions"""
        self._load_firefox_extensions()
        self._load_chrome_extensions()

    def _load_firefox_extensions(self):
        """Load Firefox extensions (.xpi files)"""
        for xpi in os.listdir(self.firefox_dir):
            if xpi.endswith('.xpi'):
                self._load_firefox_extension(os.path.join(self.firefox_dir, xpi))

    def _load_chrome_extensions(self):
        """Load Chrome extensions (.crx files)"""
        for crx in os.listdir(self.chrome_dir):
            if crx.endswith('.crx'):
                self._load_chrome_extension(os.path.join(self.chrome_dir, crx))

class Settings:
    def __init__(self):
        self.settings = QSettings('Sledge', 'Browser')
        self.load_defaults()

    def load_defaults(self):
        """Set default settings if not already set"""
        defaults = {
            'privacy': {
                'do_not_track': True,
                'block_third_party_cookies': True,
                'clear_on_exit': False,
            },
            'security': {
                'strict_cors': True,
                'block_mixed_content': True,
                'block_dangerous_ports': True,
                'block_dangerous_schemes': True,
                'dev_mode': False,
            },
            'downloads': {
                'default_path': QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation),
                'ask_for_location': True,
            },
            'appearance': {
                'dark_mode': True,
                'tab_position': 'top',
                'show_bookmarks_bar': True,
            },
            'startup': {
                'restore_session': True,
                'home_page': 'https://duckduckgo.com',
            }
        }
        
        for section, values in defaults.items():
            if not self.settings.contains(section):
                self.settings.setValue(section, values)

    def get(self, section, key):
        """Get a setting value"""
        return self.settings.value(section, {}).get(key)

    def set(self, section, key, value):
        """Set a setting value"""
        settings_dict = self.settings.value(section, {})
        settings_dict[key] = value
        self.settings.setValue(section, settings_dict)
        self.settings.sync()

class SledgeBrowser(QMainWindow):
    def __init__(self):
        print("\n" + "="*50)
        print("🔍 [SLEDGE INIT] Starting SledgeBrowser initialization...")
        super().__init__()
        self.settings = Settings()
        print("🔍 [SLEDGE INIT] Created Settings")
        self.history_manager = HistoryManager()
        print("🔍 [SLEDGE INIT] Created HistoryManager")
        self.dev_tools_windows = {}
        self.page_profiles = {}
        self.tab_search_active = False
        self.theme = BrowserTheme()
        print("🔍 [SLEDGE INIT] Created BrowserTheme")
        self.extension_manager = ExtensionManager(self)
        print("🔍 [SLEDGE INIT] Created ExtensionManager")
        self.profile = self.setup_profile()
        print("🔍 [SLEDGE INIT] Setup Profile")
        self.loading_tabs = set()
        self.workspaces = {}
        self.current_workspace = None
        print("🔍 [SLEDGE INIT] About to initUI")
        self.initUI()
        print("🔍 [SLEDGE INIT] Finished initUI")
        self.setup_dev_tools()
        print("🔍 [SLEDGE INIT] Setup DevTools")
        self.setup_workspaces()
        print("🔍 [SLEDGE INIT] Setup Workspaces")
        self.setup_workspace_toolbar()
        print("🔍 [SLEDGE INIT] Setup Workspace Toolbar")
        print("🔍 [SLEDGE INIT] Initialization Complete!")
        print("="*50 + "\n")

    def setup_profile(self):
        """Set up browser profile with enhanced security defaults"""
        profile = QWebEngineProfile.defaultProfile()
        
        # Set modern user agent without problematic headers
        modern_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        profile.setHttpUserAgent(modern_agent)
        
        # Configure security settings
        settings = profile.settings()
        
        # Enable modern security features
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.XSSAuditingEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.NavigateOnDropEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowGeolocationOnInsecureOrigins, False)

        # Privacy settings
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled,
                            not self.settings.get('privacy', 'clear_on_exit'))
        
        # Enhanced cookie settings
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
            if not self.settings.get('privacy', 'clear_on_exit')
            else QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )
        
        # Set up request interceptor with enhanced security
        self.request_interceptor = self.create_request_interceptor()
        profile.setUrlRequestInterceptor(self.request_interceptor)
        
        # Inject security and dark mode scripts
        self.inject_security_scripts(profile)
        self.inject_dark_mode_script(profile)
        
        return profile

    def create_tab_profile(self):
        """Create isolated profile for tab"""
        profile = QWebEngineProfile()
        
        # Inherit main profile settings
        profile.setHttpUserAgent(self.profile.httpUserAgent())
        profile.setHttpAcceptLanguage(self.profile.httpAcceptLanguage())
        
        # Set up caching
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(
            self.profile.persistentCookiesPolicy()
        )
        
        # Add security settings
        profile.setUrlRequestInterceptor(self.request_interceptor)
        
        return profile

    def inject_security_scripts(self, profile):
        """Inject security-related scripts"""
        security_script = """
            (function() {
                // CSP reporting
                document.addEventListener('securitypolicyviolation', (e) => {
                    console.log('CSP violation:', e);
                    window.qt.securityViolation(JSON.stringify({
                        'directive': e.violatedDirective,
                        'blockedURI': e.blockedURI,
                        'originalPolicy': e.originalPolicy
                    }));
                });
                
                // Mixed content detection
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        mutation.addedNodes.forEach((node) => {
                            if (node.tagName === 'SCRIPT' || node.tagName === 'LINK') {
                                const url = node.src || node.href;
                                if (url && url.startsWith('http:')) {
                                    window.qt.mixedContentDetected(url);
                                }
                            }
                        });
                    });
                });
                observer.observe(document, { childList: true, subtree: true });
                
                // Anti-fingerprinting
                const protectFingerprint = () => {
                    const protect = (obj, prop) => {
                        const descriptor = Object.getOwnPropertyDescriptor(obj, prop);
                        if (descriptor && descriptor.configurable) {
                            Object.defineProperty(obj, prop, {
                                get: () => undefined
                            });
                        }
                    };
                    
                    // Protect canvas fingerprinting
                    const getContext = HTMLCanvasElement.prototype.getContext;
                    HTMLCanvasElement.prototype.getContext = function() {
                        const context = getContext.apply(this, arguments);
                        if (context && arguments[0] === '2d') {
                            const getImageData = context.getImageData;
                            context.getImageData = function() {
                                // Add slight noise to prevent fingerprinting
                                const imageData = getImageData.apply(this, arguments);
                                const pixels = imageData.data;
                                for (let i = 0; i < pixels.length; i += 4) {
                                    pixels[i] += Math.random() < 0.5 ? 1 : -1;
                                }
                                return imageData;
                            };
                        }
                        return context;
                    };
                    
                    // Protect audio fingerprinting
                    protect(AudioBuffer.prototype, 'getChannelData');
                    protect(AnalyserNode.prototype, 'getFloatFrequencyData');
                    
                    // Protect WebRTC fingerprinting
                    protect(RTCPeerConnection.prototype, 'createDataChannel');
                    protect(RTCPeerConnection.prototype, 'createOffer');
                    protect(RTCPeerConnection.prototype, 'createAnswer');
                };
                
                protectFingerprint();
            })();
        """
        
        script = QWebEngineScript()
        script.setName("security")
        script.setSourceCode(security_script)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
        script.setRunsOnSubFrames(True)
        
        profile.scripts().insert(script)
        
    def inject_dark_mode_script(self, profile):
        """Inject dark mode script separately"""
        early_dark = """
            (function() {
                const style = document.createElement('style');
                style.textContent = `
                    * { 
                        background-color: #212121 !important;
                        color: #e0e0e0 !important;
                        transition: none !important;
                    }
                `;
                document.documentElement.appendChild(style);
            })();
        """
        
        script = QWebEngineScript()
        script.setName("dark_mode")
        script.setSourceCode(early_dark)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
        script.setRunsOnSubFrames(True)
        
        profile.scripts().insert(script)

    def create_request_interceptor(self):
        """Create request interceptor for security and privacy"""
        return RequestInterceptor(self)

    def get_icon(self, name):
        """Get icon or return a default one if missing"""
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', f'{name}.png')
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        
        # Default icons using standard theme
        defaults = {
            'new_tab': 'document-new',
            'back': 'go-previous',
            'forward': 'go-next',
            'reload': 'view-refresh',
            'tabs': 'view-list',
            'settings': 'preferences-system',
            'history': 'document-open-recent'
        }
        return QIcon.fromTheme(defaults.get(name, 'application-x-executable'))

    def initUI(self):
        print("\n" + "-"*50)
        print("🎨 [SLEDGE UI] Starting UI initialization...")
        self.setWindowTitle('Sledge Browser')
        self.setGeometry(100, 100, 1280, 800)
        print("🎨 [SLEDGE UI] Set window properties")

        # Enable touch gestures
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self.touch_start = None
        self.touch_tracking = False
        self.touch_timer = QTimer()
        self.touch_timer.setSingleShot(True)
        self.touch_timer.setInterval(500)  # 500ms for long press
        self.touch_timer.timeout.connect(self._handle_long_press)
        print("🎨 [SLEDGE UI] Enabled touch gestures")

        # Create ImprovedTabWidget
        print("🎨 [SLEDGE UI] Creating tab widget...")
        self.tabs = TabWidget()
        print("🎨 [SLEDGE UI] Successfully created TabWidget")
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)
        print("🎨 [SLEDGE UI] Created tab widget")

        # Create NavBar
        print("🎨 [SLEDGE UI] Creating navbar...")
        navbar = QToolBar()
        navbar.setMovable(False)
        navbar.setIconSize(QSize(16, 16))
        self.addToolBar(navbar)
        print("🎨 [SLEDGE UI] Created navbar")

        # Navigation buttons
        print("🎨 [SLEDGE UI] Adding navigation buttons...")
        back_btn = QAction(self.get_icon('back'), 'Back', self)
        back_btn.setToolTip("Go Back (Alt+Left)")
        back_btn.setShortcut("Alt+Left")
        back_btn.setStatusTip("Go back one page")
        back_btn.triggered.connect(lambda: self.current_tab().back())
        navbar.addAction(back_btn)
        print("🎨 [SLEDGE UI] Added back button")

        forward_btn = QAction(self.get_icon('forward'), 'Forward', self)
        forward_btn.setToolTip("Go Forward (Alt+Right)")
        forward_btn.setShortcut("Alt+Right")
        forward_btn.setStatusTip("Go forward one page")
        forward_btn.triggered.connect(lambda: self.current_tab().forward())
        navbar.addAction(forward_btn)
        print("🎨 [SLEDGE UI] Added forward button")

        reload_btn = QAction(self.get_icon('reload'), 'Reload', self)
        reload_btn.setToolTip("Reload Page (F5)")
        reload_btn.setShortcut("F5")
        reload_btn.setStatusTip("Reload current page")
        reload_btn.triggered.connect(lambda: self.current_tab().reload())
        navbar.addAction(reload_btn)
        print("🎨 [SLEDGE UI] Added reload button")

        # Add New Tab button with dropdown
        new_tab_btn = QAction(self.get_icon('new_tab'), 'New Tab', self)
        new_tab_btn.setToolTip("New Tab (Ctrl+T)")
        new_tab_btn.setShortcut("Ctrl+T")
        new_tab_btn.setStatusTip("Open a new tab")
        new_tab_btn.triggered.connect(self.show_new_tab_menu)
        navbar.addAction(new_tab_btn)

        # Tab Management Button
        tab_manage_btn = QAction(self.get_icon('tabs'), 'Tab Management', self)
        tab_manage_btn.setToolTip("Manage Tabs (Ctrl+M)")
        tab_manage_btn.setShortcut("Ctrl+M")
        tab_manage_btn.setStatusTip("Show tab management options")
        tab_manage_btn.triggered.connect(self.show_tab_management)
        navbar.addAction(tab_manage_btn)

        # Style Adjuster button and panel
        style_btn = QAction(self.get_icon('style'), 'Style Adjuster', self)
        style_btn.setToolTip("Adjust Page Style (Ctrl+B)")
        style_btn.setShortcut("Ctrl+B")
        style_btn.triggered.connect(self.toggle_style_panel)
        navbar.addAction(style_btn)

        # Style the navbar buttons
        navbar.setStyleSheet("""
            QToolBar {
                spacing: 5px;
                padding: 5px;
            }
            QToolButton {
                min-width: 40px;
                padding: 5px;
                border-radius: 5px;
                color: #d8dee9;
            }
            QToolButton:hover {
                background: #3b4252;
            }
            QToolButton::menu-indicator {
                image: none;
            }
            QToolButton[popupMode="1"] {
                padding-right: 20px;
            }
            QToolButton::menu-button {
                width: 16px;
                border: none;
            }
            QToolButton::menu-button:hover {
                background: none;
            }
        """)

        # Enhanced URL Bar
        self.url_bar = EnhancedURLBar(self)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.textEdited.connect(self.on_url_edit)
        navbar.addWidget(self.url_bar)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(120)
        navbar.addWidget(self.progress_bar)

        # Initialize tab groups
        self.initialize_default_groups()

        # Add bookmark and download widgets
        self.setup_bookmark_widget()
        self.setup_download_widget()

        # Apply theme
        self.setStyleSheet(self.theme.get_stylesheet())

        # Load extensions
        self.extension_manager.load_extensions()

        # Add initial tab
        self.add_new_tab()

        # Add Settings button
        settings_btn = QAction(self.get_icon('settings'), 'Settings', self)
        settings_btn.triggered.connect(self.show_settings)
        navbar.addAction(settings_btn)

        # Add History button
        history_btn = QAction(self.get_icon('history'), 'History', self)
        history_btn.triggered.connect(self.show_history)
        navbar.addAction(history_btn)
        
        # Add Extensions button
        extensions_btn = QAction(self.get_icon('extension'), 'Extensions', self)
        extensions_btn.triggered.connect(self.show_extensions)
        navbar.addAction(extensions_btn)

        # Create style adjuster panel
        self.style_dock = QDockWidget("Style Adjuster", self)
        self.style_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.style_panel = StyleAdjusterPanel(self)
        self.style_dock.setWidget(self.style_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.style_dock)
        self.style_dock.hide()

    def initialize_default_groups(self):
        """Initialize default tab groups"""
        self.tabs.createGroup("Work", QColor(200, 230, 200))
        self.tabs.createGroup("Personal", QColor(230, 200, 200))
        self.tabs.createGroup("Reference", QColor(200, 200, 230))
        self.tabs.createGroup("Media", QColor(230, 230, 200))

    def setup_bookmark_widget(self):
        """Set up the bookmark widget and dock"""
        self.bookmark_dock = QDockWidget("Bookmarks", self)
        self.bookmark_widget = BookmarkWidget()
        self.bookmark_widget.bookmark_clicked.connect(self.load_bookmark)
        self.bookmark_dock.setWidget(self.bookmark_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.bookmark_dock)
        self.bookmark_dock.hide()

    def setup_download_widget(self):
        """Set up the download widget and dock"""
        self.download_dock = QDockWidget("Downloads", self)
        self.download_widget = DownloadWidget()
        self.download_dock.setWidget(self.download_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.download_dock)
        self.download_dock.hide()

    def add_new_tab(self, qurl=None, label="New Tab"):
        """Add new browser tab with process isolation and optimizations"""
        if qurl is None:
            qurl = QUrl('about:blank')
            
        # Create browser with dark background and process isolation
        browser = QWebEngineView()
        browser.setStyleSheet("""
            QWebEngineView {
                background: #212121;
            }
        """)
        
        # Create page with optimizations
        page = QWebEnginePage(self.profile, browser)  # Use main profile to prevent early deletion
        page.setBackgroundColor(QColor("#212121"))
        
        # Performance optimizations
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)  # Reduce painting
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, False)  # Disable unused features
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        
        # Enable hardware acceleration
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        
        # Connect signals
        page.loadStarted.connect(lambda: self.loading_started(browser))
        page.loadProgress.connect(lambda p: self.loading_progress(browser, p))
        page.loadFinished.connect(lambda: self.loading_finished(browser))
        browser.iconChanged.connect(lambda: self.update_tab_icon(browser))
        page.titleChanged.connect(lambda title: self.update_tab_title(browser, title))
        
        # Add context menu
        browser.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        browser.customContextMenuRequested.connect(
            lambda pos: self.show_web_context_menu(browser, pos)
        )
        
        # Set up resource hints
        self.setup_resource_hints(page)
        
        # Inject performance optimizations
        self.inject_performance_scripts(page)
        
        # Set the page before loading
        browser.setPage(page)
        
        # Store reference to prevent garbage collection
        browser.page_ref = page
        
        # Load URL after all setup is done
        browser.setUrl(qurl)
        
        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)
        return i

    def setup_resource_hints(self, page):
        """Set up resource hints for performance"""
        hints_script = """
        (function() {
                // DNS prefetch
                const prefetchDomains = new Set();
                document.addEventListener('mouseover', (e) => {
                    const link = e.target.closest('a');
                    if (link && link.href) {
                        const domain = new URL(link.href).hostname;
                        if (!prefetchDomains.has(domain)) {
                            prefetchDomains.add(domain);
                            const hint = document.createElement('link');
                            hint.rel = 'dns-prefetch';
                            hint.href = `//${domain}`;
                            document.head.appendChild(hint);
                        }
                    }
                });
                
                // Preconnect on hover
                document.addEventListener('mouseover', (e) => {
                    const link = e.target.closest('a');
                    if (link && link.href) {
                        const hint = document.createElement('link');
                        hint.rel = 'preconnect';
                        hint.href = link.href;
                        document.head.appendChild(hint);
                        setTimeout(() => hint.remove(), 5000);
                    }
                });
                
                // Prerender on high-confidence navigation prediction
                let lastHover = null;
                document.addEventListener('mouseover', (e) => {
                    const link = e.target.closest('a');
                    if (link && link.href) {
                        lastHover = { link, time: Date.now() };
                        setTimeout(() => {
                            if (lastHover && lastHover.link === link && 
                                Date.now() - lastHover.time > 1000) {
                                const hint = document.createElement('link');
                                hint.rel = 'prerender';
                                hint.href = link.href;
                                document.head.appendChild(hint);
                            }
                        }, 1000);
                    }
                });
            })();
        """
        page.runJavaScript(hints_script)
        
    def inject_performance_scripts(self, page):
        """Inject performance optimization scripts"""
        performance_script = """
            (function() {
                // Lazy load images
                document.addEventListener('DOMContentLoaded', () => {
                    const images = document.querySelectorAll('img[data-src]');
                    const imageObserver = new IntersectionObserver((entries) => {
                        entries.forEach(entry => {
                            if (entry.isIntersecting) {
                                const img = entry.target;
                                img.src = img.dataset.src;
                                imageObserver.unobserve(img);
                            }
                        });
                    });
                    
                    images.forEach(img => imageObserver.observe(img));
                });
                
                // Defer non-critical resources
                const deferResource = (element) => {
                    if (element.tagName === 'SCRIPT' && !element.async && !element.defer) {
                        element.defer = true;
                    }
                };
                
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach(mutation => {
                        mutation.addedNodes.forEach(node => {
                            if (node.nodeType === 1) {  // Element node
                                deferResource(node);
                            }
                        });
                    });
                });
                
                observer.observe(document, { 
                    childList: true, 
                    subtree: true 
                });
                
                // Optimize animations
                const optimizeAnimations = () => {
                    const style = document.createElement('style');
                    style.textContent = `
                        @media (prefers-reduced-motion: reduce) {
                            *, *::before, *::after {
                                animation-duration: 0.01ms !important;
                                animation-iteration-count: 1 !important;
                                transition-duration: 0.01ms !important;
                                scroll-behavior: auto !important;
                            }
                        }
                    `;
                    document.head.appendChild(style);
                };
                
                optimizeAnimations();
        })();
        """
        page.runJavaScript(performance_script)

    def loading_started(self, browser):
        """Handle page load start"""
        self.loading_tabs.add(browser)
        # Ensure dark background during load
        browser.page().setBackgroundColor(QColor("#212121"))
        browser.setStyleSheet("background: #212121;")

    def loading_progress(self, browser, progress):
        """Handle page load progress"""
        if browser in self.loading_tabs:
            # Maintain dark background during load
            browser.page().setBackgroundColor(QColor("#212121"))
            browser.setStyleSheet("background: #212121;")

    def loading_finished(self, browser):
        """Handle page load completion"""
        if browser in self.loading_tabs:
            self.loading_tabs.remove(browser)
            # Re-inject dark mode to catch any missed elements
            self.inject_dark_mode_to_tab(browser)

    def handle_load_finished(self, web_view, ok):
        """Handle page load completion"""
        index = self.tabs.indexOf(web_view)
        if not ok:
            # Handle load failure
            error_html = """
            <html>
            <body style="background: #2e3440; color: #d8dee9; font-family: sans-serif; padding: 2em;">
                <h2>⚠️ Page Load Failed</h2>
                <p>The requested page could not be loaded.</p>
                <p>Possible reasons:</p>
                <ul>
                    <li>No internet connection</li>
                    <li>Website is down</li>
                    <li>Invalid URL</li>
                </ul>
                <button onclick="window.location.reload()" 
                        style="padding: 8px 16px; background: #5e81ac; color: white; 
                               border: none; border-radius: 4px; cursor: pointer;">
                    Try Again
                </button>
            </body>
            </html>
            """
            web_view.setHtml(error_html)
            self.tabs.setTabIcon(index, self.get_icon('error'))
        else:
            # Update favicon
            icon = web_view.icon()
            if not icon.isNull():
                self.tabs.setTabIcon(index, icon)

    def create_web_profile(self, browser):
        """Create a web profile with privacy settings"""
        profile = QWebEngineProfile(browser)
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        profile.setHttpAcceptLanguage("en-US,en;q=0.9")
        profile.setHttpUserAgent(profile.httpUserAgent() + 
                               " Permissions-Policy: interest-cohort=()")
        return profile

    def show_settings(self):
        """Show settings dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        layout = QVBoxLayout(dialog)
        
        # Create tab widget for settings
        tabs = QTabWidget()
        
        # Add security panel
        security_panel = SecurityPanel(self.settings)
        tabs.addTab(security_panel, "Security")
        
        # Add privacy panel
        privacy_panel = QWidget()
        privacy_layout = QVBoxLayout(privacy_panel)
        
        do_not_track = QCheckBox("Enable Do Not Track")
        do_not_track.setChecked(self.settings.get('privacy', 'do_not_track'))
        do_not_track.stateChanged.connect(
            lambda state: self.settings.set('privacy', 'do_not_track', bool(state))
        )
        privacy_layout.addWidget(do_not_track)
        
        block_cookies = QCheckBox("Block Third-Party Cookies")
        block_cookies.setChecked(self.settings.get('privacy', 'block_third_party_cookies'))
        block_cookies.stateChanged.connect(
            lambda state: self.settings.set('privacy', 'block_third_party_cookies', bool(state))
        )
        privacy_layout.addWidget(block_cookies)
        
        clear_exit = QCheckBox("Clear Data on Exit")
        clear_exit.setChecked(self.settings.get('privacy', 'clear_on_exit'))
        clear_exit.stateChanged.connect(
            lambda state: self.settings.set('privacy', 'clear_on_exit', bool(state))
        )
        privacy_layout.addWidget(clear_exit)
        
        tabs.addTab(privacy_panel, "Privacy")
        
        # Add appearance panel
        appearance_panel = QWidget()
        appearance_layout = QVBoxLayout(appearance_panel)
        
        dark_mode = QCheckBox("Dark Mode")
        dark_mode.setChecked(self.settings.get('appearance', 'dark_mode'))
        dark_mode.stateChanged.connect(
            lambda state: self.settings.set('appearance', 'dark_mode', bool(state))
        )
        appearance_layout.addWidget(dark_mode)
        
        show_bookmarks = QCheckBox("Show Bookmarks Bar")
        show_bookmarks.setChecked(self.settings.get('appearance', 'show_bookmarks_bar'))
        show_bookmarks.stateChanged.connect(
            lambda state: self.settings.set('appearance', 'show_bookmarks_bar', bool(state))
        )
        appearance_layout.addWidget(show_bookmarks)
        
        tabs.addTab(appearance_panel, "Appearance")
        
        # Add downloads panel
        downloads_panel = QWidget()
        downloads_layout = QVBoxLayout(downloads_panel)
        
        ask_location = QCheckBox("Ask for Download Location")
        ask_location.setChecked(self.settings.get('downloads', 'ask_for_location'))
        ask_location.stateChanged.connect(
            lambda state: self.settings.set('downloads', 'ask_for_location', bool(state))
        )
        downloads_layout.addWidget(ask_location)
        
        path_layout = QHBoxLayout()
        path_label = QLabel("Default Download Path:")
        path_layout.addWidget(path_label)
        
        path_edit = QLineEdit(self.settings.get('downloads', 'default_path'))
        path_layout.addWidget(path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(lambda: self._browse_download_path(path_edit))
        path_layout.addWidget(browse_btn)
        
        downloads_layout.addLayout(path_layout)
        tabs.addTab(downloads_panel, "Downloads")
        
        # Add tabs to dialog
        layout.addWidget(tabs)
        
        # Add buttons
        buttons = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_settings()

    def _browse_download_path(self, line_edit):
        """Browse for download path"""
        path = QFileDialog.getExistingDirectory(
            self, "Select Download Directory",
            self.settings.get('downloads', 'default_path')
        )
        if path:
            line_edit.setText(path)
            self.settings.set('downloads', 'default_path', path)

    def apply_settings(self):
        """Apply current settings"""
        # Apply privacy settings
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(
            QWebEngineProfile.HttpCacheType.MemoryHttpCache
            if self.settings.get('privacy', 'clear_on_exit')
            else QWebEngineProfile.HttpCacheType.DiskHttpCache
        )
        
        # Apply appearance settings
        if self.settings.get('appearance', 'dark_mode'):
            self.setStyleSheet(self.theme.get_stylesheet())
            self.inject_dark_mode()
        
        # Apply download settings
        self.download_widget.default_path = self.settings.get('downloads', 'default_path')
        
        # Apply startup settings
        if self.settings.get('startup', 'restore_session'):
            self.load_session()

    def save_session(self):
        """Save current session"""
        session = {
            'tabs': [],
            'current_tab': self.tabs.currentIndex(),
            'groups': {}
        }
        
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'url'):
                session['tabs'].append({
                    'url': tab.url().toString(),
                    'title': self.tabs.tabText(i),
                    'group': self.tabs.tab_groups.get(i)
                })
        
        session_file = os.path.expanduser('~/.sledge/session.json')
        os.makedirs(os.path.dirname(session_file), exist_ok=True)
        with open(session_file, 'w') as f:
            json.dump(session, f)

    def load_session(self):
        """Load previous session"""
        session_file = os.path.expanduser('~/.sledge/session.json')
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                session = json.load(f)
            
            # Close current tabs
            while self.tabs.count() > 0:
                self.tabs.removeTab(0)
            
            # Restore tabs
            for tab in session['tabs']:
                index = self.add_new_tab(QUrl(tab['url']))
                self.tabs.setTabText(index, tab['title'])
                if tab['group']:
                    self.tabs.addTabToGroup(index, tab['group'])
            
            # Restore current tab
            if session['current_tab'] < self.tabs.count():
                self.tabs.setCurrentIndex(session['current_tab'])

    def handle_download(self, download):
        """Handle file download"""
        if self.settings.get('downloads', 'ask_for_location'):
            path, _ = QFileDialog.getSaveFileName(
                self, "Save File",
                os.path.join(
                    self.settings.get('downloads', 'default_path'),
                    download.suggestedFileName()
                ))
            if path:
                download.setDownloadDirectory(os.path.dirname(path))
                download.setDownloadFileName(os.path.basename(path))
                download.accept()
                self.download_widget.add_download(download)
                self.download_dock.show()
        else:
            path = os.path.join(
                self.settings.get('downloads', 'default_path'),
                download.suggestedFileName()
            )
            download.setDownloadDirectory(os.path.dirname(path))
            download.setDownloadFileName(os.path.basename(path))
            download.accept()
            self.download_widget.add_download(download)

    def closeEvent(self, event):
        """Handle browser closing with cleanup"""
        if self.settings.get('startup', 'restore_session'):
            self.save_session()
        
        # Clean up web profiles and pages
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'page_ref'):
                # Disconnect all signals
                page = tab.page_ref
                page.loadStarted.disconnect()
                page.loadProgress.disconnect()
                page.loadFinished.disconnect()
                page.titleChanged.disconnect()
                # Delete page explicitly
                page.deleteLater()
                del tab.page_ref
            tab.deleteLater()
        
        # Clear any temporary data if needed
        if self.settings.get('privacy', 'clear_on_exit'):
            self.profile.clearHttpCache()
            self.profile.clearAllVisitedLinks()
        
        event.accept()

    def show_history(self):
        """Show history dialog"""
        entries = self.history_manager.get_history()
        dialog = QDialog(self)
        dialog.setWindowTitle("History")
        layout = QVBoxLayout(dialog)
        
        # Search box
        search = QLineEdit()
        search.setPlaceholderText("Search history...")
        layout.addWidget(search)
        
        # History list
        history_list = QListWidget()
        layout.addWidget(history_list)
        
        # Clear button
        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(lambda: self.history_manager.clear_history())
        layout.addWidget(clear_btn)
        
        def update_list(search_text=""):
            history_list.clear()
            entries = self.history_manager.get_history(search=search_text)
            for url, title, visit_time, count in entries:
                item = QListWidgetItem(f"{title}\n{url}")
                item.setData(Qt.ItemDataRole.UserRole, url)
                history_list.addItem(item)
        
        # Connect signals
        search.textChanged.connect(update_list)
        history_list.itemDoubleClicked.connect(
            lambda item: self.add_new_tab(QUrl(item.data(Qt.ItemDataRole.UserRole)))
        )
        self.history_manager.history_updated.connect(
            lambda: update_list(search.text())
        )
        
        update_list()
        dialog.exec()

    def close_tab(self, index):
        """Close tab at given index"""
        if self.tabs.count() < 2:  # Keep at least one tab
            return
            
        # Clean up the tab's page
        tab = self.tabs.widget(index)
        if hasattr(tab, 'page_ref'):
            # Disconnect all signals
            page = tab.page_ref
            page.loadStarted.disconnect()
            page.loadProgress.disconnect()
            page.loadFinished.disconnect()
            page.titleChanged.disconnect()
            # Delete page explicitly
            page.deleteLater()
            del tab.page_ref
            
        self.tabs.removeTab(index)

    def current_tab(self):
        """Get current tab widget"""
        return self.tabs.currentWidget()

    def navigate_to_url(self):
        """Navigate to URL in url bar"""
        q = QUrl(self.url_bar.text())
        if q.scheme() == "":
            q.setScheme("http")
        self.current_tab().setUrl(q)

    def update_urlbar(self, q, browser=None):
        """Update URL bar with current URL"""
        if browser != self.current_tab():
            return
        self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0)

    def update_progress(self, progress):
        """Update progress bar"""
        self.progress_bar.setValue(progress)

    def load_bookmark(self, url):
        """Load URL from bookmark"""
        self.add_new_tab(QUrl(url))

    def show_tab_management(self):
        """Show tab management menu"""
        menu = QMenu(self)
        
        # Toggle compact mode
        compact_action = menu.addAction("Compact Mode")
        compact_action.setCheckable(True)
        compact_action.setChecked(getattr(self.tabs, 'compact_mode', False))
        compact_action.triggered.connect(
            lambda x: setattr(self.tabs, 'compact_mode', x)
        )
        
        # Group management submenu
        group_menu = menu.addMenu("Tab Groups")
        for group_name in self.tabs.groups:
            action = group_menu.addAction(group_name)
            action.triggered.connect(
                lambda x, g=group_name: self.tabs.addTabToGroup(
                    self.tabs.currentIndex(), g
                )
            )
        
        # Add tab management actions
        menu.addSeparator()
        menu.addAction("Show All Tabs", self.tabs.show_spread)
        menu.addAction("New Group...", self.create_new_group_with_tab)
        menu.addAction("Sort by Group", self.tabs._organize_tabs)
        
        # Get the button that triggered this
        button = self.findChild(QToolBar).widgetForAction(
            [a for a in self.findChild(QToolBar).actions() 
             if a.text() == 'Tab Management'][0]
        )
        menu.exec(button.mapToGlobal(QPoint(0, button.height())))

    def inject_dark_mode(self):
        """Inject dark mode CSS into web pages"""
        script = QWebEngineScript()
        script.setName("dark_mode")
        script.setSourceCode(apply_dark_mode_js())
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(True)
        
        # Add to all existing tabs
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, QWebEngineView):
                tab.page().scripts().insert(script)

    def on_url_edit(self, text):
        """Handle URL bar text changes"""
        if not text:
            self.url_bar.suggestions_list.hide()
            return

        suggestions = []
        
        # Check for special prefixes
        if text.startswith("tab:") or text.lower().startswith("t "):
            # Tab search mode
            search_text = text.split(":", 1)[1].strip() if ":" in text else text[2:].strip()
            suggestions.extend(self.search_tabs(search_text))
        else:
            # Regular mode - search everything
            # Add tab suggestions first
            tab_results = self.search_tabs(text)
            if tab_results:
                suggestions.extend(tab_results)

            # Add history suggestions
            history = self.history_manager.get_history(limit=5, search=text)
            for url, title, _, _ in history:
                item = ("history", title, url, f"History: {title}")
                if item not in suggestions:
                    suggestions.append(item)

            # Add search suggestions
            if not any(s[2].startswith(text) for s in suggestions):
                # Prepare different search queries
                search_suggestions = [
                    ("search", f"Search for: {text}", 
                     f"https://duckduckgo.com/?q={text}", "Web Search"),
                    ("search", f"Site search: {text}", 
                     f"site:{self.current_tab().url().host()} {text}", "Site Search"),
                    ("search", f"Scholar: {text}", 
                     f"https://scholar.google.com/scholar?q={text}", "Academic Search")
                ]
                suggestions.extend(search_suggestions)

        # Update suggestions list
        self.url_bar.suggestions_list.clear()
        for category, title, url, display_text in suggestions:
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, url)
            item.setData(Qt.ItemDataRole.UserRole + 1, category)
            # Set category property for styling
            item.setData(Qt.ItemDataRole.UserRole + 2, category)
            self.url_bar.suggestions_list.addItem(item)

        if self.url_bar.suggestions_list.count():
            self.url_bar.show_suggestions()
        else:
            self.url_bar.suggestions_list.hide()

    def search_tabs(self, text):
        """Search through open tabs"""
        results = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            title = self.tabs.tabText(i)
            url = tab.url().toString() if hasattr(tab, 'url') else ""
            
            # Check if text matches title or URL
            if (text.lower() in title.lower() or 
                text.lower() in url.lower()):
                group = self.tabs.tabBar.tab_groups.get(i, "")
                display_text = f"Tab: {title}"
                if group:
                    display_text = f"Tab [{group}]: {title}"
                results.append(("tab", title, f"tab:{i}", display_text))
        
        return results

    def use_suggestion(self, item):
        """Use selected suggestion"""
        url = item.data(Qt.ItemDataRole.UserRole)
        category = item.data(Qt.ItemDataRole.UserRole + 1)
        
        if category == "tab":
            # Switch to tab
            tab_index = int(url.split(":")[1])
            self.tabs.setCurrentIndex(tab_index)
            self.url_bar.clear()
        else:
            # Regular URL navigation
            self.url_bar.setText(url)
            self.url_bar.suggestions_list.hide()
            self.navigate_to_url()

    def show_new_tab_menu(self):
        """Show new tab menu with group options"""
        menu = QMenu(self)
        
        # New Tab (No Group)
        new_tab_action = menu.addAction("New Tab")
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        
        # Add to Existing Group submenu
        if self.tabs.tabBar.groups:
            group_menu = menu.addMenu("Add to Group")
            for group_name in self.tabs.tabBar.groups:
                action = group_menu.addAction(group_name)
                action.triggered.connect(
                    lambda x, g=group_name: self.add_new_tab_to_group(g)
                )
        
        # Create New Group option
        menu.addSeparator()
        new_group_action = menu.addAction("Create New Group...")
        new_group_action.triggered.connect(self.create_new_group_with_tab)
        
        # Get the button that triggered this
        button = self.findChild(QToolBar).widgetForAction(
            [a for a in self.findChild(QToolBar).actions() 
             if a.text() == 'New Tab'][0]
        )
        menu.exec(button.mapToGlobal(QPoint(0, button.height())))

    def add_new_tab_to_group(self, group_name):
        """Add a new tab to a specific group"""
        index = self.add_new_tab()
        self.tabs.addTabToGroup(index, group_name)

    def create_new_group_with_tab(self):
        """Create a new group and add a tab to it"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Tab Group")
        layout = QVBoxLayout(dialog)
        
        # Group name input
        name_label = QLabel("Group Name:")
        layout.addWidget(name_label)
        name_input = QLineEdit()
        layout.addWidget(name_input)
        
        # Color selection (simplified)
        colors = [
            ("Red", QColor(230, 200, 200)),
            ("Green", QColor(200, 230, 200)),
            ("Blue", QColor(200, 200, 230)),
            ("Yellow", QColor(230, 230, 200)),
            ("Purple", QColor(230, 200, 230))
        ]
        
        color_label = QLabel("Group Color:")
        layout.addWidget(color_label)
        color_combo = QComboBox()
        for color_name, _ in colors:
            color_combo.addItem(color_name)
        layout.addWidget(color_combo)
        
        # Buttons
        buttons = QHBoxLayout()
        create_btn = QPushButton("Create")
        cancel_btn = QPushButton("Cancel")
        buttons.addWidget(create_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        create_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            group_name = name_input.text()
            if group_name:
                color = colors[color_combo.currentIndex()][1]
                self.tabs.createTabGroup(group_name, color)
                self.add_new_tab_to_group(group_name)

    def update_tab_loading(self, index, progress):
        """Update loading state and progress for tab"""
        if progress < 100:
            if index not in self.loading_tabs:
                self.loading_tabs.add(index)
                self.tabs.setTabIcon(index, self.get_icon('loading'))
        else:
            self.loading_tabs.discard(index)
            tab = self.tabs.widget(index)
            if hasattr(tab, 'icon'):
                self.tabs.setTabIcon(index, tab.icon())
            else:
                self.tabs.setTabIcon(index, QIcon())
        
        # Update progress bar if it's the current tab
        if index == self.tabs.currentIndex():
            self.progress_bar.setValue(progress)

    def update_tab_title(self, browser, title):
        """Update tab title when page title changes"""
        index = self.tabs.indexOf(browser)
        if index >= 0:
            self.tabs.setTabText(index, title)
            # Re-apply group styling if needed
            self.tabs.update_tab_appearances(index)

    def create_test_tabs(self):
        """Create initial test tabs"""
        # Create and load test tabs
        self.tabs.create_test_tabs()
        
        # Apply dark mode to all tabs
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'page'):
                tab.page().setBackgroundColor(QColor(33, 33, 33))
                self.inject_dark_mode()

    def show(self):
        super().show()
        # Create test tabs after window is shown
        QTimer.singleShot(100, self.create_test_tabs)

    def inject_dark_mode_to_tab(self, tab):
        """Inject dark mode CSS into a specific tab"""
        if not hasattr(tab, 'page'):
            return
        
        # Set dark background immediately
        tab.setStyleSheet("background-color: #212121;")
        tab.page().setBackgroundColor(QColor("#212121"))
        
        # Inject immediate dark mode
        immediate_style = """
        (function() {
            // Immediate style injection
            const style = document.createElement('style');
            style.textContent = `
                /* Base dark mode */
                html, body, iframe, div { 
                    background-color: #212121 !important; 
                }
                
                /* Ad containers */
                [class*="ad-"], [class*="advertisement"], [id*="ad-"],
                [class*="sponsor"], [id*="sponsor"],
                iframe[src*="ad"], iframe[id*="ad"], 
                div[class*="ad"], div[id*="ad"] {
                    background-color: #2b2b2b !important;
                    color: #999999 !important;
                    border: 1px solid #333333 !important;
                }
            `;
            document.documentElement.appendChild(style);
            
            // Monitor for dynamic content
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) {  // Element node
                            if (node.tagName === 'IFRAME' || 
                                node.className.includes('ad') ||
                                node.id.includes('ad')) {
                                node.style.backgroundColor = '#2b2b2b';
                                node.style.border = '1px solid #333333';
                            }
                        }
                    });
                });
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        })();
        """
        tab.page().runJavaScript(immediate_style)
        
        # Create and inject the main dark mode script
        script = QWebEngineScript()
        script.setName("dark_mode")
        script.setSourceCode(apply_dark_mode_js())
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
        script.setRunsOnSubFrames(True)
        
        tab.page().scripts().insert(script)

    def setup_dev_tools(self):
        """Setup developer tools"""
        # Add dev tools shortcut
        dev_tools_action = QAction("Developer Tools", self)
        dev_tools_action.setShortcut("F12")
        dev_tools_action.triggered.connect(self.toggle_dev_tools)
        self.addAction(dev_tools_action)
        
        # Create dev tools dock widget with dark theme
        self.dev_tools_dock = QDockWidget("Developer Tools", self)
        self.dev_tools_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.dev_tools_dock.setMinimumHeight(300)  # Set minimum height
        
        # Create dev tools view with dark theme
        self.dev_tools = QWebEngineView()
        self.dev_tools.setStyleSheet("""
            QWebEngineView {
                background: #1e1e1e;
            }
        """)
        
        # Create container widget for proper sizing
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.dev_tools)
        
        self.dev_tools_dock.setWidget(container)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dev_tools_dock)
        
        # Set initial size to 40% of window height
        self.dev_tools_dock.hide()

    def toggle_dev_tools(self):
        """Toggle developer tools for current tab"""
        current_tab = self.tabs.currentWidget()
        if hasattr(current_tab, 'page'):
            if not self.dev_tools_dock.isVisible():
                # Set size when showing
                self.dev_tools_dock.show()
                self.resizeDocks(
                    [self.dev_tools_dock],
                    [int(self.height() * 0.4)],
                    Qt.Orientation.Vertical
                )
            current_tab.page().setDevToolsPage(self.dev_tools.page())
            
            # Apply dark theme to dev tools
            js = """
            (function() {
                if (!document.documentElement.getAttribute('devtools-theme-applied')) {
                    const style = document.createElement('style');
                    style.textContent = `
                        :root {
                            --background-color: #1e1e1e !important;
                            --toolbar-bg-color: #2d2d2d !important;
                            --text-color: #e0e0e0 !important;
                        }
                        body {
                            background-color: var(--background-color) !important;
                            color: var(--text-color) !important;
                        }
                        .inspector-view-toolbar {
                            background-color: var(--toolbar-bg-color) !important;
                        }
                    `;
                    document.documentElement.appendChild(style);
                    document.documentElement.setAttribute('devtools-theme-applied', 'true');
                }
            })();
            """
            self.dev_tools.page().runJavaScript(js)

    def show_web_context_menu(self, browser, pos):
        """Show custom context menu for web view"""
        menu = QMenu(self)
        
        # Add standard actions
        menu.addAction("Back", browser.back)
        menu.addAction("Forward", browser.forward)
        menu.addAction("Reload", browser.reload)
        menu.addSeparator()
        
        # Add inspect element option
        inspect_action = menu.addAction("Inspect Element")
        inspect_action.triggered.connect(lambda: self.inspect_element_at(browser, pos))
        
        menu.exec(browser.mapToGlobal(pos))

    def inspect_element_at(self, browser, pos):
        """Open dev tools and inspect element at position"""
        if not self.dev_tools_dock.isVisible():
            self.dev_tools_dock.show()
        browser.page().setDevToolsPage(self.dev_tools.page())
        # Use JavaScript to inspect element since inspectElement is not available
        js = """
        (function() {
            let element = document.elementFromPoint(%d, %d);
            if (element) {
                inspect(element);
            }
        })();
        """ % (pos.x(), pos.y())
        browser.page().runJavaScript(js)

    def setup_workspaces(self):
        """Setup workspace selection toolbar"""
        workspace_toolbar = QToolBar("Workspaces")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, workspace_toolbar)
        
        # Add workspace selector
        self.workspace_selector = QComboBox()
        self.workspace_selector.setMinimumWidth(150)
        self.workspace_selector.setStyleSheet("""
            QComboBox {
                background: #2e3440;
                color: #d8dee9;
                border: 1px solid #4c566a;
                padding: 4px;
                border-radius: 4px;
                margin: 2px 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(:/icons/down-arrow.png);
                width: 12px;
                height: 12px;
            }
        """)
        self.workspace_selector.currentTextChanged.connect(self.switch_workspace)
        workspace_toolbar.addWidget(self.workspace_selector)
        
        # Add workspace management buttons
        new_workspace = workspace_toolbar.addAction("New")
        new_workspace.triggered.connect(self.create_workspace)
        rename_workspace = workspace_toolbar.addAction("Rename")
        rename_workspace.triggered.connect(self.rename_workspace)
        delete_workspace = workspace_toolbar.addAction("Delete")
        delete_workspace.triggered.connect(self.delete_workspace)

    def create_workspace(self, name=None):
        """Create a new workspace"""
        if name is None:
            count = len(self.workspaces) + 1
            name = f"Workspace {count}"
            
        workspace = {
            'name': name,
            'tabs': [],
            'groups': {},
            'active_tab': 0
        }
        self.workspaces[name] = workspace
        self.workspace_selector.addItem(name)
        
        if not self.current_workspace:
            self.switch_workspace(name)

    def switch_workspace(self, name):
        """Switch to a different workspace"""
        if name not in self.workspaces:
            return
            
        # Save current workspace state
        if self.current_workspace:
            self.save_workspace_state(self.current_workspace)
            
        # Switch to new workspace
        self.current_workspace = name
        self.restore_workspace_state(name)
        self.workspace_selector.setCurrentText(name)
    def rename_workspace(self, name):
        """Rename a workspace"""
        if name not in self.workspaces:
            return
        self.workspaces[name]['name'] = name
        self.workspace_selector.setItemText(self.workspace_selector.currentIndex(), name)

    def delete_workspace(self, name):
        """Delete a workspace"""
        if name not in self.workspaces:
            return
        del self.workspaces[name]
        self.workspace_selector.removeItem(self.workspace_selector.currentIndex())
        if self.current_workspace == name:
            self.switch_workspace(self.workspace_selector.currentText())

    def save_workspace_state(self, name):
        """Save current tab state to workspace"""
        workspace = self.workspaces[name]
        workspace['tabs'] = []
        workspace['groups'] = self.tabs.groups.copy()
        
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'url'):
                workspace['tabs'].append({
                    'url': tab.url().toString(),
                    'title': self.tabs.tabText(i),
                    'group': self.tabs.tab_groups.get(i)
                })
        
        workspace['active_tab'] = self.tabs.currentIndex()

    def restore_workspace_state(self, name):
        """Restore workspace state"""
        workspace = self.workspaces[name]
        
        # Clear current tabs
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)
            
        # Restore groups
        self.tabs.groups = workspace['groups'].copy()
        
        # Restore tabs
        for tab_state in workspace['tabs']:
            idx = self.add_new_tab(QUrl(tab_state['url']), tab_state['title'])
            if tab_state['group']:
                self.tabs.addTabToGroup(idx, tab_state['group'])
                
        if workspace['tabs']:
            self.tabs.setCurrentIndex(workspace['active_tab'])
    def setup_workspace_toolbar(self):
        """Setup workspace selection toolbar"""
        workspace_toolbar = QToolBar("Workspaces")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, workspace_toolbar)

    def update_tab_icon(self, browser):
        """Update tab icon when page icon changes"""
        index = self.tabs.indexOf(browser)
        if index >= 0:
            icon = browser.icon()
            if not icon.isNull():
                self.tabs.setTabIcon(index, icon)

    def show_extensions(self):
        """Show extensions management dialog"""
        from .extensions.ui import ExtensionManager
        dialog = ExtensionManager(self)
        dialog.exec()

    def event(self, event):
        """Handle touch events for gestures"""
        if event.type() == QEvent.Type.TouchBegin:
            points = event.points()
            if points:
                self.touch_start = points[0].position()
                self.touch_tracking = True
                self.touch_timer.start()
            return True
            
        elif event.type() == QEvent.Type.TouchUpdate:
            if self.touch_tracking and self.touch_start:
                points = event.points()
                if points:
                    pos = points[0].position()
                    delta = pos - self.touch_start
                    
                    # Check for three-finger swipe up
                    if len(points) == 3 and delta.y() < -100:
                        self.tabs.show_spread()
                        self.touch_tracking = False
                        self.touch_timer.stop()
                        return True
                    
                    # Check for two-finger pinch
                    if len(points) == 2:
                        p1 = points[0].position()
                        p2 = points[1].position()
                        current_dist = (p1 - p2).manhattanLength()
                        
                        if hasattr(self, 'pinch_start_dist'):
                            if current_dist > self.pinch_start_dist * 1.5:
                                # Pinch out - show tab spread
                                self.tabs.show_spread()
                                self.touch_tracking = False
                                self.touch_timer.stop()
                                return True
                        else:
                            self.pinch_start_dist = current_dist
            return True
            
        elif event.type() == QEvent.Type.TouchEnd:
            self.touch_tracking = False
            self.touch_timer.stop()
            if hasattr(self, 'pinch_start_dist'):
                del self.pinch_start_dist
            return True
            
        return super().event(event)

    def _handle_long_press(self):
        """Handle long press gesture to show ring menu"""
        if self.touch_tracking and self.touch_start:
            # Show ring menu at touch point
            from .tabs.ring_menu import RingMenu
            menu = RingMenu(self)
            
            # Add common actions
            menu.add_action("New Tab", self.add_new_tab)
            menu.add_action("Close Tab", lambda: self.close_tab(self.tabs.currentIndex()))
            menu.add_action("Tab Overview", self.tabs.show_spread)
            menu.add_action("Bookmark", self.bookmark_current_tab)
            menu.add_action("History", self.show_history)
            menu.add_action("Settings", self.show_settings)
            
            # Show menu at touch point
            menu.show_at(self.mapToGlobal(self.touch_start.toPoint()))
            self.touch_tracking = False

    def bookmark_current_tab(self):
        """Add current tab to bookmarks"""
        current = self.current_tab()
        if hasattr(current, 'url'):
            self.bookmark_widget.add_bookmark(
                current.url().toString(),
                self.tabs.tabText(self.tabs.currentIndex())
            )

    def toggle_style_panel(self):
        """Toggle the style adjuster panel"""
        if self.style_dock.isVisible():
            self.style_dock.hide()
        else:
            self.style_dock.show()
            # Apply current style to the page
            self.style_panel._update_style()

class EnhancedURLBar(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Search tabs, history, or enter address")
        self.suggestions_list = None
        self.setup_suggestions()
        self.search_mode = False  # Track if we're in search mode
        
    def setup_suggestions(self):
        """Create and set up suggestions list"""
        self.suggestions_list = QListWidget(self)
        self.suggestions_list.setWindowFlags(Qt.WindowType.Popup)
        self.suggestions_list.setFocusProxy(self)
        self.suggestions_list.setMouseTracking(True)
        self.suggestions_list.itemClicked.connect(self.parent().use_suggestion)
        self.suggestions_list.hide()

        # Add category labels to suggestions
        self.suggestions_list.setStyleSheet("""
            QListWidget::item[category="tab"] { 
                color: #88c0d0; 
                border-left: 3px solid #88c0d0;
            }
            QListWidget::item[category="history"] { 
                color: #a3be8c;
                border-left: 3px solid #a3be8c;
            }
            QListWidget::item[category="search"] { 
                color: #b48ead;
                border-left: 3px solid #b48ead;
            }
        """)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.suggestions_list.isVisible():
                self.suggestions_list.hide()
                return
            self.clear()
            return
            
        if event.key() == Qt.Key.Key_Tab:
            # Quick tab switch mode
            self.search_mode = True
            self.setText("tab: " + self.text())
            event.accept()
            return

        super().keyPressEvent(event)

class SecurityPanel(QWidget):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        layout = QVBoxLayout(self)
        
        # Security Mode Group
        mode_group = QGroupBox("Security Mode")
        mode_layout = QVBoxLayout()
        
        # Dev Mode Toggle
        self.dev_mode = QCheckBox("Developer Mode (Relaxed Security)")
        self.dev_mode.setChecked(self.settings.get('security', 'dev_mode'))
        self.dev_mode.stateChanged.connect(
            lambda state: self.settings.set('security', 'dev_mode', bool(state))
        )
        mode_layout.addWidget(self.dev_mode)
        
        # Warning Label
        warning_label = QLabel(
            "⚠️ Developer Mode disables certain security features.\n"
            "Only use during development!"
        )
        warning_label.setStyleSheet("color: #ebcb8b;")  # Warning yellow
        mode_layout.addWidget(warning_label)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Security Features Group
        features_group = QGroupBox("Security Features")
        features_layout = QVBoxLayout()
        
        # CORS Settings
        self.strict_cors = QCheckBox("Strict CORS Policy")
        self.strict_cors.setChecked(self.settings.get('security', 'strict_cors'))
        self.strict_cors.stateChanged.connect(
            lambda state: self.settings.set('security', 'strict_cors', bool(state))
        )
        features_layout.addWidget(self.strict_cors)
        
        # Mixed Content
        self.block_mixed = QCheckBox("Block Mixed Content")
        self.block_mixed.setChecked(self.settings.get('security', 'block_mixed_content'))
        self.block_mixed.stateChanged.connect(
            lambda state: self.settings.set('security', 'block_mixed_content', bool(state))
        )
        features_layout.addWidget(self.block_mixed)
        
        # Dangerous Ports
        self.block_ports = QCheckBox("Block Dangerous Ports")
        self.block_ports.setChecked(self.settings.get('security', 'block_dangerous_ports'))
        self.block_ports.stateChanged.connect(
            lambda state: self.settings.set('security', 'block_dangerous_ports', bool(state))
        )
        features_layout.addWidget(self.block_ports)
        
        # Dangerous Schemes
        self.block_schemes = QCheckBox("Block Dangerous URL Schemes")
        self.block_schemes.setChecked(self.settings.get('security', 'block_dangerous_schemes'))
        self.block_schemes.stateChanged.connect(
            lambda state: self.settings.set('security', 'block_dangerous_schemes', bool(state))
        )
        features_layout.addWidget(self.block_schemes)
        
        features_group.setLayout(features_layout)
        layout.addWidget(features_group)
        
        # Status Indicator
        self.status_label = QLabel()
        self.update_status_label()
        layout.addWidget(self.status_label)
        
        # Connect dev mode to update status
        self.dev_mode.stateChanged.connect(self.update_status_label)
        
        layout.addStretch()
        
    def update_status_label(self):
        if self.dev_mode.isChecked():
            self.status_label.setText("🔓 Developer Mode Active - Security Features Relaxed")
            self.status_label.setStyleSheet("color: #bf616a;")  # Red for warning
        else:
            self.status_label.setText("🔒 Normal Security Mode - Full Protection Active")
            self.status_label.setStyleSheet("color: #a3be8c;")  # Green for secure

def main():
    # Redirect web-related output to a log file
    import os
    import sys
    web_log_path = os.path.expanduser('~/.sledge/web.log')
    os.makedirs(os.path.dirname(web_log_path), exist_ok=True)
    web_log = open(web_log_path, 'w')
    sys.stderr = web_log  # Redirect stderr (where most web errors go) to file
    
    print("\n" + "="*50)
    print("🚀 [SLEDGE DEBUG] 1. Entering main()")
    app = QApplication(sys.argv)
    print("🚀 [SLEDGE DEBUG] 2. Created QApplication")
    browser = SledgeBrowser()
    print("🚀 [SLEDGE DEBUG] 3. Created SledgeBrowser")
    browser.show()
    print("🚀 [SLEDGE DEBUG] 4. Called browser.show()")
    print("="*50 + "\n")
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
