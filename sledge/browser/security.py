import re

from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import sledge.browser.webview as _webview_mod
from sledge.browser.adblock import AdBlocker

# Ports that are blocked as potentially dangerous (same list browsers use)
DANGEROUS_PORTS = {
    1,
    2,
    3,
    7,
    9,
    11,
    13,
    15,
    17,
    19,
    20,
    21,
    22,
    23,
    25,
    37,
    42,
    43,
    53,
    77,
    79,
    87,
    95,
    101,
    102,
    103,
    104,
    109,
    110,
    111,
    113,
    115,
    117,
    119,
    123,
    135,
    139,
    143,
    179,
    389,
    465,
    512,
    513,
    514,
    515,
    526,
    530,
    531,
    532,
    540,
    548,
    556,
    563,
    587,
    601,
    636,
    993,
    995,
    2049,
    3659,
    4045,
    6000,
    6665,
    6666,
    6667,
    6668,
    6669,
}

# Domains that serve video/media and need Referer/Origin spoofing to work.
# Maps domain substring → the Origin value the media server expects.
VIDEO_DOMAINS: dict[str, bytes] = {
    "cizgifilmlerizle.com": b"https://cizgifilmlerizle.com",
    "watchanimesub.net": b"https://embed.watchanimesub.net",
    "wcofun.net": b"https://www.wcofun.net",
}


class RequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Main request interceptor: ad blocking, video CORS headers, dangerous-port blocking."""

    def __init__(self, browser=None):
        super().__init__()
        self.browser = browser

        # Feature flags — toggled by SecurityPanel
        self.block_dangerous_ports = True
        self.block_mixed_content = True
        self.block_ads = True

        # Lazy-initialised; SecurityPanel can reach in and disable/enable it.
        self.adblocker = AdBlocker()
        self.adblocker.load_async()

    # ------------------------------------------------------------------
    # QWebEngineUrlRequestInterceptor interface
    # ------------------------------------------------------------------

    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        first_party = info.firstPartyUrl().toString()

        # 1. Ad / tracker blocking
        if self.block_ads and self.adblocker.should_block(url, first_party):
            info.block(True)
            return

        # 2. Block dangerous ports
        if self.block_dangerous_ports:
            port = info.requestUrl().port(-1)
            if port in DANGEROUS_PORTS:
                info.block(True)
                return

        # 3. Block mixed content (http resource on https page)
        if self.block_mixed_content:
            if (
                info.requestUrl().scheme() == "http"
                and info.firstPartyUrl().scheme() == "https"
            ):
                info.block(True)
                return

        # 4. Video / media server header fixups
        #    Some media servers validate Origin/Referer and reject requests
        #    that don't match their expected value.  We spoof them here.
        matched_origin: bytes | None = None
        for domain, origin in VIDEO_DOMAINS.items():
            if domain in url:
                matched_origin = origin
                break

        if matched_origin:
            info.setHttpHeader(b"Origin", matched_origin)
            referer = matched_origin + b"/"
            info.setHttpHeader(b"Referer", referer)
            info.setHttpHeader(b"Sec-Fetch-Site", b"cross-site")
            info.setHttpHeader(b"Sec-Fetch-Mode", b"cors")
            info.setHttpHeader(b"Sec-Fetch-Dest", b"empty")
            info.setHttpHeader(b"Accept", b"*/*")
            info.setHttpHeader(b"Accept-Language", b"en-US,en;q=0.9")

        # 5. getvid URL parameter cleanup
        if "getvid" in url and "?" in url:
            base, params = url.split("?", 1)
            params = re.sub(r"([^=&])%([^=&])", r"\1\2", params)
            info.redirect(QUrl(f"{base}?{params}"))

        # 6. Security response-hint headers (best-effort; only affects
        #    requests where Qt lets us set them — typically our own origins)
        info.setHttpHeader(b"X-Content-Type-Options", b"nosniff")
        info.setHttpHeader(b"Sec-CH-Prefers-Color-Scheme", b"dark")


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------


class SecurityPanel(QWidget):
    """Security settings panel."""

    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        root = QVBoxLayout(self)

        # ── Security ────────────────────────────────────────────────────
        sec_group = QGroupBox("Security Settings")
        sec_layout = QVBoxLayout(sec_group)

        self.strict_cors = QCheckBox("Strict CORS Policy")
        self.strict_cors.setChecked(True)
        self.strict_cors.toggled.connect(self._update_security)
        sec_layout.addWidget(self.strict_cors)

        self.block_mixed = QCheckBox("Block Mixed Content")
        self.block_mixed.setChecked(True)
        self.block_mixed.toggled.connect(self._update_security)
        sec_layout.addWidget(self.block_mixed)

        self.block_dangerous = QCheckBox("Block Dangerous Ports")
        self.block_dangerous.setChecked(True)
        self.block_dangerous.toggled.connect(self._update_security)
        sec_layout.addWidget(self.block_dangerous)

        root.addWidget(sec_group)

        # ── Ad Blocking ─────────────────────────────────────────────────
        ad_group = QGroupBox("Ad & Tracker Blocking")
        ad_layout = QVBoxLayout(ad_group)

        self.block_ads = QCheckBox("Block Ads & Trackers")
        self.block_ads.setChecked(True)
        self.block_ads.toggled.connect(self._update_security)
        ad_layout.addWidget(self.block_ads)

        interceptor = self._interceptor()
        if interceptor and not interceptor.adblocker.available:
            warn = QLabel(
                "⚠ 'adblock' package not installed — ad blocking unavailable."
            )
            ad_layout.addWidget(warn)
            self.block_ads.setEnabled(False)

        root.addWidget(ad_group)

        # ── Video ───────────────────────────────────────────────────────
        video_group = QGroupBox("Video Settings")
        video_layout = QVBoxLayout(video_group)

        self.popups_new_tab = QCheckBox("Open video popups in new tab")
        self.popups_new_tab.setToolTip(
            "Off (default): video players open inside the embed (recommended).\n"
            "On: window.open() popups open as a new browser tab."
        )
        self.popups_new_tab.setChecked(_webview_mod.POPUPS_OPEN_NEW_TAB)
        self.popups_new_tab.toggled.connect(self._update_video)
        video_layout.addWidget(self.popups_new_tab)

        root.addWidget(video_group)

        # ── Network ─────────────────────────────────────────────────────
        net_group = QGroupBox("Network Settings")
        net_layout = QVBoxLayout(net_group)

        self.dns_prefetch = QCheckBox("Enable DNS Prefetching")
        self.dns_prefetch.setChecked(True)
        self.dns_prefetch.toggled.connect(self._update_network)
        net_layout.addWidget(self.dns_prefetch)

        self.disk_cache = QCheckBox("Enable Disk Cache")
        self.disk_cache.setChecked(True)
        self.disk_cache.toggled.connect(self._update_network)
        net_layout.addWidget(self.disk_cache)

        root.addWidget(net_group)

        # ── Privacy ─────────────────────────────────────────────────────
        priv_group = QGroupBox("Privacy Settings")
        priv_layout = QVBoxLayout(priv_group)

        self.do_not_track = QCheckBox("Send Do Not Track")
        self.do_not_track.setChecked(True)
        self.do_not_track.toggled.connect(self._update_privacy)
        priv_layout.addWidget(self.do_not_track)

        self.block_third_party = QCheckBox("Block Third-Party Cookies")
        self.block_third_party.setChecked(True)
        self.block_third_party.toggled.connect(self._update_privacy)
        priv_layout.addWidget(self.block_third_party)

        root.addWidget(priv_group)
        root.addStretch()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _interceptor(self) -> RequestInterceptor | None:
        try:
            return self.browser.profile.urlRequestInterceptor()
        except Exception:
            return None

    def _update_video(self):
        _webview_mod.POPUPS_OPEN_NEW_TAB = self.popups_new_tab.isChecked()

    def _update_security(self):
        interceptor = self._interceptor()
        if interceptor:
            interceptor.block_mixed_content = self.block_mixed.isChecked()
            interceptor.block_dangerous_ports = self.block_dangerous.isChecked()
            interceptor.block_ads = self.block_ads.isChecked()

    def _update_network(self):
        from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings

        profile = self.browser.profile
        settings = profile.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.DnsPrefetchEnabled,
            self.dns_prefetch.isChecked(),
        )
        cache_type = (
            QWebEngineProfile.HttpCacheType.DiskHttpCache
            if self.disk_cache.isChecked()
            else QWebEngineProfile.HttpCacheType.MemoryHttpCache
        )
        profile.setHttpCacheType(cache_type)

    def _update_privacy(self):
        from PyQt6.QtWebEngineCore import QWebEngineProfile

        profile = self.browser.profile
        ua = profile.httpUserAgent()
        if self.do_not_track.isChecked():
            if "DNT=1" not in ua:
                ua += " DNT=1"
        else:
            ua = ua.replace("DNT=1", "").strip()
        profile.setHttpUserAgent(ua)

        policy = (
            QWebEngineProfile.PersistentCookiesPolicy.BlockThirdPartyCookies
            if self.block_third_party.isChecked()
            else QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        profile.setPersistentCookiesPolicy(policy)
