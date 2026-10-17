package com.sledge.browser.model

/**
 * A page the user saved for later.
 *
 * @property id        Stable identifier. 0 means not yet assigned.
 * @property url       Full URL of the bookmarked page.
 * @property title     Page title at the time it was saved.
 * @property createdAt Unix epoch timestamp in milliseconds.
 */
data class Bookmark(
    val id: Long = 0L,
    val url: String,
    val title: String,
    val createdAt: Long,
)
