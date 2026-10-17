from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

# When True, all window.open() / target=_blank calls open in a new tab.
# When False (default), only genuine new-tab links open in a new tab;
# popup/dialog windows (e.g. video player popups) are blocked so the
# video plays inside the embed instead of jumping to a new page.
POPUPS_OPEN_NEW_TAB: bool = False


class WebView(QWebEngineView):
    """Custom web view with enhanced features."""

    titleChanged = pyqtSignal(str)
    urlChanged = pyqtSignal(QUrl)

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.parent = parent

        # Create page with our profile
        self.setPage(QWebEnginePage(self.profile, self))

        # Per-page settings
        settings = self.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        # View-level settings
        settings = self.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True
        )
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, True)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.XSSAuditingEnabled, False)

        # Profile-level settings (cache / cookies)
        p = self.page().profile()
        p.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        p.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        p.setPersistentStoragePath("./cache")
        p.setCachePath("./cache")

        # Connect signals
        self.page().titleChanged.connect(self.titleChanged)
        self.page().urlChanged.connect(self.urlChanged)
        self.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, ok: bool):
        if not ok:
            return
        url = self.url()
        if url.scheme() in ("about", "chrome", "qrc"):
            return

        # Patch VideoJS and native <video> elements for better HLS / playback compat
        js = """
        (function () {
            // VideoJS configuration
            if (window.videojs) {
                videojs.options.autoplay = false;
                videojs.options.controls = true;
                videojs.options.html5 = {
                    vhs: {
                        overrideNative: true,
                        fastQualityChange: true,
                        useDevicePixelRatio: true,
                        withCredentials: false,
                    },
                    nativeAudioTracks: false,
                    nativeVideoTracks: false,
                    nativeTextTracks: false,
                };

                document.querySelectorAll('.video-js:not([data-sledge])').forEach(function (el) {
                    el.setAttribute('data-sledge', '1');
                    videojs(el, {
                        techOrder: ['html5'],
                        playbackRates: [0.5, 1, 1.5, 2],
                        responsive: true,
                        fluid: true,
                    });
                });

                videojs.hook('error', function (player) {
                    var err = player.error();
                    if (err && err.code === 4) {
                        var sources = player.currentSources();
                        if (sources && sources.length > 0) {
                            var src = sources[0].src;
                            if (src) {
                                player.src(src.includes('.m3u8')
                                    ? src.replace('.m3u8', '.mp4')
                                    : src.replace('.mp4', '.m3u8'));
                                player.play();
                            }
                        }
                    }
                });
            }

            // Native <video> fixups
            document.querySelectorAll('video').forEach(function (v) {
                v.setAttribute('playsinline', '');
                v.setAttribute('webkit-playsinline', '');
                if (!v.dataset.sledge) {
                    v.dataset.sledge = '1';
                    v.addEventListener('error', function (e) {
                        var t = e.target;
                        if (t.error && t.error.code === 4 && t.src) {
                            t.src = t.src.includes('.m3u8')
                                ? t.src.replace('.m3u8', '.mp4')
                                : t.src.replace('.mp4', '.m3u8');
                            t.load();
                        }
                    });
                }
            });
        })();
        """
        self.page().runJavaScript(js)

    def createWindow(self, window_type):
        Tab = QWebEnginePage.WebWindowType.WebBrowserTab
        BgTab = QWebEnginePage.WebWindowType.WebBrowserBackgroundTab

        if window_type in (Tab, BgTab):
            # Genuine new-tab request (target="_blank" link) — always open.
            if self.parent and hasattr(self.parent, "add_new_tab"):
                return self.parent.add_new_tab()
        elif POPUPS_OPEN_NEW_TAB:
            # Popup/dialog window (video player, window.open()) — only open
            # as a new tab when the setting is explicitly enabled.
            if self.parent and hasattr(self.parent, "add_new_tab"):
                return self.parent.add_new_tab()
        # Default: return None → Qt keeps the popup inside the embed.
        return None
