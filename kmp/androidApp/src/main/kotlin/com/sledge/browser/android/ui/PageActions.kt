package com.sledge.browser.android.ui

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.webkit.CookieManager
import android.webkit.GeolocationPermissions
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import com.sledge.browser.android.BrowserStore
import com.sledge.browser.android.R
import com.sledge.browser.android.displayHost
import com.sledge.browser.android.engine.PublicDownload
import com.sledge.browser.android.engine.SledgeWebView
import com.sledge.browser.android.engine.decodeDataUrl
import com.sledge.browser.android.engine.enqueuePublicDownload
import com.sledge.browser.android.engine.fetchToFile
import com.sledge.browser.android.engine.guessDownloadName
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

/**
 * File chooser, runtime permissions, and downloads for every [SledgeWebView].
 * Launchers are registered once for the screen and shared across tabs.
 * A second dialog is cancelled while one is already open.
 */
class PageActions(
    val onShowFileChooser: (ValueCallback<Array<Uri>>?, WebChromeClient.FileChooserParams?) -> Boolean,
    val onPermissionRequest: (PermissionRequest) -> Unit,
    val onGeolocation: (String, GeolocationPermissions.Callback) -> Unit,
    val onDownload: (
        view: SledgeWebView,
        url: String,
        userAgent: String,
        contentDisposition: String,
        mimeType: String,
        contentLength: Long,
    ) -> Unit,
)

@Composable
fun rememberPageActions(snackbar: SnackbarHostState, store: BrowserStore): PageActions {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val pending = remember { PendingPageRequests() }
    var sitePrompt by remember {
        mutableStateOf<Pair<String, GeolocationPermissions.Callback>?>(null)
    }

    fun finishSitePrompt(allowed: Boolean) {
        val prompt = sitePrompt ?: return
        sitePrompt = null
        pending.dialogOpen = false
        store.setLocationChoice(prompt.first, allowed)
        prompt.second.invoke(prompt.first, allowed, false)
    }

    fun showSitePrompt(origin: String, callback: GeolocationPermissions.Callback) {
        when (store.locationChoice(origin)) {
            false -> callback.invoke(origin, false, false)
            true -> callback.invoke(origin, true, false)
            null -> {
                pending.dialogOpen = true
                sitePrompt = origin to callback
            }
        }
    }

    sitePrompt?.let { (origin, _) ->
        val host = displayHost(origin).ifBlank { origin }
        AlertDialog(
            onDismissRequest = { finishSitePrompt(false) },
            title = { Text(context.getString(R.string.location_title)) },
            text = { Text(context.getString(R.string.location_message, host)) },
            confirmButton = {
                TextButton(onClick = { finishSitePrompt(true) }) {
                    Text(context.getString(R.string.location_allow))
                }
            },
            dismissButton = {
                TextButton(onClick = { finishSitePrompt(false) }) {
                    Text(context.getString(R.string.location_block))
                }
            },
        )
    }

    fun failDownload(filename: String) {
        scope.launch { snackbar.showSnackbar(context.getString(R.string.download_failed, filename)) }
    }

    fun finishFile(uris: Array<Uri>?) {
        pending.dialogOpen = false
        val callback = pending.file
        pending.file = null
        callback?.onReceiveValue(uris)
    }

    val getContent = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        finishFile(uri?.let { arrayOf(it) })
    }
    val openMultiple = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->
        finishFile(if (uris.isEmpty()) null else uris.toTypedArray())
    }
    val mediaPermissions = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { result ->
        val request = pending.permission
        val prior = pending.priorGrants
        pending.permission = null
        pending.priorGrants = emptySet()
        pending.dialogOpen = false
        if (request == null) return@rememberLauncherForActivityResult
        grantKnownMedia(request, prior + result.filterValues { it }.keys)
    }
    val locationPermissions = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { result ->
        val origin = pending.geoOrigin
        val callback = pending.geoCallback
        pending.geoOrigin = null
        pending.geoCallback = null
        pending.dialogOpen = false
        if (origin == null || callback == null) return@rememberLauncherForActivityResult
        val granted = result[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            result[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        if (!granted) callback.invoke(origin, false, false) else showSitePrompt(origin, callback)
    }
    val createDocument = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("application/octet-stream"),
    ) { uri ->
        val save = pending.save
        pending.save = null
        pending.dialogOpen = false
        if (uri == null || save == null) {
            save?.file?.delete()
            return@rememberLauncherForActivityResult
        }
        scope.launch {
            val wrote = writeSave(context, uri, save)
            save.file?.delete()
            snackbar.showSnackbar(
                context.getString(
                    if (wrote) R.string.download_saved else R.string.download_failed,
                    save.filename,
                ),
            )
        }
    }

    fun offerSave(filename: String, bytes: ByteArray?, file: File?) {
        if (pending.dialogOpen) {
            file?.delete()
            failDownload(filename)
            return
        }
        pending.dialogOpen = true
        pending.save = PendingSave(filename, bytes, file)
        createDocument.launch(filename)
    }

    return remember(getContent, openMultiple, mediaPermissions, locationPermissions, createDocument) {
        PageActions(
            onShowFileChooser = { callback, params ->
                if (callback == null) return@PageActions false
                if (pending.dialogOpen) {
                    callback.onReceiveValue(null)
                    return@PageActions true
                }
                pending.dialogOpen = true
                pending.file = callback
                val mime = params.acceptMime()
                if (params?.mode == WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE) {
                    openMultiple.launch(arrayOf(mime))
                } else {
                    getContent.launch(mime)
                }
                true
            },
            onPermissionRequest = { request ->
                val needed = mediaPermissionsFor(request.resources)
                val already = needed.filter { permission ->
                    ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
                }.toSet()
                val missing = needed.filter { it !in already }
                if (missing.isEmpty()) {
                    grantKnownMedia(request, already)
                    return@PageActions
                }
                if (pending.dialogOpen) {
                    request.deny()
                    return@PageActions
                }
                pending.dialogOpen = true
                pending.permission = request
                pending.priorGrants = already
                mediaPermissions.launch(missing.toTypedArray())
            },
            onGeolocation = { origin, callback ->
                if (store.locationChoice(origin) == false) {
                    callback.invoke(origin, false, false)
                    return@PageActions
                }
                val fine = ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.ACCESS_FINE_LOCATION,
                ) == PackageManager.PERMISSION_GRANTED
                val coarse = ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                ) == PackageManager.PERMISSION_GRANTED
                if (fine || coarse) {
                    if (pending.dialogOpen && store.locationChoice(origin) != true) {
                        callback.invoke(origin, false, false)
                    } else {
                        showSitePrompt(origin, callback)
                    }
                    return@PageActions
                }
                if (pending.dialogOpen) {
                    callback.invoke(origin, false, false)
                    return@PageActions
                }
                pending.dialogOpen = true
                pending.geoOrigin = origin
                pending.geoCallback = callback
                locationPermissions.launch(
                    arrayOf(
                        Manifest.permission.ACCESS_FINE_LOCATION,
                        Manifest.permission.ACCESS_COARSE_LOCATION,
                    ),
                )
            },
            onDownload = { view, url, userAgent, contentDisposition, mimeType, _ ->
                val filename = guessDownloadName(url, contentDisposition, mimeType)
                when {
                    url.startsWith("http://") || url.startsWith("https://") -> {
                        when (val result = enqueuePublicDownload(context, url, userAgent, contentDisposition, mimeType)) {
                            is PublicDownload.Enqueued -> scope.launch {
                                snackbar.showSnackbar(context.getString(R.string.download_started, result.filename))
                            }
                            PublicDownload.NeedsSaveDialog -> {
                                if (pending.dialogOpen || pending.transferOpen) {
                                    failDownload(filename)
                                } else {
                                    pending.transferOpen = true
                                    val cookie = CookieManager.getInstance().getCookie(url)
                                    val dest = cacheDownload(context)
                                    scope.launch {
                                        val ok = withContext(Dispatchers.IO) {
                                            fetchToFile(url, userAgent, cookie, dest)
                                        }
                                        pending.transferOpen = false
                                        if (ok) offerSave(filename, null, dest) else {
                                            dest.delete()
                                            failDownload(filename)
                                        }
                                    }
                                }
                            }
                            PublicDownload.Failed -> failDownload(filename)
                        }
                    }
                    url.startsWith("data:") -> {
                        val decoded = decodeDataUrl(url)
                        if (decoded == null) failDownload(filename) else offerSave(filename, decoded.bytes, null)
                    }
                    url.startsWith("blob:") -> {
                        if (pending.dialogOpen || pending.transferOpen) {
                            failDownload(filename)
                        } else {
                            pending.transferOpen = true
                            val dest = cacheDownload(context)
                            view.readBlob(url, dest) { file ->
                                pending.transferOpen = false
                                if (file == null) failDownload(filename) else offerSave(filename, null, file)
                            }
                        }
                    }
                    else -> failDownload(filename)
                }
            },
        )
    }
}

private class PendingPageRequests {
    var dialogOpen: Boolean = false
    var transferOpen: Boolean = false
    var file: ValueCallback<Array<Uri>>? = null
    var permission: PermissionRequest? = null
    var priorGrants: Set<String> = emptySet()
    var geoOrigin: String? = null
    var geoCallback: GeolocationPermissions.Callback? = null
    var save: PendingSave? = null
}

private class PendingSave(val filename: String, val bytes: ByteArray?, val file: File?)

private fun cacheDownload(context: Context): File {
    val dir = File(context.cacheDir, "downloads").apply { mkdirs() }
    return File(dir, "sledge-${System.nanoTime()}")
}

private fun WebChromeClient.FileChooserParams?.acceptMime(): String {
    val raw = this?.acceptTypes?.firstOrNull { it.isNotBlank() } ?: return "*/*"
    return if (raw.startsWith(".")) "*/*" else raw
}

private fun mediaPermissionsFor(resources: Array<String>): List<String> = buildList {
    if (PermissionRequest.RESOURCE_VIDEO_CAPTURE in resources) add(Manifest.permission.CAMERA)
    if (PermissionRequest.RESOURCE_AUDIO_CAPTURE in resources) add(Manifest.permission.RECORD_AUDIO)
}

private fun grantKnownMedia(request: PermissionRequest, granted: Set<String>) {
    val allow = request.resources.filter { resource ->
        when (resource) {
            PermissionRequest.RESOURCE_VIDEO_CAPTURE ->
                Manifest.permission.CAMERA in granted
            PermissionRequest.RESOURCE_AUDIO_CAPTURE ->
                Manifest.permission.RECORD_AUDIO in granted
            PermissionRequest.RESOURCE_PROTECTED_MEDIA_ID -> true
            else -> false
        }
    }
    if (allow.isEmpty()) request.deny() else request.grant(allow.toTypedArray())
}

private suspend fun writeSave(context: Context, uri: Uri, save: PendingSave): Boolean =
    withContext(Dispatchers.IO) {
        runCatching {
            context.contentResolver.openOutputStream(uri)?.use { stream ->
                when {
                    save.bytes != null -> stream.write(save.bytes)
                    save.file != null -> save.file.inputStream().use { it.copyTo(stream) }
                    else -> return@use
                }
            } != null
        }.getOrDefault(false)
    }
