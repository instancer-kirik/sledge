package com.sledge.browser.history

/**
 * Platform-agnostic contract for reading and writing browser history.
 *
 * Implementations are expected on each target platform (Android / iOS).
 * All operations are `suspend` functions and are safe to call from any coroutine context;
 * implementations should dispatch heavy I/O to an appropriate dispatcher internally.
 */
interface HistoryManager {

    /**
     * Records a new visit for [url] with the given [title].
     *
     * If an entry for the same URL already exists within a reasonable deduplication
     * window (implementation-defined), the implementation may choose to update the
     * existing record's [HistoryEntry.visitedAt] rather than inserting a duplicate.
     */
    suspend fun add(url: String, title: String)

    /**
     * Returns all history entries whose URL or title contains [query] (case-insensitive),
     * ordered by most-recently-visited first.
     *
     * An empty [query] string should return all entries.
     */
    suspend fun search(query: String): List<HistoryEntry>

    /**
     * Returns up to [limit] most-recently-visited entries, ordered newest-first.
     *
     * @param limit Maximum number of entries to return. Defaults to 50.
     */
    suspend fun recent(limit: Int = 50): List<HistoryEntry>

    /**
     * Permanently deletes all history entries.
     */
    suspend fun clear()

    /**
     * Permanently deletes the single history entry identified by [id].
     *
     * If no entry with the given [id] exists this is a no-op.
     */
    suspend fun delete(id: Long)
}
