package com.sledge.browser.ui

import androidx.compose.runtime.Composable
import androidx.compose.material3.SnackbarHostState
import androidx.compose.ui.Modifier
import com.sledge.browser.model.BrowserSettings

enum class ConsoleLevel { Log, Info, Warn, Error }

data class ConsoleLine(
    val level: ConsoleLevel,
    val message: String,
    val source: String,
    val line: Int,
)

/** One request the page made. `type` is document, script, stylesheet, image, and so on. */
data class NetworkEntry(
    val url: String,
    val type: String,
    val blocked: Boolean,
)

/** Events the screen listens for. The host reads them when the page fires. */
class PageHooks {
    var onPageStarted: (String) -> Unit = {}
    var onPageFinished: (String, String?) -> Unit = { _, _ -> }
    var onProgress: (Int) -> Unit = {}
    var onTitle: (String) -> Unit = {}
    var onLookalike: (String) -> Boolean = { false }
    var onDownload: (String, String, String, String, Long) -> Unit = { _, _, _, _, _ -> }
    var onCreateTab: (String?) -> BrowserPage? = { null }
    var onConsole: (ConsoleLevel, String, String, Int) -> Unit = { _, _, _, _ -> }
    var onNetwork: (String, String, Boolean) -> Unit = { _, _, _ -> }
}

/** What the shared screen can ask a page to do. */
interface BrowserPage {
    val url: String?
    val fullscreen: Boolean
    fun loadUrl(url: String)
    fun goBack()
    fun goForward()
    fun reload()
    fun canGoBack(): Boolean
    fun canGoForward(): Boolean
    fun applySettings(settings: BrowserSettings)
    fun onPause()
    fun onResume()
    fun destroy()
    fun exitFullscreen()
    fun setFindListener(listener: (Int, Int, Boolean) -> Unit)
    fun clearMatches()
    fun findAllAsync(query: String)
    fun findNext(forward: Boolean)

    /** Runs in the page after it finishes loading. Used for extension content scripts. */
    fun evaluate(script: String) {}

    /** Runs [script] and passes back the string the page returned. */
    fun evaluate(script: String, onResult: (String?) -> Unit) {
        evaluate(script)
        onResult(null)
    }
}

/** Filter status the settings panel shows. The engine stays on the target. */
interface ListBlocker {
    var enabled: Boolean
    val status: String
}

/** Platform pieces around the shared screen. */
class ChromeHost(
    val openPage: (PageHooks) -> BrowserPage,
    val pageSlot: @Composable (BrowserPage, Modifier) -> Unit,
    val fullscreen: @Composable (BrowserPage, Modifier) -> Unit,
    val backHandler: @Composable (Boolean, () -> Unit) -> Unit,
    val launchAddress: (String) -> Boolean,
    val ringGesture: @Composable (() -> Unit) -> Unit,
    val wire: @Composable (SnackbarHostState) -> Unit,
    /** Opens a file picker and passes back the chosen `.zip` or `.crx` bytes. */
    val chooseZip: ((ByteArray) -> Unit) -> Unit = {},
)
