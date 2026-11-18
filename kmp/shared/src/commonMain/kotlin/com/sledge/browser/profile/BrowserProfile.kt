package com.sledge.browser.profile

/**
 * Site sign-in that survives leaving the app.
 *
 * Android writes the WebView cookie jar. Desktop writes the Chromium profile.
 * The two stores are not interchangeable, so each target implements this itself.
 */
interface BrowserProfile {
    /** Accept cookies before the first page loads. */
    fun open()

    /** Push cookies to disk. Call this before the process can be killed. */
    fun flush()
}
