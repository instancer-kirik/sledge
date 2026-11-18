package com.sledge.browser.android.profile

import android.webkit.CookieManager
import android.webkit.WebView
import com.sledge.browser.profile.BrowserProfile

/**
 * WebView already keeps cookies in the app's private data. This makes that
 * jar accept sign-in cookies and writes them out before Android can kill the
 * process. No separate keystore: the app sandbox is the protection.
 */
class AndroidBrowserProfile : BrowserProfile {
    override fun open() {
        CookieManager.getInstance().setAcceptCookie(true)
    }

    override fun flush() {
        CookieManager.getInstance().flush()
    }

    /** Sign-in widgets on another origin need this. First-party cookies stay on either way. */
    fun acceptOn(view: WebView) {
        CookieManager.getInstance().setAcceptThirdPartyCookies(view, true)
    }
}
