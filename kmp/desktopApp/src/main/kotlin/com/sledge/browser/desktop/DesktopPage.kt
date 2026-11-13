package com.sledge.browser.desktop

import com.sledge.browser.engine.PageEngine
import dev.datlag.kcef.KCEFBrowser
import com.sledge.browser.model.BrowserSettings


/**
 * Desktop page view. Navigation calls the embedded Chromium browser.
 * Signatures come from SledgeWebView. Methods Chromium cannot host stay as stubs.
 */
class DesktopPage : PageEngine {
    var browser: KCEFBrowser? = null
    private var pendingUrl: String? = null

    fun attach(next: KCEFBrowser) {
        browser = next
        val url = pendingUrl ?: return
        pendingUrl = null
        next.loadURL(url)
    }

    override fun loadUrl(url: String) {
        val current = browser
        if (current == null) pendingUrl = url else current.loadURL(url)
        }
    override fun applySettings(updated: BrowserSettings) {
        println("desktop page engine stub: applySettings")
    }
    override fun navigateBack(): Boolean {
        val current = browser ?: return false
        if (!current.canGoBack()) return false
        current.goBack()
        return true
        }
    override fun goBack() { browser?.goBack() }
    override fun goForward() { browser?.goForward() }
    override fun reload() { browser?.reload() }
    override fun canGoBack(): Boolean = browser?.canGoBack() == true
    override fun canGoForward(): Boolean = browser?.canGoForward() == true
}
