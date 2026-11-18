package com.sledge.browser.android

import android.view.View
import android.view.ViewGroup
import android.webkit.ConsoleMessage
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.material3.SnackbarHostState
import com.sledge.browser.BrowserStore
import com.sledge.browser.ui.BrowserPage
import com.sledge.browser.ui.ChromeHost
import com.sledge.browser.ui.ConsoleLevel
import com.sledge.browser.ui.PageHooks
import com.sledge.browser.adblock.AdBlocker
import com.sledge.browser.android.engine.BraveAdBlock
import com.sledge.browser.android.engine.SledgeWebView
import com.sledge.browser.android.engine.launchAddressAction
import com.sledge.browser.android.ui.PageActions
import com.sledge.browser.android.ui.rememberPageActions
import com.sledge.browser.model.BrowserSettings

/** Android page host. The WebView, including video handling, stays in this module. */
@Composable
fun rememberAndroidHost(
    store: BrowserStore,
    adBlocker: AdBlocker,
    brave: BraveAdBlock,
): ChromeHost {
    val context = LocalContext.current
    val actions = androidx.compose.runtime.remember { mutableStateOf<PageActions?>(null) }
    val zipReceiver = remember { mutableStateOf<(ByteArray) -> Unit>({}) }
    val openZip = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: return@rememberLauncherForActivityResult
        zipReceiver.value(bytes)
    }
    return ChromeHost(
        openPage = { hooks -> AndroidBrowserPage(context, store, adBlocker, brave, hooks, actions) },
        pageSlot = { page, modifier ->
            AndroidPageView((page as AndroidBrowserPage).webView, modifier)
        },
        fullscreen = { page, modifier ->
            val view = (page as AndroidBrowserPage).customView
            if (view != null) AndroidPageView(view, modifier)
        },
        backHandler = { enabled, onBack -> BackHandler(enabled, onBack) },
        launchAddress = { raw -> launchAddressAction(context, raw) },
        ringGesture = { onRing ->
            val activity = LocalContext.current as? MainActivity
            SideEffect { activity?.onTwoFingerDoubleTap = onRing }
            DisposableEffect(activity) {
                onDispose { activity?.onTwoFingerDoubleTap = null }
            }
        },
        wire = { snackbar -> actions.value = rememberPageActions(snackbar, store) },
        chooseZip = { deliver ->
            zipReceiver.value = deliver
            openZip.launch(arrayOf("application/zip", "application/octet-stream", "*/*"))
        },
    )
}

@Composable
private fun AndroidPageView(view: View, modifier: Modifier) {
    AndroidView(
        factory = {
            (view.parent as? ViewGroup)?.removeView(view)
            view
        },
        modifier = modifier,
    )
}

private fun ConsoleMessage.MessageLevel?.toConsoleLevel(): ConsoleLevel = when (this) {
    ConsoleMessage.MessageLevel.ERROR -> ConsoleLevel.Error
    ConsoleMessage.MessageLevel.WARNING -> ConsoleLevel.Warn
    ConsoleMessage.MessageLevel.TIP, ConsoleMessage.MessageLevel.DEBUG -> ConsoleLevel.Info
    else -> ConsoleLevel.Log
}

class AndroidBrowserPage(
    context: android.content.Context,
    store: BrowserStore,
    adBlocker: AdBlocker,
    brave: BraveAdBlock,
    private val hooks: PageHooks,
    private val actions: androidx.compose.runtime.MutableState<PageActions?>,
) : BrowserPage {
    private var full by mutableStateOf(false)
    var customView by mutableStateOf<View?>(null)
        private set
    override val fullscreen: Boolean get() = full

    val webView: SledgeWebView = SledgeWebView(
        context = context,
        settings = store.settings,
        adBlocker = adBlocker,
        brave = brave,
        onCreateTab = { initial ->
            (hooks.onCreateTab(initial) as? AndroidBrowserPage)?.webView
        },
    ).also { view ->
        view.onPageStartedCallback = { hooks.onPageStarted(it) }
        view.onPageFinishedCallback = { url, title -> hooks.onPageFinished(url, title) }
        view.sledgeWebChromeClient.onProgress = { hooks.onProgress(it) }
        view.sledgeWebChromeClient.onTitle = { hooks.onTitle(it) }
        view.sledgeWebChromeClient.onEnterFullscreen = { shown, _ ->
            customView = shown
            full = true
        }
        view.sledgeWebChromeClient.onExitFullscreen = {
            customView = null
            full = false
        }
        view.sledgeWebViewClient.onLookalike = { hooks.onLookalike(it) }
        view.onDownload = { url, userAgent, disposition, mime, length ->
            val handler = actions.value
            if (handler != null) {
                handler.onDownload(view, url, userAgent, disposition, mime, length)
            } else {
                hooks.onDownload(url, userAgent, disposition, mime, length)
            }
        }
        // Read the current actions when the page asks. The WebView is created
        // during composition, before the permission launcher is stored.
        view.sledgeWebChromeClient.onShowFileChooser = { callback, params ->
            val handler = actions.value
            if (handler == null) {
                callback?.onReceiveValue(null)
                false
            } else {
                handler.onShowFileChooser(callback, params)
            }
        }
        view.sledgeWebChromeClient.onPermissionRequest = { request ->
            val handler = actions.value
            if (handler == null) request.deny() else handler.onPermissionRequest(request)
        }
        view.sledgeWebChromeClient.onGeolocation = { origin, callback ->
            val handler = actions.value
            if (handler == null) callback.invoke(origin, false, false) else handler.onGeolocation(origin, callback)
        }
        view.sledgeWebChromeClient.onConsole = { message ->
            hooks.onConsole(
                message.messageLevel().toConsoleLevel(),
                message.message().orEmpty(),
                message.sourceId().orEmpty(),
                message.lineNumber(),
            )
        }
        view.sledgeWebViewClient.onResource = { url, type, blocked ->
            hooks.onNetwork(url, type, blocked)
        }
    }

    override val url: String? get() = webView.url
    override fun loadUrl(url: String) = webView.loadUrl(url)
    override fun goBack() = webView.goBack()
    override fun goForward() = webView.goForward()
    override fun reload() = webView.reload()
    override fun canGoBack(): Boolean = webView.canGoBack()
    override fun canGoForward(): Boolean = webView.canGoForward()
    override fun applySettings(settings: BrowserSettings) = webView.applySettings(settings)
    override fun onPause() = webView.onPause()
    override fun onResume() = webView.onResume()
    override fun destroy() {
        (webView.parent as? ViewGroup)?.removeView(webView)
        webView.destroy()
    }
    override fun exitFullscreen() = webView.sledgeWebChromeClient.exitFullscreen()
    override fun setFindListener(listener: (Int, Int, Boolean) -> Unit) {
        webView.setFindListener { ordinal, count, done -> listener(ordinal, count, done) }
    }
    override fun clearMatches() = webView.clearMatches()
    override fun findAllAsync(query: String) = webView.findAllAsync(query)
    override fun findNext(forward: Boolean) = webView.findNext(forward)
    override fun evaluate(script: String) = evaluate(script) {}
    override fun evaluate(script: String, onResult: (String?) -> Unit) {
        webView.evaluateJavascript(script) { value -> onResult(value) }
    }
}
