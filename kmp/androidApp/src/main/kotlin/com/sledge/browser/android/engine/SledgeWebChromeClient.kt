package com.sledge.browser.android.engine

import android.net.Uri
import android.view.View
import android.view.ViewGroup
import android.webkit.GeolocationPermissions
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebView

/**
 * [WebChromeClient] subclass that handles progress/title updates, popup windows,
 * and fullscreen video.
 *
 * @param onCreateTab     Called when a popup window should open a new tab.
 *                        Receives an optional initial URL and returns the new [WebView]
 *                        (so its [android.webkit.WebView.WebViewTransport] can be set), or
 *                        `null` if the caller declines to create a tab.
 * @param popupsOpenNewTab Returns `true` when popups should be captured as new tabs rather
 *                        than being blocked outright.
 */
class SledgeWebChromeClient(
    private val onCreateTab: (initialUrl: String?) -> WebView?,
    private val popupsOpenNewTab: () -> Boolean,
) : WebChromeClient() {

    // ---------------------------------------------------------------------------------
    // Progress / title callbacks
    // ---------------------------------------------------------------------------------

    /** Invoked with loading progress in the range [0, 100]. */
    var onProgress: ((progress: Int) -> Unit)? = null

    /** Invoked when the page title changes. */
    var onTitle: ((title: String) -> Unit)? = null

    // ---------------------------------------------------------------------------------
    // Fullscreen video callbacks
    // ---------------------------------------------------------------------------------

    /** Invoked when a video element enters fullscreen. The caller must add [view] to the
     *  window and hide all other UI. */
    var onEnterFullscreen: ((view: View, callback: CustomViewCallback) -> Unit)? = null

    /** Invoked when fullscreen mode ends. The caller must remove the view added in
     *  [onEnterFullscreen] and restore the normal UI. */
    var onExitFullscreen: (() -> Unit)? = null

    // Track the custom fullscreen view so we can clean up if needed.
    private var fullscreenView: View? = null
    private var fullscreenCallback: CustomViewCallback? = null

    // ---------------------------------------------------------------------------------
    // WebChromeClient overrides
    // ---------------------------------------------------------------------------------

    override fun onProgressChanged(view: WebView, newProgress: Int) {
        super.onProgressChanged(view, newProgress)
        onProgress?.invoke(newProgress)
    }

    override fun onReceivedTitle(view: WebView, title: String) {
        super.onReceivedTitle(view, title)
        onTitle?.invoke(title)
    }

    override fun onCreateWindow(
        view: WebView,
        isDialog: Boolean,
        isUserGesture: Boolean,
        resultMsg: android.os.Message,
    ): Boolean {
        if (!isDialog && !isUserGesture) return false
        if (!popupsOpenNewTab()) return false

        val newWebView = onCreateTab(null) ?: return false

        val transport = resultMsg.obj as? WebView.WebViewTransport ?: return false
        transport.webView = newWebView
        resultMsg.sendToTarget()
        return true
    }

    override fun onShowCustomView(view: View, callback: CustomViewCallback) {
        // If there's already a fullscreen view, dismiss it first.
        fullscreenView?.let { existing ->
            (existing.parent as? ViewGroup)?.removeView(existing)
            fullscreenCallback?.onCustomViewHidden()
        }
        fullscreenView = view
        fullscreenCallback = callback
        onEnterFullscreen?.invoke(view, callback)
    }

    override fun onHideCustomView() {
        val view = fullscreenView ?: return
        val callback = fullscreenCallback
        fullscreenView = null
        fullscreenCallback = null
        (view.parent as? ViewGroup)?.removeView(view)
        callback?.onCustomViewHidden()
        onExitFullscreen?.invoke()
    }

    /** Leaves fullscreen video when the system back button is pressed. */
    fun exitFullscreen() {
        if (fullscreenView != null) onHideCustomView()
    }

    // ---------------------------------------------------------------------------------
    // File chooser and permissions
    // ---------------------------------------------------------------------------------

    /**
     * Return true after taking [callback]. The caller must invoke it, including with
     * null when the user cancels, or the page waits forever.
     */
    var onShowFileChooser: ((ValueCallback<Array<Uri>>?, FileChooserParams?) -> Boolean)? = null

    /** Return without calling through and the request is denied. */
    var onPermissionRequest: ((PermissionRequest) -> Unit)? = null

    /** Third argument to the geolocation callback is always `false` (do not retain). */
    var onGeolocation: ((origin: String, callback: GeolocationPermissions.Callback) -> Unit)? = null

    override fun onShowFileChooser(
        webView: WebView,
        filePathCallback: ValueCallback<Array<Uri>>?,
        fileChooserParams: FileChooserParams?,
    ): Boolean {
        return onShowFileChooser?.invoke(filePathCallback, fileChooserParams) == true
    }

    override fun onPermissionRequest(request: PermissionRequest) {
        val handler = onPermissionRequest
        if (handler == null) request.deny() else handler(request)
    }

    override fun onGeolocationPermissionsShowPrompt(
        origin: String,
        callback: GeolocationPermissions.Callback,
    ) {
        val handler = onGeolocation
        if (handler == null) callback.invoke(origin, false, false) else handler(origin, callback)
    }
}
