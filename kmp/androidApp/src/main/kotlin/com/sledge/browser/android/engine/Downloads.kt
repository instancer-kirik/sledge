package com.sledge.browser.android.engine

import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.util.Base64
import android.webkit.CookieManager
import android.webkit.URLUtil
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.net.URLDecoder
import java.util.concurrent.TimeUnit

/** A `data:` URL decoded into bytes the Storage Access Framework can write. */
data class DecodedData(val mime: String, val bytes: ByteArray)

fun guessDownloadName(url: String, contentDisposition: String, mimeType: String): String =
    URLUtil.guessFileName(url, contentDisposition, mimeType)

/** Result of asking [DownloadManager] to store a file in public Downloads. */
sealed class PublicDownload {
    data class Enqueued(val filename: String) : PublicDownload()

    /** Public Downloads rejected the write. The caller should save the bytes itself. */
    data object NeedsSaveDialog : PublicDownload()

    data object Failed : PublicDownload()
}

private val downloadClient: OkHttpClient by lazy {
    OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .build()
}

/**
 * Enqueues an http(s) download into public Downloads.
 * [PublicDownload.NeedsSaveDialog] means the platform refused the public directory.
 */
fun enqueuePublicDownload(
    context: Context,
    url: String,
    userAgent: String,
    contentDisposition: String,
    mimeType: String,
): PublicDownload {
    val filename = guessDownloadName(url, contentDisposition, mimeType)
    val request = DownloadManager.Request(Uri.parse(url))
        .setMimeType(mimeType.ifBlank { "application/octet-stream" })
        .setTitle(filename)
        .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
        .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename)
        .addRequestHeader("User-Agent", userAgent)
    CookieManager.getInstance().getCookie(url)?.let { request.addRequestHeader("Cookie", it) }
    return try {
        val manager = context.getSystemService(DownloadManager::class.java)
            ?: return PublicDownload.Failed
        manager.enqueue(request)
        PublicDownload.Enqueued(filename)
    } catch (_: SecurityException) {
        PublicDownload.NeedsSaveDialog
    } catch (_: Exception) {
        PublicDownload.Failed
    }
}

/** Streams an http(s) response into [dest]. [cookie] is the WebView cookie header, if any. */
fun fetchToFile(url: String, userAgent: String, cookie: String?, dest: File): Boolean {
    val builder = Request.Builder().url(url).header("User-Agent", userAgent)
    if (!cookie.isNullOrBlank()) builder.header("Cookie", cookie)
    return try {
        downloadClient.newCall(builder.build()).execute().use { response ->
            if (!response.isSuccessful) return false
            val body = response.body ?: return false
            dest.outputStream().use { output -> body.byteStream().copyTo(output) }
            true
        }
    } catch (_: Exception) {
        dest.delete()
        false
    }
}

/** Decodes a `data:` URL. Returns null when the payload is missing or not valid base64. */
fun decodeDataUrl(url: String): DecodedData? {
    if (!url.startsWith("data:", ignoreCase = true)) return null
    val comma = url.indexOf(',')
    if (comma < 0) return null
    val meta = url.substring(5, comma)
    val payload = url.substring(comma + 1)
    val mime = meta.substringBefore(';').ifBlank { "application/octet-stream" }
    val bytes = if (meta.contains(";base64", ignoreCase = true)) {
        try {
            Base64.decode(payload, Base64.DEFAULT)
        } catch (_: IllegalArgumentException) {
            return null
        }
    } else {
        try {
            URLDecoder.decode(payload, Charsets.UTF_8.name()).toByteArray(Charsets.UTF_8)
        } catch (_: IllegalArgumentException) {
            return null
        }
    }
    return DecodedData(mime, bytes)
}
