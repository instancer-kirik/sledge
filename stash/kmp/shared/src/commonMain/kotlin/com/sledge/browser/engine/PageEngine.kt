package com.sledge.browser.engine

import com.sledge.browser.model.BrowserSettings

/**
 * Page actions the Android view already exposes.
 * Generated from SledgeWebView. Android-only methods stay on that class.
 */
interface PageEngine {
    fun loadUrl(url: String)
    fun applySettings(updated: BrowserSettings)
    fun navigateBack(): Boolean
    fun goBack()
    fun goForward()
    fun reload()
    fun canGoBack(): Boolean
    fun canGoForward(): Boolean
}
