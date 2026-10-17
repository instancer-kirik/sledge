package com.sledge.browser.android.engine

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.net.http.SslError
import android.webkit.SslErrorHandler
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import com.sledge.browser.engine.RequestInfo
import com.sledge.browser.engine.RequestInterceptor
import com.sledge.browser.engine.ResourceType
import com.sledge.browser.model.BrowserSettings
import org.mlm.adblock.RequestTypeMapper
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.ByteArrayInputStream

/**
 * [WebViewClient] subclass that wires the shared [RequestInterceptor] into Android's
 * WebView request pipeline and surfaces page-lifecycle events as simple lambdas.
 */
class SledgeWebViewClient(
    private val interceptor: RequestInterceptor,
    private val settings: BrowserSettings,
    private val brave: BraveAdBlock? = null,
) : WebViewClient() {

    // ---------------------------------------------------------------------------------
    // Lifecycle callbacks
    // ---------------------------------------------------------------------------------

    /** Called when a new page URL begins loading. Provides the URL. */
    var onPageStarted: ((url: String) -> Unit)? = null

    /**
     * Called when a page finishes loading.
     * @param url     Final URL (after any redirects).
     * @param title   Page title at finish time, or `null` if unavailable.
     */
    var onPageFinished: ((url: String, title: String?) -> Unit)? = null

    /** Called when the WebView reports a network or rendering error. */
    var onError: ((url: String?, errorCode: Int, description: String) -> Unit)? = null

    // ---------------------------------------------------------------------------------
    // OkHttpClient for ModifyHeaders fetches (lazy, one per client instance)
    // ---------------------------------------------------------------------------------

    private val okHttp: OkHttpClient by lazy { OkHttpClient() }

    /**
     * Page URL captured on the UI thread. [shouldInterceptRequest] runs on a
     * background thread and must not call [WebView.getUrl].
     */
    @Volatile
    private var pageUrl: String = ""

    /** Picks up a new [BrowserSettings] snapshot without rebuilding the WebView. */
    fun updateSettings(newSettings: BrowserSettings) {
        interceptor.updateSettings(newSettings)
    }

    // ---------------------------------------------------------------------------------
    // Resource-type inference
    // ---------------------------------------------------------------------------------

    /**
     * Infers a [ResourceType] from the request URL and Accept header because the
     * Android [WebResourceRequest] API does not expose a semantic resource-type field.
     */
    private fun inferResourceType(request: WebResourceRequest): ResourceType {
        val url = request.url.toString().lowercase()
        val accept = request.requestHeaders["Accept"] ?: ""
        return when {
            request.isForMainFrame -> ResourceType.MAIN_FRAME
            accept.contains("text/html") -> ResourceType.SUB_FRAME
            url.contains(".js") || url.contains("/script") -> ResourceType.SCRIPT
            url.contains(".css") || url.contains("/style") -> ResourceType.STYLESHEET
            accept.startsWith("image/") || url.matches(Regex(".*\\.(png|jpg|jpeg|gif|webp|svg|ico)(\\?.*)?$")) -> ResourceType.IMAGE
            accept.startsWith("font/") || url.matches(Regex(".*\\.(woff2?|ttf|otf|eot)(\\?.*)?$")) -> ResourceType.FONT
            accept.contains("application/json") || accept.contains("text/xml") -> ResourceType.XHR
            url.matches(Regex(".*\\.(mp4|webm|m3u8|ts|mpd|m4s|ogg|mp3|aac)(\\?.*)?$")) -> ResourceType.MEDIA
            else -> ResourceType.OTHER
        }
    }

    // ---------------------------------------------------------------------------------
    // Request interception
    // ---------------------------------------------------------------------------------

    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
        return openExternalScheme(view, request.url)
    }

    override fun shouldInterceptRequest(
        view: WebView,
        request: WebResourceRequest,
    ): WebResourceResponse? {
        val url = request.url.toString()
        val sourceUrl = if (request.isForMainFrame) url else pageUrl

        // Map the URL path and Accept header hints to a ResourceType because the
        // Android WebResourceRequest API does not expose a semantic resource type.
        val resourceType = inferResourceType(request)

        val requestType = if (request.isForMainFrame) {
            "document"
        } else {
            RequestTypeMapper.from(request.url, request.requestHeaders["Accept"])
        }
        if (brave?.shouldBlock(url, sourceUrl, requestType) == true) {
            return emptyBlockedResponse()
        }

        val requestInfo = RequestInfo(
            url = url,
            sourceUrl = sourceUrl,
            method = request.method ?: "GET",
            resourceType = resourceType,
        )

        return when (val result = interceptor.intercept(requestInfo)) {
            is RequestInterceptor.InterceptResult.Allow -> null

            is RequestInterceptor.InterceptResult.Block -> emptyBlockedResponse()

            is RequestInterceptor.InterceptResult.ModifyHeaders -> {
                fetchWithModifiedHeaders(request, result.headers)
            }
        }
    }

    private fun emptyBlockedResponse() = WebResourceResponse(
        "text/plain",
        "UTF-8",
        200,
        "OK",
        emptyMap(),
        ByteArrayInputStream(ByteArray(0)),
    )

    /**
     * Re-executes [request] via OkHttp with [extraHeaders] merged in, then wraps the
     * response body as a [WebResourceResponse] for the WebView to consume.
     */
    private fun fetchWithModifiedHeaders(
        request: WebResourceRequest,
        extraHeaders: Map<String, String>,
    ): WebResourceResponse? {
        return try {
            val builder = Request.Builder().url(request.url.toString())

            // Carry over original headers, then apply overrides.
            request.requestHeaders.forEach { (k, v) -> builder.header(k, v) }
            extraHeaders.forEach { (k, v) -> builder.header(k, v) }

            if (request.method != null && request.method != "GET") {
                builder.method(request.method, null)
            }

            val response = okHttp.newCall(builder.build()).execute()
            val contentType = response.header("Content-Type", "application/octet-stream") ?: "application/octet-stream"
            val mimeType = contentType.substringBefore(';').trim()
            val encoding = contentType.substringAfter("charset=", "UTF-8").trim()

            val responseHeaders = response.headers.toMultimap().mapValues { it.value.joinToString(", ") }

            WebResourceResponse(
                mimeType,
                encoding,
                response.code,
                response.message.ifBlank { "OK" },
                responseHeaders,
                response.body?.byteStream() ?: ByteArrayInputStream(ByteArray(0)),
            )
        } catch (_: Exception) {
            null // Fall back to the WebView's default handling on error.
        }
    }

    // ---------------------------------------------------------------------------------
    // Page lifecycle
    // ---------------------------------------------------------------------------------

    override fun onPageStarted(view: WebView, url: String, favicon: Bitmap?) {
        pageUrl = url
        super.onPageStarted(view, url, favicon)
        onPageStarted?.invoke(url)
    }

    override fun onPageFinished(view: WebView, url: String) {
        super.onPageFinished(view, url)
        onPageFinished?.invoke(url, view.title)
    }

    @Suppress("OVERRIDE_DEPRECATION")
    override fun onReceivedError(
        view: WebView,
        errorCode: Int,
        description: String,
        failingUrl: String,
    ) {
        @Suppress("DEPRECATION")
        super.onReceivedError(view, errorCode, description, failingUrl)
        onError?.invoke(failingUrl, errorCode, description)
    }

    override fun onReceivedError(
        view: WebView,
        request: WebResourceRequest,
        error: WebResourceError,
    ) {
        super.onReceivedError(view, request, error)
        if (request.isForMainFrame) {
            onError?.invoke(
                request.url.toString(),
                error.errorCode,
                error.description.toString(),
            )
        }
    }

    override fun onReceivedSslError(view: WebView, handler: SslErrorHandler, error: SslError) {
        // Strict: cancel SSL errors; never call handler.proceed() unconditionally.
        handler.cancel()
    }
}

private val EXTERNAL_SCHEMES = setOf("mailto", "tel", "sms", "intent", "market")

/**
 * Sends [uri] to another app when its scheme is one Sledge does not render.
 * http and https stay in the WebView. An [intent] URI cannot target a specific component.
 */
internal fun openExternalScheme(view: WebView, uri: Uri): Boolean {
    val scheme = uri.scheme?.lowercase() ?: return false
    if (scheme == "http" || scheme == "https") return false
    if (scheme !in EXTERNAL_SCHEMES) return false

    val intent = if (scheme == "intent") {
        try {
            Intent.parseUri(uri.toString(), Intent.URI_INTENT_SCHEME).apply {
                addCategory(Intent.CATEGORY_BROWSABLE)
                component = null
                selector = null
            }
        } catch (_: Exception) {
            return true
        }
    } else {
        Intent(Intent.ACTION_VIEW, uri)
    }

    return try {
        view.context.startActivity(intent)
        true
    } catch (_: ActivityNotFoundException) {
        val fallback = intent.getStringExtra("browser_fallback_url")
        if (fallback != null && (fallback.startsWith("https://") || fallback.startsWith("http://"))) {
            view.loadUrl(fallback)
        }
        true
    }
}

/** Opens a mailto, tel, sms, or market address from the address bar. */
internal fun launchAddressAction(context: Context, raw: String): Boolean {
    val uri = Uri.parse(raw)
    val scheme = uri.scheme?.lowercase() ?: return false
    if (scheme !in setOf("mailto", "tel", "sms", "market")) return false
    return try {
        context.startActivity(Intent(Intent.ACTION_VIEW, uri))
        true
    } catch (_: ActivityNotFoundException) {
        false
    }
}
