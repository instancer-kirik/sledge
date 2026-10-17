package com.sledge.browser.android

import com.sledge.browser.history.HistoryEntry
import com.sledge.browser.model.Bookmark
import com.sledge.browser.model.BrowserSettings
import com.sledge.browser.model.Tab
import com.sledge.browser.model.TabGroup
import com.sledge.browser.model.TabLifecycle
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Tabs, history, bookmarks, settings, and per-site location choices in one file. */
class SessionFile(private val file: File) {

    fun load(desk: TabDesk, store: BrowserStore) {
        if (!file.exists()) return
        val root = try {
            JSONObject(file.readText())
        } catch (_: Exception) {
            return
        }
        store.importSession(
            history = root.optJSONArray("history").toHistory(),
            bookmarks = root.optJSONArray("bookmarks").toBookmarks(),
            settings = root.optJSONObject("settings").toSettings(store.settings),
            locationChoices = root.optJSONObject("location").toLocationChoices(),
        )
        desk.restore(
            tabs = root.optJSONArray("tabs").toTabs(),
            groups = root.optJSONArray("groups").toGroups(),
            currentIndex = root.optInt("currentIndex", 0),
            autoMemory = root.optBoolean("autoMemory", true),
        )
    }

    fun save(desk: TabDesk, store: BrowserStore) {
        val root = JSONObject()
        root.put("currentIndex", desk.currentIndex)
        root.put("autoMemory", desk.autoMemory)
        root.put("history", JSONArray().apply {
            store.history.forEach { entry ->
                put(JSONObject()
                    .put("id", entry.id)
                    .put("url", entry.url)
                    .put("title", entry.title)
                    .put("visitedAt", entry.visitedAt))
            }
        })
        root.put("bookmarks", JSONArray().apply {
            store.bookmarks.forEach { mark ->
                put(JSONObject()
                    .put("id", mark.id)
                    .put("url", mark.url)
                    .put("title", mark.title)
                    .put("createdAt", mark.createdAt))
            }
        })
        root.put("settings", JSONObject()
            .put("blockAds", store.settings.blockAds)
            .put("blockMixedContent", store.settings.blockMixedContent)
            .put("blockDangerousPorts", store.settings.blockDangerousPorts)
            .put("popupsOpenNewTab", store.settings.popupsOpenNewTab)
            .put("javascriptEnabled", store.settings.javascriptEnabled)
            .put("darkMode", store.settings.darkMode))
        root.put("groups", JSONArray().apply {
            desk.groups.forEach { group ->
                put(JSONObject()
                    .put("id", group.id)
                    .put("name", group.name)
                    .put("color", group.color)
                    .put("collapsed", group.collapsed)
                    .put("keepActive", group.keepActive))
            }
        })
        root.put("tabs", JSONArray().apply {
            desk.tabs.forEach { tab ->
                put(JSONObject()
                    .put("id", tab.id)
                    .put("url", tab.url)
                    .put("title", tab.title)
                    .put("lifecycle", tab.lifecycle.name)
                    .put("groupId", tab.groupId)
                    .put("lastAccessedAt", tab.lastAccessedAt))
            }
        })
        val location = JSONObject()
        store.locationChoices.forEach { (origin, allowed) -> location.put(origin, allowed) }
        root.put("location", location)
        writeAtomic(root.toString())
    }

    private fun writeAtomic(text: String) {
        val tmp = File(file.parentFile, "${file.name}.tmp")
        tmp.writeText(text)
        if (!tmp.renameTo(file)) {
            file.writeText(text)
            tmp.delete()
        }
    }
}

private fun JSONArray?.toHistory(): List<HistoryEntry> {
    if (this == null) return emptyList()
    return buildList {
        for (i in 0 until length()) {
            val item = optJSONObject(i) ?: continue
            val url = item.optString("url")
            if (!url.startsWith("http://") && !url.startsWith("https://")) continue
            add(HistoryEntry(
                id = item.optLong("id"),
                url = url,
                title = item.optString("title"),
                visitedAt = item.optLong("visitedAt"),
            ))
        }
    }
}

private fun JSONArray?.toBookmarks(): List<Bookmark> {
    if (this == null) return emptyList()
    return buildList {
        for (i in 0 until length()) {
            val item = optJSONObject(i) ?: continue
            val url = item.optString("url")
            if (!url.startsWith("http://") && !url.startsWith("https://")) continue
            add(Bookmark(
                id = item.optLong("id"),
                url = url,
                title = item.optString("title"),
                createdAt = item.optLong("createdAt"),
            ))
        }
    }
}

private fun JSONObject?.toSettings(current: BrowserSettings): BrowserSettings {
    if (this == null) return current
    return current.copy(
        blockAds = optBoolean("blockAds", current.blockAds),
        blockMixedContent = optBoolean("blockMixedContent", current.blockMixedContent),
        blockDangerousPorts = optBoolean("blockDangerousPorts", current.blockDangerousPorts),
        popupsOpenNewTab = optBoolean("popupsOpenNewTab", current.popupsOpenNewTab),
        javascriptEnabled = optBoolean("javascriptEnabled", current.javascriptEnabled),
        darkMode = optBoolean("darkMode", current.darkMode),
    )
}

private fun JSONArray?.toGroups(): List<TabGroup> {
    if (this == null) return emptyList()
    return buildList {
        for (i in 0 until length()) {
            val item = optJSONObject(i) ?: continue
            val id = item.optString("id")
            if (id.isBlank()) continue
            add(TabGroup(
                id = id,
                name = item.optString("name").ifBlank { "Group" },
                color = item.optLong("color"),
                collapsed = item.optBoolean("collapsed"),
                keepActive = item.optBoolean("keepActive"),
            ))
        }
    }
}

private fun JSONArray?.toTabs(): List<Tab> {
    if (this == null) return emptyList()
    return buildList {
        for (i in 0 until length()) {
            val item = optJSONObject(i) ?: continue
            val id = item.optString("id")
            val url = item.optString("url")
            val web = url.startsWith("http://") || url.startsWith("https://")
            val asset = url.startsWith("file:///android_asset/") || url.startsWith("file:///android_res/")
            if (id.isBlank() || (!web && !asset)) continue
            val saved = runCatching { TabLifecycle.valueOf(item.optString("lifecycle")) }
                .getOrDefault(TabLifecycle.Active)
            add(Tab(
                id = id,
                url = url,
                title = item.optString("title"),
                isLoading = false,
                lifecycle = if (saved == TabLifecycle.Hibernated) TabLifecycle.Hibernated else TabLifecycle.Active,
                groupId = item.optString("groupId").ifBlank { null },
                lastAccessedAt = item.optLong("lastAccessedAt"),
            ))
        }
    }
}

private fun JSONObject?.toLocationChoices(): Map<String, Boolean> {
    if (this == null) return emptyMap()
    return buildMap {
        keys().forEach { key ->
            if (!isNull(key)) put(key, optBoolean(key))
        }
    }
}
