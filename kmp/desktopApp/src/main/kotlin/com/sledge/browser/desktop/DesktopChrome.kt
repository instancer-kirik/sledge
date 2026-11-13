package com.sledge.browser.desktop

import androidx.compose.foundation.layout.Box
import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.awt.SwingPanel
import dev.datlag.kcef.KCEFBrowser
import dev.datlag.kcef.KCEFClient
import org.cef.CefSettings
import org.cef.browser.CefBrowser
import org.cef.browser.CefFrame
import org.cef.browser.CefRendering
import org.cef.handler.CefDisplayHandlerAdapter
import org.cef.handler.CefLifeSpanHandlerAdapter
import org.cef.handler.CefLoadHandlerAdapter
import org.cef.handler.CefRequestHandlerAdapter
import org.cef.network.CefRequest
import com.sledge.browser.ui.BrowserPage
import com.sledge.browser.ui.ChromeHost
import com.sledge.browser.ui.ConsoleLevel
import com.sledge.browser.ui.ListBlocker
import com.sledge.browser.ui.PageHooks
import com.sledge.browser.model.BrowserSettings
import java.awt.Component
import java.io.File
import java.net.URLEncoder
import java.util.concurrent.ConcurrentHashMap
import javax.swing.SwingUtilities

/** Desktop page host. Request handling for this engine is filled in here. */
@Composable
fun rememberDesktopHost(): ChromeHost = ChromeHost(
    openPage = { hooks -> DesktopBrowserPage(hooks) },
    pageSlot = { page, modifier -> DesktopPageView(page as DesktopBrowserPage, modifier) },
    fullscreen = { page, modifier -> DesktopPageView(page as DesktopBrowserPage, modifier) },
    backHandler = { _, _ -> },
    launchAddress = { _ -> false },
    ringGesture = { _ -> },
    wire = { _: SnackbarHostState -> },
)

class DesktopFilters : ListBlocker {
    override var enabled: Boolean = true
    override var status by mutableStateOf("Filter lists run in the shared blocker")
        private set
}

object DesktopEngine {
    var client: KCEFClient? = null

    /** Kept here so a regenerated Main still starts the engine the same way. */
    fun prepare(bundle: File) {
        if (!bundle.isDirectory) return
        val aside = File(bundle, "gpu-aside")
        val names = listOf(
            "libGLESv2.so",
            "libEGL.so",
            "libvk_swiftshader.so",
            "libvulkan.so.1",
            "vk_swiftshader_icd.json",
        )
        val present = names.map { File(bundle, it) }.filter { it.isFile }
        if (present.isEmpty()) return
        aside.mkdirs()
        present.forEach { file -> file.renameTo(File(aside, file.name)) }
    }

    fun arguments(bundle: File, helper: String): Array<String> = arrayOf(
        "--browser-subprocess-path=$helper",
        "--resources-dir-path=${bundle.absolutePath}",
        "--locales-dir-path=${File(bundle, "locales").absolutePath}",
        "--use-gl=egl",
        "--disable-gpu-sandbox",
        "--disable-features=Vulkan",
    )
}

private object DesktopNavigation {
    private val pages = ConcurrentHashMap<CefBrowser, DesktopBrowserPage>()
    private val pagesById = ConcurrentHashMap<Int, DesktopBrowserPage>()
    private var installed = false

    fun install(client: KCEFClient) {
        if (installed) return
        installed = true
        client.addLifeSpanHandler(object : CefLifeSpanHandlerAdapter() {
            override fun onAfterCreated(browser: CefBrowser) {
                remember(browser)
            }

            override fun onBeforePopup(
                browser: CefBrowser,
                frame: CefFrame,
                targetUrl: String,
                targetFrameName: String,
            ): Boolean {
                openInPage(browser, targetUrl)
                return true
            }
        })
        client.addRequestHandler(object : CefRequestHandlerAdapter() {
            override fun onOpenURLFromTab(
                browser: CefBrowser,
                frame: CefFrame,
                targetUrl: String,
                userGesture: Boolean,
            ): Boolean {
                openInPage(browser, targetUrl)
                return true
            }

            override fun onBeforeBrowse(
                browser: CefBrowser,
                frame: CefFrame,
                request: CefRequest,
                userGesture: Boolean,
                isRedirect: Boolean,
            ): Boolean {
                if (!frame.isMain) return false
                val url = request.url ?: return false
                if (!url.startsWith("http://") && !url.startsWith("https://")) return false
                return page(browser)?.blockForLookalike(url) == true
            }
        })
        client.addDisplayHandler(object : CefDisplayHandlerAdapter() {
            override fun onAddressChange(browser: CefBrowser, frame: CefFrame, url: String) {
                if (frame.isMain) page(browser)?.showAddress(url)
            }

            override fun onTitleChange(browser: CefBrowser, title: String) {
                page(browser)?.showTitle(title)
            }

            override fun onConsoleMessage(
                browser: CefBrowser,
                level: CefSettings.LogSeverity,
                message: String,
                source: String,
                line: Int,
            ): Boolean {
                page(browser)?.showConsole(level.toConsoleLevel(), message, source, line)
                return true
            }
        })
        client.addLoadHandler(object : CefLoadHandlerAdapter() {
            override fun onLoadEnd(browser: CefBrowser, frame: CefFrame, httpStatusCode: Int) {
                if (frame.isMain) page(browser)?.showFinished(browser.url.orEmpty())
            }

            override fun onLoadError(
                browser: CefBrowser,
                frame: CefFrame,
                errorCode: org.cef.handler.CefLoadHandler.ErrorCode,
                errorText: String,
                failedUrl: String,
            ) {
                if (frame.isMain && errorCode != org.cef.handler.CefLoadHandler.ErrorCode.ERR_ABORTED) {
                    page(browser)?.showFinished(failedUrl)
                }
            }
        })
    }

    fun attach(browser: CefBrowser, page: DesktopBrowserPage) {
        pages[browser] = page
        val id = browser.identifier
        if (id > 0) pagesById[id] = page
    }

    fun detach(browser: CefBrowser) {
        val page = pages.remove(browser) ?: return
        pagesById.entries.removeIf { it.value === page }
    }

    private fun remember(browser: CefBrowser) {
        val known = page(browser) ?: pages.values.firstOrNull { pages.size == 1 } ?: return
        pages[browser] = known
        val id = browser.identifier
        if (id > 0) pagesById[id] = known
    }

    private fun page(browser: CefBrowser): DesktopBrowserPage? =
        pages[browser] ?: browser.identifier.takeIf { it > 0 }?.let { pagesById[it] }

    private fun openInPage(browser: CefBrowser, targetUrl: String?) {
        val url = targetUrl?.takeIf { it.isNotBlank() } ?: return
        SwingUtilities.invokeLater { browser.loadURL(url) }
    }
}

internal fun navigableWebUrl(url: String): String? {
    val trimmed = url.trim()
    if (trimmed.isEmpty()) return null
    val scheme = trimmed.substringBefore(':', missingDelimiterValue = "").lowercase()
    return when (scheme) {
        "http", "https", "file" -> trimmed
        "about" -> trimmed.takeIf { it.equals("about:blank", ignoreCase = true) }
        "javascript", "data", "content", "intent", "blob",
        "mailto", "tel", "sms", "market",
        -> null
        else -> when {
            ' ' in trimmed || '.' !in trimmed ->
                "https://duckduckgo.com/?q=${URLEncoder.encode(trimmed, Charsets.UTF_8)}"
            else -> "https://$trimmed"
        }
    }
}

@Composable
private fun DesktopPageView(page: DesktopBrowserPage, modifier: Modifier) {
    val component = page.component
    if (component == null) Box(modifier) else SwingPanel(factory = { component }, modifier = modifier)
}

class DesktopBrowserPage(private val hooks: PageHooks) : BrowserPage {
    val permissions = DesktopPermissionGate()
    private var browser: KCEFBrowser? = null
    private var current: String? = null
    override val url: String? get() = current
    override val fullscreen: Boolean get() = false
    var component by mutableStateOf<Component?>(null)
        private set

    override fun loadUrl(next: String) {
        val url = navigableWebUrl(next) ?: return
        if (hooks.onLookalike(url)) return
        current = url
        hooks.onPageStarted(url)
        val page = browser ?: open(url)
        page?.loadURL(url)
    }

    fun blockForLookalike(url: String): Boolean = hooks.onLookalike(url)

    fun showAddress(url: String) {
        if (url.isBlank()) return
        SwingUtilities.invokeLater {
            current = url
            hooks.onPageStarted(url)
        }
    }

    fun showTitle(title: String) {
        SwingUtilities.invokeLater { hooks.onTitle(title) }
    }

    fun showConsole(level: ConsoleLevel, message: String, source: String, line: Int) {
        SwingUtilities.invokeLater { hooks.onConsole(level, message, source, line) }
    }

    fun showFinished(url: String) {
        val shown = url.ifBlank { current }.orEmpty()
        if (shown.isBlank()) return
        SwingUtilities.invokeLater {
            current = shown
            hooks.onPageFinished(shown, null)
        }
    }

    override fun goBack() { browser?.goBack() }
    override fun goForward() { browser?.goForward() }
    override fun reload() { browser?.reload() }
    override fun canGoBack(): Boolean = browser?.canGoBack() == true
    override fun canGoForward(): Boolean = browser?.canGoForward() == true
    override fun applySettings(settings: BrowserSettings) {}
    override fun onPause() {}
    override fun onResume() {}
    override fun destroy() {
        val page = browser
        browser = null
        component = null
        if (page != null) {
            DesktopNavigation.detach(page)
            page.close(true)
        }
    }
    override fun exitFullscreen() {}
    override fun setFindListener(listener: (Int, Int, Boolean) -> Unit) {}
    override fun clearMatches() {}
    override fun findAllAsync(query: String) {}
    override fun findNext(forward: Boolean) {}

    private fun open(next: String): KCEFBrowser? {
        val holder = DesktopEngine.client ?: return null
        DesktopNavigation.install(holder)
        val created = holder.createBrowser(next, CefRendering.DEFAULT, false)
        created.createImmediately()
        DesktopNavigation.attach(created, this)
        browser = created
        component = created.uiComponent
        return created
    }
}

private fun CefSettings.LogSeverity.toConsoleLevel(): ConsoleLevel = when (this) {
    CefSettings.LogSeverity.LOGSEVERITY_ERROR,
    CefSettings.LogSeverity.LOGSEVERITY_FATAL,
    -> ConsoleLevel.Error
    CefSettings.LogSeverity.LOGSEVERITY_WARNING -> ConsoleLevel.Warn
    CefSettings.LogSeverity.LOGSEVERITY_INFO,
    CefSettings.LogSeverity.LOGSEVERITY_VERBOSE,
    -> ConsoleLevel.Info
    else -> ConsoleLevel.Log
}
