package com.sledge.browser.android.engine

import android.content.Context
import android.util.Log
import android.webkit.WebView
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import org.mlm.adblock.AdblockEngine
import java.io.File
import java.util.concurrent.TimeUnit
import kotlin.concurrent.thread

/**
 * Brave's adblock-rust engine, the same one the desktop app reaches through
 * the Python `adblock` package. Filter lists are downloaded and cached.
 */
class BraveAdBlock(context: Context) {

    private val appContext = context.applicationContext
    private val engine = AdblockEngine.create()
    private val dir = File(appContext.filesDir, "adblock").apply { mkdirs() }
    private val engineFile = File(dir, "engine.bin")
    private val stampFile = File(dir, "stamp.txt")

    @Volatile
    var enabled: Boolean = true

    @Volatile
    private var ready: Boolean = false

    var status by mutableStateOf("Brave engine is loading filter lists")
        private set

    private val http = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .build()

    fun start() {
        thread(name = "brave-adblock", isDaemon = true) {
            try {
                val cacheFresh = stampFile.exists() &&
                    System.currentTimeMillis() - stampFile.readText().toLong() < MAX_AGE_MS
                if (cacheFresh && engine.deserializeFrom(engineFile)) {
                    loadResources()
                    ready = true
                    status = "Brave engine, using cached EasyList, EasyPrivacy, and uBlock"
                    Log.i(TAG, status)
                    return@thread
                }

                val lists = FILTER_LISTS.map { fetch(it) }.filter { it.isNotBlank() }
                if (lists.isEmpty()) {
                    status = "Brave engine could not download filter lists"
                    Log.w(TAG, status)
                    return@thread
                }
                engine.loadFilterList(lists.joinToString("\n"))
                loadResources()
                engine.serializeTo(engineFile)
                stampFile.writeText(System.currentTimeMillis().toString())
                ready = true
                status = "Brave engine, EasyList + EasyPrivacy + uBlock"
                Log.i(TAG, status)
            } catch (error: Throwable) {
                status = "Brave engine failed to start"
                Log.e(TAG, status, error)
            }
        }
    }

    fun shouldBlock(url: String, sourceUrl: String, requestType: String): Boolean {
        if (!enabled || !ready) return false
        val decision = engine.checkNetworkRequest(url, sourceUrl, requestType)
        return decision.matched && !decision.exception
    }

    /** Hides elements the network rules cannot remove, such as inline ad slots. */
    fun injectCosmetics(webView: WebView, pageUrl: String) {
        if (!enabled || !ready || !pageUrl.startsWith("http")) return
        val css = engine.cosmeticResources(pageUrl)?.css().orEmpty()
        if (css.isBlank()) return
        val quoted = JSONObject.quote(css)
        webView.evaluateJavascript(
            """
            (function(){
              var style = document.getElementById('sledge-cosmetics');
              if (!style) {
                style = document.createElement('style');
                style.id = 'sledge-cosmetics';
                (document.head || document.documentElement).appendChild(style);
              }
              style.textContent = $quoted;
            })();
            """.trimIndent(),
            null,
        )
    }

    private fun loadResources() {
        try {
            val json = appContext.assets.open("adblock/resources.json")
                .bufferedReader()
                .use { it.readText() }
            engine.loadResources(json)
        } catch (error: Exception) {
            Log.w(TAG, "Scriptlet resources were not loaded", error)
        }
    }

    private fun fetch(url: String): String {
        val cache = File(dir, url.substringAfterLast('/').substringBefore('?'))
        return try {
            val response = http.newCall(Request.Builder().url(url).build()).execute()
            response.use { resp ->
                if (!resp.isSuccessful) error("HTTP ${resp.code} for $url")
                val body = resp.body?.string().orEmpty()
                if (body.isNotBlank()) cache.writeText(body)
                body
            }
        } catch (error: Exception) {
            Log.w(TAG, "Filter download failed for $url", error)
            if (cache.exists()) cache.readText() else ""
        }
    }

    private companion object {
        const val TAG = "Sledge"
        const val MAX_AGE_MS = 24L * 60L * 60L * 1000L
        val FILTER_LISTS = listOf(
            "https://easylist.to/easylist/easylist.txt",
            "https://easylist.to/easylist/easyprivacy.txt",
            "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/filters.txt",
        )
    }
}
