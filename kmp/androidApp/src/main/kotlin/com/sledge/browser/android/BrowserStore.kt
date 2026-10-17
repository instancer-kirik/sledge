package com.sledge.browser.android

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.sledge.browser.history.HistoryEntry
import com.sledge.browser.history.HistoryManager
import com.sledge.browser.model.Bookmark
import com.sledge.browser.model.BrowserSettings

/** Local start page bundled in android assets. */
const val START_PAGE = "file:///android_asset/start.html"

/** An http(s) URL from an external intent. Anything else is dropped. */
fun externalWebUrl(raw: String?): String? {
    val scheme = raw?.let { android.net.Uri.parse(it).scheme }?.lowercase() ?: return null
    return if (scheme == "http" || scheme == "https") raw else null
}

private val blockedBarSchemes = setOf(
    "file", "javascript", "data", "content", "intent", "about", "blob",
)

/** Schemes the bar hands to another app instead of loading or searching. */
private val actionBarSchemes = setOf("mailto", "tel", "sms", "market")

/** What the address bar should do with [text]. */
sealed class AddressInput {
    data object Empty : AddressInput()
    data object Blocked : AddressInput()
    data class Open(val text: String) : AddressInput()
    data class Action(val text: String) : AddressInput()
}

/** Web and search text, an app action, or a scheme the bar must not load. */
fun addressBarTarget(text: String): AddressInput {
    val trimmed = text.trim()
    if (trimmed.isEmpty()) return AddressInput.Empty
    val scheme = trimmed.substringBefore(':', missingDelimiterValue = "").lowercase()
    if (scheme in blockedBarSchemes) return AddressInput.Blocked
    if (scheme in actionBarSchemes) return AddressInput.Action(trimmed)
    return AddressInput.Open(trimmed)
}

/** Hide the asset URL in the address bar. */
fun displayUrl(url: String): String =
    if (url.startsWith("file:///android_asset/")) "" else url

/** Host shown in the address pill when it is not being edited. */
fun displayHost(url: String): String {
    if (!url.startsWith("http://") && !url.startsWith("https://")) return ""
    return url.substringAfter("://")
        .substringBefore("/")
        .substringBefore("?")
        .removePrefix("www.")
}

/**
 * History, bookmarks, settings, and per-site location choices.
 *
 * Holds snapshot state so Compose redraws as soon as a page is recorded or a
 * toggle changes. [onChanged] writes the session file. Implements [HistoryManager]
 * so the shared contract stays real.
 */
class BrowserStore : HistoryManager {

    val history = mutableStateListOf<HistoryEntry>()
    val bookmarks = mutableStateListOf<Bookmark>()
    var settings by mutableStateOf(BrowserSettings())
    var locationChoices by mutableStateOf<Map<String, Boolean>>(emptyMap())
        private set

    /** Fired after a user-visible change. Not fired while a session file is loading. */
    var onChanged: (() -> Unit)? = null

    private var nextHistoryId = 1L
    private var nextBookmarkId = 1L
    private var loading = false

    fun recordVisit(url: String, title: String) {
        if (!url.startsWith("http://") && !url.startsWith("https://")) return
        val now = System.currentTimeMillis()
        val existing = history.indexOfFirst { it.url == url }
        val id = if (existing >= 0) history[existing].id else nextHistoryId++
        if (existing >= 0) history.removeAt(existing)
        history.add(
            0,
            HistoryEntry(
                id = id,
                url = url,
                title = title.ifBlank { url },
                visitedAt = now,
            ),
        )
        while (history.size > 200) history.removeAt(history.lastIndex)
        changed()
    }

    fun updateSettings(updated: BrowserSettings) {
        settings = updated
        changed()
    }

    /** `null` when this origin has not been asked yet. */
    fun locationChoice(origin: String): Boolean? = locationChoices[origin]

    fun setLocationChoice(origin: String, allowed: Boolean) {
        locationChoices = locationChoices + (origin to allowed)
        changed()
    }

    fun clearLocationChoices() {
        if (locationChoices.isEmpty()) return
        locationChoices = emptyMap()
        changed()
    }

    fun importSession(
        history: List<HistoryEntry>,
        bookmarks: List<Bookmark>,
        settings: BrowserSettings,
        locationChoices: Map<String, Boolean>,
    ) {
        loading = true
        this.history.clear()
        this.history.addAll(history)
        this.bookmarks.clear()
        this.bookmarks.addAll(bookmarks)
        this.settings = settings
        this.locationChoices = locationChoices
        nextHistoryId = (history.maxOfOrNull { it.id } ?: 0L) + 1L
        nextBookmarkId = (bookmarks.maxOfOrNull { it.id } ?: 0L) + 1L
        loading = false
    }

    fun isBookmarked(url: String): Boolean = bookmarks.any { it.url == url }

    /** @return true when the page is now bookmarked. */
    fun toggleBookmark(url: String, title: String): Boolean {
        if (!url.startsWith("http://") && !url.startsWith("https://")) return false
        val existing = bookmarks.indexOfFirst { it.url == url }
        if (existing >= 0) {
            bookmarks.removeAt(existing)
            changed()
            return false
        }
        bookmarks.add(
            0,
            Bookmark(
                id = nextBookmarkId++,
                url = url,
                title = title.ifBlank { url },
                createdAt = System.currentTimeMillis(),
            ),
        )
        changed()
        return true
    }

    fun deleteBookmark(id: Long) {
        bookmarks.removeAll { it.id == id }
        changed()
    }

    fun deleteHistory(id: Long) {
        history.removeAll { it.id == id }
        changed()
    }

    fun clearHistory() {
        history.clear()
        changed()
    }

    private fun changed() {
        if (!loading) onChanged?.invoke()
    }

    override suspend fun add(url: String, title: String) = recordVisit(url, title)

    override suspend fun search(query: String): List<HistoryEntry> {
        if (query.isBlank()) return history.toList()
        return history.filter {
            it.url.contains(query, ignoreCase = true) ||
                it.title.contains(query, ignoreCase = true)
        }
    }

    override suspend fun recent(limit: Int): List<HistoryEntry> = history.take(limit)

    override suspend fun clear() = clearHistory()

    override suspend fun delete(id: Long) = deleteHistory(id)
}
