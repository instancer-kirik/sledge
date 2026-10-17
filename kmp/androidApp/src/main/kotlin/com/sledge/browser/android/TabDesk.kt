package com.sledge.browser.android

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.sledge.browser.model.Tab
import com.sledge.browser.model.TabGroup
import com.sledge.browser.model.TabLifecycle
import java.util.UUID

/**
 * Tab list, groups, and the memory pass for one browser window.
 *
 * Compose reads [tabs], [groups], [currentIndex], and [autoMemory] directly,
 * so the chrome redraws as soon as a page, group, or lifecycle changes.
 */
class TabDesk {
    val tabs = mutableStateListOf<Tab>()
    val groups = mutableStateListOf<TabGroup>()
    var currentIndex by mutableIntStateOf(0)
    var autoMemory by mutableStateOf(true)
        private set

    fun updateAutoMemory(enabled: Boolean) {
        if (autoMemory == enabled) return
        autoMemory = enabled
        changed()
    }

    val current: Tab? get() = tabs.getOrNull(currentIndex)

    /** Fired after a user-visible change. Not fired while [restore] is running. */
    var onChanged: (() -> Unit)? = null

    fun restore(
        tabs: List<Tab>,
        groups: List<TabGroup>,
        currentIndex: Int,
        autoMemory: Boolean,
    ) {
        val listener = onChanged
        onChanged = null
        this.tabs.clear()
        this.tabs.addAll(tabs)
        this.groups.clear()
        this.groups.addAll(groups)
        this.currentIndex = currentIndex.coerceIn(0, (tabs.size - 1).coerceAtLeast(0))
        this.autoMemory = autoMemory
        onChanged = listener
    }

    fun open(url: String = START_PAGE): Tab {
        val tab = Tab(
            id = UUID.randomUUID().toString(),
            url = url,
            title = "",
            isLoading = true,
            lastAccessedAt = System.currentTimeMillis(),
        )
        tabs += tab
        currentIndex = tabs.lastIndex
        changed()
        return tab
    }

    fun close(index: Int) {
        if (tabs.isEmpty()) return
        if (tabs.size <= 1) {
            tabs[0] = fresh(START_PAGE)
            currentIndex = 0
            pruneGroups()
            changed()
            return
        }
        if (index !in tabs.indices) return
        tabs.removeAt(index)
        currentIndex = currentIndex.coerceAtMost(tabs.lastIndex)
        pruneGroups()
        changed()
    }

    fun select(index: Int) {
        if (index !in tabs.indices) return
        currentIndex = index
        val tab = tabs[index]
        tabs[index] = tab.copy(
            lifecycle = TabLifecycle.Active,
            lastAccessedAt = System.currentTimeMillis(),
            isLoading = tab.lifecycle == TabLifecycle.Hibernated || tab.isLoading,
        )
        changed()
    }

    fun update(id: String, url: String, title: String?, isLoading: Boolean?) {
        val index = tabs.indexOfFirst { it.id == id }
        if (index !in tabs.indices) return
        val current = tabs[index]
        tabs[index] = current.copy(
            url = url.ifBlank { current.url },
            title = if (title.isNullOrBlank()) current.title else title,
            isLoading = isLoading ?: current.isLoading,
        )
        changed()
    }

    fun hibernate(index: Int) {
        if (index !in tabs.indices) return
        val tab = tabs[index]
        if (tab.lifecycle == TabLifecycle.Hibernated) return
        tabs[index] = tab.copy(lifecycle = TabLifecycle.Hibernated, isLoading = false)
        changed()
    }

    fun wake(index: Int) = select(index)

    /** Mark every discarded tab live again. Pages reload the next time they are shown. */
    fun wakeAll() {
        val now = System.currentTimeMillis()
        tabs.forEachIndexed { index, tab ->
            if (tab.lifecycle != TabLifecycle.Active) {
                tabs[index] = tab.copy(lifecycle = TabLifecycle.Active, lastAccessedAt = now)
            }
        }
        changed()
    }

    /** Discard every background tab that is not in a keep-awake group. */
    fun sleepBackground() {
        val currentId = current?.id
        tabs.forEachIndexed { index, tab ->
            if (tab.id == currentId) return@forEachIndexed
            val group = groups.find { it.id == tab.groupId }
            if (group?.keepActive == true) return@forEachIndexed
            if (tab.lifecycle != TabLifecycle.Hibernated) {
                tabs[index] = tab.copy(lifecycle = TabLifecycle.Hibernated, isLoading = false)
            }
        }
        changed()
    }

    fun applyMemory() {
        val plan = TabMemory.plan(tabs, groups, current?.id, autoMemory)
        var dirty = false
        tabs.forEachIndexed { index, tab ->
            val next = when (tab.id) {
                in plan.hibernateIds -> TabLifecycle.Hibernated
                in plan.freezeIds -> TabLifecycle.Frozen
                else -> tab.lifecycle
            }
            if (next != tab.lifecycle) {
                dirty = true
                tabs[index] = tab.copy(
                    lifecycle = next,
                    isLoading = if (next == TabLifecycle.Hibernated) false else tab.isLoading,
                )
            }
        }
        if (dirty) changed()
    }

    fun createGroup(name: String, color: Long, tabIndex: Int) {
        val cleaned = name.trim().ifBlank { "Group" }
        val group = TabGroup(
            id = UUID.randomUUID().toString(),
            name = cleaned,
            color = color,
        )
        groups += group
        assignGroup(tabIndex, group.id)
        changed()
    }

    fun assignGroup(tabIndex: Int, groupId: String?) {
        if (tabIndex !in tabs.indices) return
        if (groupId != null && groups.none { it.id == groupId }) return
        tabs[tabIndex] = tabs[tabIndex].copy(groupId = groupId)
        pruneGroups()
        changed()
    }

    fun toggleCollapsed(groupId: String) = editGroup(groupId) { it.copy(collapsed = !it.collapsed) }

    fun toggleKeepActive(groupId: String, keep: Boolean) = editGroup(groupId) { it.copy(keepActive = keep) }

    fun renameGroup(groupId: String, name: String) {
        val cleaned = name.trim()
        if (cleaned.isEmpty()) return
        editGroup(groupId) { it.copy(name = cleaned) }
    }

    fun recolorGroup(groupId: String, color: Long) = editGroup(groupId) { it.copy(color = color) }

    fun dissolveGroup(groupId: String) {
        tabs.forEachIndexed { index, tab ->
            if (tab.groupId == groupId) tabs[index] = tab.copy(groupId = null)
        }
        groups.removeAll { it.id == groupId }
        changed()
    }

    private fun editGroup(groupId: String, block: (TabGroup) -> TabGroup) {
        val index = groups.indexOfFirst { it.id == groupId }
        if (index >= 0) groups[index] = block(groups[index])
        changed()
    }

    private fun pruneGroups() {
        val live = tabs.mapNotNull { it.groupId }.toSet()
        groups.removeAll { it.id !in live }
    }

    private fun changed() {
        onChanged?.invoke()
    }

    private fun fresh(url: String) = Tab(
        id = UUID.randomUUID().toString(),
        url = url,
        title = "",
        isLoading = true,
        lastAccessedAt = System.currentTimeMillis(),
    )
}
