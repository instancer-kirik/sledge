package com.sledge.browser.history

/**
 * A single recorded page visit in the browser history.
 *
 * @property id         Auto-assigned primary key (0 means not yet persisted).
 * @property url        The full URL that was visited.
 * @property title      The page title at the time of the visit.
 * @property visitedAt  Unix epoch timestamp in milliseconds.
 * @property faviconUrl Remote URL of the page's favicon, if known.
 */
data class HistoryEntry(
    val id: Long = 0L,
    val url: String,
    val title: String,
    val visitedAt: Long,
    val faviconUrl: String? = null,
)
