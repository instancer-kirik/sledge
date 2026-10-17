package com.sledge.browser.model

/** How much of a tab's page is kept in memory. */
enum class TabLifecycle {
    /** Page is loaded and eligible to run. */
    Active,

    /** Page is still loaded, but paused so it costs less while it sits in the background. */
    Frozen,

    /** Page was discarded. The URL is kept and reloaded the next time the tab is opened. */
    Hibernated,
}

/**
 * Represents a single browser tab.
 *
 * @property id        Stable unique identifier for the tab (e.g. UUID string).
 * @property url       The current URL displayed in the tab.
 * @property title     The page title; may be empty while the page is loading.
 * @property isLoading Whether the tab is actively loading content.
 * @property favicon   Raw bytes of the tab's favicon image, or `null` if unavailable.
 * @property lifecycle Whether the page is live, paused, or discarded.
 * @property groupId   Owning [TabGroup.id], or `null` when the tab is ungrouped.
 * @property lastAccessedAt Epoch millis when the tab was last selected.
 */
data class Tab(
    val id: String,
    val url: String,
    val title: String,
    val isLoading: Boolean = false,
    val favicon: ByteArray? = null,
    val lifecycle: TabLifecycle = TabLifecycle.Active,
    val groupId: String? = null,
    val lastAccessedAt: Long = 0L,
) {
    // ByteArray breaks structural equality; provide explicit implementations.
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is Tab) return false
        return id == other.id &&
            url == other.url &&
            title == other.title &&
            isLoading == other.isLoading &&
            favicon.contentEquals(other.favicon) &&
            lifecycle == other.lifecycle &&
            groupId == other.groupId &&
            lastAccessedAt == other.lastAccessedAt
    }

    override fun hashCode(): Int {
        var result = id.hashCode()
        result = 31 * result + url.hashCode()
        result = 31 * result + title.hashCode()
        result = 31 * result + isLoading.hashCode()
        result = 31 * result + (favicon?.contentHashCode() ?: 0)
        result = 31 * result + lifecycle.hashCode()
        result = 31 * result + (groupId?.hashCode() ?: 0)
        result = 31 * result + lastAccessedAt.hashCode()
        return result
    }
}

/**
 * A named, colour-coded collection of tabs.
 *
 * Membership lives on [Tab.groupId] so closing a tab cannot leave a stale id behind.
 *
 * @property id         Stable unique identifier for the group.
 * @property name       Display name shown in the tab strip.
 * @property color      Opaque ARGB colour used for the group mark.
 * @property collapsed  When true, member tabs hide in the strip until expanded.
 * @property keepActive When true, automatic memory management leaves these tabs alone.
 */
data class TabGroup(
    val id: String,
    val name: String,
    val color: Long = 0xFF88C0D0,
    val collapsed: Boolean = false,
    val keepActive: Boolean = false,
)

/** Convenience extension to check whether a [ByteArray]? matches another. */
private fun ByteArray?.contentEquals(other: ByteArray?): Boolean =
    if (this == null && other == null) true
    else if (this == null || other == null) false
    else this.contentEquals(other)
