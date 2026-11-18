package com.sledge.browser.desktop

import com.sledge.browser.profile.BrowserProfile
import org.cef.network.CefCookieManager
import java.io.File

/**
 * Chromium profile for desktop sign-in. The directory stays under the home
 * folder so a launch from another working directory still finds the cookies.
 * The cookie encryption key stays in the desktop keyring. A local password
 * store would let anyone who can read this directory decrypt the jar.
 */
class DesktopBrowserProfile : BrowserProfile {
    override fun open() {
        desktopProfileDirectory().mkdirs()
    }

    override fun flush() {
        flushDesktopCookies()
    }
}

fun desktopProfileDirectory(): File {
    val dir = File(System.getProperty("user.home"), ".local/share/sledge")
    dir.mkdirs()
    return dir
}

fun flushDesktopCookies() {
    val manager = CefCookieManager.getGlobalManager() ?: return
    manager.flushStore(null)
}
