package com.sledge.browser.android

import com.sledge.browser.model.Tab
import com.sledge.browser.model.TabGroup
import java.io.File

/** Tabs the memory pass should pause or discard. */
data class MemoryPlan(
    val freezeIds: Set<String> = emptySet(),
    val hibernateIds: Set<String> = emptySet(),
)

/**
 * Decides which background tabs to freeze or hibernate.
 *
 * Mirrors the desktop browser: the visible tab stays live, groups marked
 * keep-awake are skipped, and idle tabs are paused before they are discarded.
 * Under memory pressure the discard threshold drops so background pages go
 * sooner.
 */
object TabMemory {
    const val FREEZE_IDLE_MS = 45_000L
    const val HIBERNATE_IDLE_MS = 90_000L
    const val PRESSURE_IDLE_MS = 20_000L
    const val PRESSURE_MB = 380

    fun rssMegabytes(): Int = runCatching {
        File("/proc/self/status").useLines { lines ->
            val line = lines.firstOrNull { it.startsWith("VmRSS:") } ?: return 0
            val kb = line.substringAfter(":").trim().substringBefore(" ").toIntOrNull() ?: return 0
            kb / 1024
        }
    }.getOrDefault(0)

    fun plan(
        tabs: List<Tab>,
        groups: List<TabGroup>,
        currentId: String?,
        auto: Boolean,
        now: Long = System.currentTimeMillis(),
        rssMb: Int = rssMegabytes(),
    ): MemoryPlan {
        if (!auto) return MemoryPlan()
        val keep = groups.filter { it.keepActive }.map { it.id }.toSet()
        val hibernateAfter = if (rssMb >= PRESSURE_MB) PRESSURE_IDLE_MS else HIBERNATE_IDLE_MS
        val freeze = mutableSetOf<String>()
        val hibernate = mutableSetOf<String>()
        for (tab in tabs) {
            if (tab.id == currentId || tab.groupId in keep) continue
            val idle = now - tab.lastAccessedAt
            when {
                idle >= hibernateAfter -> hibernate += tab.id
                idle >= FREEZE_IDLE_MS -> freeze += tab.id
            }
        }
        return MemoryPlan(freeze, hibernate)
    }
}
