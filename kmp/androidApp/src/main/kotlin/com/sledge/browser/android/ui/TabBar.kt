package com.sledge.browser.android.ui

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import kotlinx.coroutines.delay
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sledge.browser.android.R
import com.sledge.browser.android.displayHost
import com.sledge.browser.model.Tab
import com.sledge.browser.model.TabGroup
import com.sledge.browser.model.TabLifecycle

private sealed interface StripItem {
    data class Header(val group: TabGroup, val count: Int) : StripItem
    data class Chip(val index: Int, val tab: Tab, val color: Color?) : StripItem
}

/**
 * Tab strip with colour-coded groups.
 *
 * A group header sits in front of its members. Collapsed groups keep the
 * header and hide the rest, except the tab that is currently open.
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
fun TabBar(
    tabs: List<Tab>,
    groups: List<TabGroup>,
    currentIndex: Int,
    onTabSelect: (Int) -> Unit,
    onTabClose: (Int) -> Unit,
    onTabLongPress: (Int) -> Unit,
    onGroupClick: (String) -> Unit,
    onGroupLongPress: (String) -> Unit,
    onNewTab: () -> Unit,
    onOverview: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val scrollState = rememberScrollState()
    val byId = groups.associateBy { it.id }
    val items = buildStrip(tabs, byId, currentIndex)

    LaunchedEffect(currentIndex, tabs.size) {
        delay(32)
        val target = (currentIndex * 150).coerceAtLeast(0)
        scrollState.animateScrollTo(target.coerceAtMost(scrollState.maxValue))
    }

    Surface(color = SledgeTheme.Chrome, modifier = modifier.height(56.dp)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxHeight()
                .horizontalScroll(scrollState)
                .padding(horizontal = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            items.forEach { item ->
                when (item) {
                    is StripItem.Header -> GroupChip(
                        group = item.group,
                        count = item.count,
                        onClick = { onGroupClick(item.group.id) },
                        onLongClick = { onGroupLongPress(item.group.id) },
                    )
                    is StripItem.Chip -> TabChip(
                        tab = item.tab,
                        isActive = item.index == currentIndex,
                        groupColor = item.color,
                        onSelect = { onTabSelect(item.index) },
                        onClose = { onTabClose(item.index) },
                        onLongPress = { onTabLongPress(item.index) },
                    )
                }
            }

            IconButton(
                onClick = onNewTab,
                modifier = Modifier
                    .size(32.dp)
                    .clip(SledgeTheme.Corner)
                    .background(SledgeTheme.Surface),
            ) {
                Icon(
                    imageVector = Icons.Default.Add,
                    contentDescription = stringResource(R.string.add_tab),
                    tint = SledgeTheme.Accent,
                    modifier = Modifier.size(18.dp),
                )
            }

            OverviewButton(count = tabs.size, onClick = onOverview)
        }
    }
}

private fun buildStrip(
    tabs: List<Tab>,
    groups: Map<String, TabGroup>,
    currentIndex: Int,
): List<StripItem> {
    val seen = mutableSetOf<String>()
    val items = mutableListOf<StripItem>()
    tabs.forEachIndexed { index, tab ->
        val group = tab.groupId?.let { groups[it] }
        if (group != null && group.id !in seen) {
            seen += group.id
            val count = tabs.count { it.groupId == group.id }
            items += StripItem.Header(group, count)
        }
        val hidden = group != null && group.collapsed && index != currentIndex
        if (!hidden) {
            items += StripItem.Chip(index, tab, group?.color?.toComposeColor())
        }
    }
    return items
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun GroupChip(
    group: TabGroup,
    count: Int,
    onClick: () -> Unit,
    onLongClick: () -> Unit,
) {
    val color = group.color.toComposeColor()
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .height(32.dp)
            .clip(SledgeTheme.Corner)
            .background(color.copy(alpha = if (group.collapsed) 0.28f else 0.16f))
            .combinedClickable(onClick = onClick, onLongClick = onLongClick)
            .padding(horizontal = 10.dp),
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(SledgeTheme.Corner)
                .background(color),
        )
        Spacer(Modifier.width(6.dp))
        Text(
            text = group.name,
            color = color,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
            maxLines = 1,
        )
        Spacer(Modifier.width(4.dp))
        Text(
            text = if (group.collapsed) count.toString() else "· $count",
            color = color.copy(alpha = 0.85f),
            fontSize = 11.sp,
        )
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun TabChip(
    tab: Tab,
    isActive: Boolean,
    groupColor: Color?,
    onSelect: () -> Unit,
    onClose: () -> Unit,
    onLongPress: () -> Unit,
) {
    val bg = if (isActive) SledgeTheme.Surface else Color.Transparent
    val textColor = when {
        tab.lifecycle == TabLifecycle.Hibernated -> SledgeTheme.Muted
        isActive -> SledgeTheme.Text
        else -> SledgeTheme.Dim
    }
    val label = tab.title.ifBlank {
        displayHost(tab.url).ifBlank { stringResource(R.string.untitled_tab) }
    }
    val mark = groupColor ?: if (isActive) SledgeTheme.Strike else Color.Transparent

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .height(36.dp)
            .width(168.dp)
            .clip(SledgeTheme.Corner)
            .background(bg)
            .combinedClickable(onClick = onSelect, onLongClick = onLongPress),
    ) {
        Box(
            modifier = Modifier
                .padding(start = 4.dp)
                .size(width = 3.dp, height = 16.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(mark),
        )
        LifecycleDot(tab)
        Text(
            text = label,
            color = textColor,
            fontSize = 13.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier
                .weight(1f)
                .padding(start = 6.dp),
        )
        if (isActive) {
            IconButton(onClick = onClose, modifier = Modifier.size(28.dp)) {
                Icon(
                    imageVector = Icons.Default.Close,
                    contentDescription = stringResource(R.string.close_tab),
                    tint = SledgeTheme.Dim,
                    modifier = Modifier.size(14.dp),
                )
            }
        } else {
            Spacer(Modifier.width(10.dp))
        }
    }
}

@Composable
private fun LifecycleDot(tab: Tab) {
    val color = when {
        tab.lifecycle == TabLifecycle.Hibernated -> SledgeTheme.Muted
        tab.lifecycle == TabLifecycle.Frozen -> SledgeTheme.Yellow
        tab.isLoading -> SledgeTheme.Strike
        else -> Color.Transparent
    }
    Box(
        modifier = Modifier
            .padding(start = 6.dp)
            .size(6.dp)
            .clip(SledgeTheme.Corner)
            .background(color),
    )
}

@Composable
private fun OverviewButton(count: Int, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .height(32.dp)
            .clip(SledgeTheme.Corner)
            .background(SledgeTheme.Surface)
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = stringResource(R.string.tab_count, count),
            color = SledgeTheme.Strike,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
        )
    }
}
