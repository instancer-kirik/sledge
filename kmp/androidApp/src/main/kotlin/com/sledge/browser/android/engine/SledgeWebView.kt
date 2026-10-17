package com.sledge.browser.android.engine

import android.annotation.SuppressLint
import android.content.Context
import android.os.Build
import android.util.Base64
import android.webkit.JavascriptInterface
import android.webkit.WebSettings
import android.webkit.WebView
import java.io.File
import androidx.webkit.WebSettingsCompat
import androidx.webkit.WebViewFeature
import com.sledge.browser.adblock.AdBlocker
import com.sledge.browser.engine.RequestInterceptor
import com.sledge.browser.model.BrowserSettings

/**
 * A [WebView] pre-configured for the Sledge browser.
 *
 * Responsibilities:
 * - Applies all required [WebSettings] (JS, DOM storage, mixed-content policy, UA, etc.)
 * - Installs [SledgeWebViewClient] and [SledgeWebChromeClient]
 * - Normalises bare URLs before loading
 * - Injects VideoJS + native-video patching JS on every page finish
 */
@SuppressLint("SetJavaScriptEnabled")
class SledgeWebView(
    context: Context,
    settings: BrowserSettings = BrowserSettings(),
    adBlocker: AdBlocker = AdBlocker(),
    private val brave: BraveAdBlock? = null,
    onCreateTab: (initialUrl: String?) -> WebView? = { null },
) : WebView(context) {

    private var browserSettings: BrowserSettings = settings

    val sledgeWebViewClient: SledgeWebViewClient
    val sledgeWebChromeClient: SledgeWebChromeClient

    /** Assigned by the UI. Read when a navigation starts, so later updates are seen. */
    var onPageStartedCallback: ((url: String) -> Unit)? = null

    /** Assigned by the UI. Video patching always runs before this. */
    var onPageFinishedCallback: ((url: String, title: String?) -> Unit)? = null

    /** Assigned by the UI. Fired from [android.webkit.DownloadListener]. */
    var onDownload: ((
        url: String,
        userAgent: String,
        contentDisposition: String,
        mimeType: String,
        contentLength: Long,
    ) -> Unit)? = null

    private val blobBridge = BlobDownloadBridge()

    init {
        // ---- WebView settings ----
        with(this.settings) {
            javaScriptEnabled = settings.javascriptEnabled
            domStorageEnabled = true
            databaseEnabled = true
            // Asset and resource URLs (file:///android_asset, file:///android_res)
            // still load as the main frame. This only closes filesystem access.
            allowFileAccess = false
            @Suppress("DEPRECATION")
            allowFileAccessFromFileURLs = false
            @Suppress("DEPRECATION")
            allowUniversalAccessFromFileURLs = false
            setSupportZoom(true)
            builtInZoomControls = true
            displayZoomControls = false
            loadWithOverviewMode = true
            useWideViewPort = true
            mediaPlaybackRequiresUserGesture = false
            javaScriptCanOpenWindowsAutomatically = true
            setSupportMultipleWindows(true)
            mixedContentMode = if (settings.blockMixedContent) {
                WebSettings.MIXED_CONTENT_NEVER_ALLOW
            } else {
                WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            }
            settings.customUserAgent?.let { userAgentString = it }
            cacheMode = WebSettings.LOAD_DEFAULT
        }

        // ---- Hardware acceleration (set at view level for good measure) ----
        setLayerType(LAYER_TYPE_HARDWARE, null)
        setBackgroundColor(android.graphics.Color.parseColor("#0C0C0E"))

        // ---- Clients ----
        val interceptor = RequestInterceptor(adBlocker, browserSettings)

        sledgeWebViewClient = SledgeWebViewClient(interceptor, browserSettings, brave).also { client ->
            client.onPageStarted = { url -> onPageStartedCallback?.invoke(url) }
            client.onPageFinished = { url, title ->
                injectVideoJs()
                brave?.injectCosmetics(this, url)
                onPageFinishedCallback?.invoke(url, title)
            }
        }

        sledgeWebChromeClient = SledgeWebChromeClient(
            onCreateTab = onCreateTab,
            popupsOpenNewTab = { !browserSettings.popupsOpenNewTab },
        )

        applyAlgorithmicDarkening(browserSettings.darkMode)

        webViewClient = sledgeWebViewClient
        webChromeClient = sledgeWebChromeClient
        addJavascriptInterface(blobBridge, "SledgeBlob")
        setDownloadListener { url, userAgent, contentDisposition, mimeType, contentLength ->
            onDownload?.invoke(url, userAgent, contentDisposition, mimeType, contentLength)
        }
    }

    /**
     * Streams a `blob:` URL into [dest] in chunks small enough for the Javascript bridge.
     * [onResult] runs on the UI thread. Null means the read failed and [dest] was removed.
     */
    fun readBlob(url: String, dest: File, onResult: (File?) -> Unit) {
        blobBridge.begin(dest) { file -> post { onResult(file) } }
        val quoted = org.json.JSONObject.quote(url)
        evaluateJavascript(
            """
            (function() {
              var chunkBytes = 131072;
              function fail() { SledgeBlob.onFail(); }
              fetch($quoted).then(function(r) { return r.blob(); }).then(function(blob) {
                var total = Math.ceil(blob.size / chunkBytes);
                if (total === 0) { SledgeBlob.onDone(); return; }
                function send(i) {
                  var slice = blob.slice(i * chunkBytes, Math.min(blob.size, (i + 1) * chunkBytes));
                  var reader = new FileReader();
                  reader.onloadend = function() {
                    var text = reader.result || '';
                    var comma = text.indexOf(',');
                    if (comma < 0) { fail(); return; }
                    SledgeBlob.onChunk(i, total, text.substring(comma + 1));
                    if (i + 1 < total) send(i + 1);
                  };
                  reader.onerror = fail;
                  reader.readAsDataURL(slice);
                }
                send(0);
              }).catch(fail);
            })();
            """.trimIndent(),
            null,
        )
    }

    override fun onLayout(changed: Boolean, left: Int, top: Int, right: Int, bottom: Int) {
        super.onLayout(changed, left, top, right, bottom)
        // WebView claims the whole view for gesture exclusion, which swallows the
        // system back swipe plus the home and recents gestures.
        post {
            if (systemGestureExclusionRects.isNotEmpty()) {
                systemGestureExclusionRects = emptyList()
            }
        }
    }

    // ---------------------------------------------------------------------------------
    // Public API
    // ---------------------------------------------------------------------------------

    /**
     * Loads [url], prepending `https://` when no scheme is present.
     */
    override fun loadUrl(url: String) {
        val next = normalise(url) ?: return
        super.loadUrl(next)
    }

    /**
     * Applies a new settings snapshot to this live WebView and its request interceptor.
     * Callers should reload if JavaScript or dark mode changed.
     */
    fun applySettings(updated: BrowserSettings) {
        browserSettings = updated
        sledgeWebViewClient.updateSettings(updated)
        with(this.settings) {
            javaScriptEnabled = updated.javascriptEnabled
            mixedContentMode = if (updated.blockMixedContent) {
                WebSettings.MIXED_CONTENT_NEVER_ALLOW
            } else {
                WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            }
            updated.customUserAgent?.let { userAgentString = it }
        }
        applyAlgorithmicDarkening(updated.darkMode)
    }

    /** Navigate back in the WebView history if possible. Returns `true` if consumed. */
    fun navigateBack(): Boolean {
        if (canGoBack()) {
            goBack()
            return true
        }
        return false
    }

    // ---------------------------------------------------------------------------------
    // Private helpers
    // ---------------------------------------------------------------------------------

    private fun applyAlgorithmicDarkening(enabled: Boolean) {
        val webSettings = settings
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            webSettings.isAlgorithmicDarkeningAllowed = enabled
        } else if (WebViewFeature.isFeatureSupported(WebViewFeature.ALGORITHMIC_DARKENING)) {
            WebSettingsCompat.setAlgorithmicDarkeningAllowed(webSettings, enabled)
        }
    }

    private fun normalise(url: String): String? {
        val trimmed = url.trim()
        if (trimmed.isEmpty()) return null
        val scheme = trimmed.substringBefore(':', missingDelimiterValue = "").lowercase()
        return when (scheme) {
            "http", "https" -> trimmed
            "file" -> trimmed.takeIf {
                it.startsWith("file:///android_asset/") || it.startsWith("file:///android_res/")
            }
            "about" -> trimmed.takeIf { it.equals("about:blank", ignoreCase = true) }
            "javascript", "data", "content", "intent", "blob",
            "mailto", "tel", "sms", "market",
            -> null
            else -> when {
                ' ' in trimmed || '.' !in trimmed ->
                    "https://duckduckgo.com/?q=${android.net.Uri.encode(trimmed)}"
                else -> "https://$trimmed"
            }
        }
    }

    /**
     * Injects JavaScript that:
     * 1. Patches all native `<video>` elements with `playsinline`, `crossorigin`, etc.
     * 2. Waits for VideoJS (if present) and configures it with proper HLS/VHS settings.
     */
    private fun injectVideoJs() {
        // language=JavaScript
        val js = """
(function() {
    // ── Native video element patching ──────────────────────────────────────────────
    function patchNativeVideos() {
        document.querySelectorAll('video').forEach(function(video) {
            if (video.hasAttribute('data-sledge-patched')) return;
            video.setAttribute('data-sledge-patched', 'true');
            video.setAttribute('playsinline', '');
            video.setAttribute('webkit-playsinline', '');
            video.setAttribute('crossorigin', 'anonymous');
            video.controls = true;
        });
    }

    patchNativeVideos();

    // Re-run when the DOM changes (lazy-loaded players).
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
            m.addedNodes.forEach(function(node) {
                if (node.nodeName === 'VIDEO') patchNativeVideos();
                if (node.querySelectorAll) node.querySelectorAll('video').forEach && patchNativeVideos();
            });
        });
    });
    observer.observe(document.body || document.documentElement, { childList: true, subtree: true });

    // ── VideoJS integration ────────────────────────────────────────────────────────
    function checkVideoSupport() {
        var t = document.createElement('video');
        return {
            hls: !!t.canPlayType('application/vnd.apple.mpegurl')
        };
    }

    function initVideoJS() {
        if (!window.videojs) return;
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

        document.querySelectorAll('.video-js').forEach(function(el) {
            if (el.player) return;
            var player = videojs(el, {
                controls: true,
                autoplay: false,
                preload: 'auto',
                responsive: true,
                fluid: true,
                playbackRates: [0.5, 1, 1.25, 1.5, 2],
                html5: {
                    vhs: { overrideNative: !checkVideoSupport().hls }
                }
            });
            player.on('error', function() {
                console.log('VideoJS error ' + player.error().code + ': ' + player.error().message);
            });
        });
    }

    function waitForVideoJS(attempts) {
        attempts = attempts || 0;
        if (window.videojs) { initVideoJS(); }
        else if (attempts < 10) { setTimeout(function() { waitForVideoJS(attempts + 1); }, 500); }
    }

    waitForVideoJS(0);
})();
        """.trimIndent()

        evaluateJavascript(js, null)
    }
}

/** Receives chunked blob bytes from page JavaScript. Ignored unless a read is in flight. */
class BlobDownloadBridge {
    private val lock = Any()
    private var transfer: BlobTransfer? = null

    fun begin(dest: File, onResult: (File?) -> Unit) {
        synchronized(lock) {
            transfer?.abort()
            transfer = BlobTransfer(dest, onResult)
        }
    }

    @JavascriptInterface
    fun onChunk(index: Int, total: Int, base64: String) {
        synchronized(lock) { transfer?.onChunk(index, total, base64) }
    }

    @JavascriptInterface
    fun onDone() {
        synchronized(lock) { transfer?.onDone() }
    }

    @JavascriptInterface
    fun onFail() {
        synchronized(lock) { transfer?.abort() }
    }

    private inner class BlobTransfer(
        private val dest: File,
        private val onResult: (File?) -> Unit,
    ) {
        private var next = 0
        private var expected = 0
        private var finished = false

        fun onChunk(index: Int, total: Int, base64: String) {
            if (finished || index != next || total < 1 || index >= total) {
                abort()
                return
            }
            if (next == 0) expected = total
            if (total != expected) {
                abort()
                return
            }
            try {
                dest.appendBytes(Base64.decode(base64, Base64.DEFAULT))
            } catch (_: IllegalArgumentException) {
                abort()
                return
            }
            next++
            if (next == expected) succeed()
        }

        fun onDone() {
            if (finished) return
            if (next == 0 && expected == 0) succeed() else abort()
        }

        fun abort() {
            if (finished) return
            finished = true
            if (transfer === this) transfer = null
            dest.delete()
            onResult(null)
        }

        private fun succeed() {
            finished = true
            if (transfer === this) transfer = null
            if (!dest.exists()) dest.createNewFile()
            onResult(dest)
        }
    }
}
