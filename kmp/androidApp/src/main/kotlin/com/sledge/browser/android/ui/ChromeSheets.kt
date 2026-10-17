package com.sledge.browser.android.ui

import android.webkit.WebView
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sledge.browser.android.R
import com.sledge.browser.android.TabDesk
import com.sledge.browser.android.TabMemory
import com.sledge.browser.android.displayHost
import com.sledge.browser.model.Tab
import com.sledge.browser.model.TabGroup
import com.sledge.browser.model.TabLifecycle
import kotlinx.coroutines.delay

sealed interface DeskSheet {
    data object Overview : DeskSheet
    data object Ports : DeskSheet
    data class TabActions(val index: Int) : DeskSheet
    data class GroupActions(val groupId: String) : DeskSheet
}

private data class DevPort(val name: String, val port: Int)

private val DevPorts = listOf(
    DevPort("Django", 8000),
    DevPort("React", 3000),
    DevPort("Vite", 5173),
    DevPort("Vue", 8080),
    DevPort("Flask", 5000),
    DevPort("Node", 3001),
    DevPort("Webpack", 8081),
    DevPort("Gleam", 8002),
)

/** Rewrite [current] onto localhost (or its existing host) at [port]. */
fun devServerUrl(current: String, port: Int): String {
    if (!current.startsWith("http://") && !current.startsWith("https://")) {
        return "http://localhost:$port/"
    }
    val scheme = current.substringBefore("://")
    val rest = current.substringAfter("://")
    val authority = rest.substringBefore("/").substringBefore("?")
    val host = authority.substringBefore(":")
    val pathAndQuery = if (rest.contains("/")) rest.substring(rest.indexOf("/")) else "/"
    return "$scheme://${host.ifBlank { "localhost" }}:$port$pathAndQuery"
}

@Composable
fun MemoryStatusBar(
    tabs: List<Tab>,
    group: TabGroup?,
    autoMemory: Boolean,
    canSleep: Boolean,
    onSleep: () -> Unit,
    onAutoMemory: (Boolean) -> Unit,
) {
    var rss by remember { mutableIntStateOf(TabMemory.rssMegabytes()) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(3_000)
            rss = TabMemory.rssMegabytes()
        }
    }
    val frozen = tabs.count { it.lifecycle == TabLifecycle.Frozen }
    val asleep = tabs.count { it.lifecycle == TabLifecycle.Hibernated }
    val summary = buildString {
        append(rss)
        append(" MB")
        if (frozen > 0) append("  ·  $frozen frozen")
        if (asleep > 0) append("  ·  $asleep asleep")
    }
    val pressure = when {
        rss >= 520 -> SledgeTheme.Red
        rss >= TabMemory.PRESSURE_MB -> SledgeTheme.Orange
        else -> SledgeTheme.Dim
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(32.dp)
            .background(SledgeTheme.Chrome)
            .padding(start = 12.dp, end = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (group != null) {
            Text(
                text = group.name,
                color = group.color.toComposeColor(),
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                modifier = Modifier.padding(end = 10.dp),
            )
        }
        Text(
            text = summary,
            color = pressure,
            fontSize = 12.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        if (canSleep) {
            Text(
                text = stringResource(R.string.sleep_tabs),
                color = SledgeTheme.Accent,
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
                modifier = Modifier
                    .clip(SledgeTheme.Corner)
                    .clickable(onClick = onSleep)
                    .padding(horizontal = 8.dp, vertical = 4.dp),
            )
        }
        Text(
            text = stringResource(R.string.auto_memory),
            color = if (autoMemory) SledgeTheme.Background else SledgeTheme.Dim,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
            modifier = Modifier
                .padding(end = 8.dp)
                .clip(SledgeTheme.Corner)
                .background(if (autoMemory) SledgeTheme.Accent else SledgeTheme.Surface)
                .clickable { onAutoMemory(!autoMemory) }
                .padding(horizontal = 8.dp, vertical = 4.dp),
        )
    }
}

@Composable
fun SleepingTab(tab: Tab, onWake: () -> Unit, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(SledgeTheme.Background)
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = stringResource(R.string.tab_asleep),
            color = SledgeTheme.Accent,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium,
            letterSpacing = 1.2.sp,
        )
        Text(
            text = tab.title.ifBlank { stringResource(R.string.untitled_tab) },
            color = SledgeTheme.Text,
            fontSize = 20.sp,
            fontWeight = FontWeight.Medium,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(top = 10.dp),
        )
        val host = displayHost(tab.url)
        if (host.isNotEmpty()) {
            Text(
                text = host,
                color = SledgeTheme.Dim,
                fontSize = 14.sp,
                modifier = Modifier.padding(top = 4.dp),
            )
        }
        TextButton(onClick = onWake, modifier = Modifier.padding(top = 16.dp)) {
            Text(stringResource(R.string.wake_tab), color = SledgeTheme.Background, modifier = Modifier
                .clip(SledgeTheme.Corner)
                .background(SledgeTheme.Accent)
                .padding(horizontal = 22.dp, vertical = 8.dp))
        }
    }
}

@Composable
fun FindBar(webView: WebView?, onClose: () -> Unit) {
    var query by remember { mutableStateOf("") }
    var label by remember { mutableStateOf("") }

    DisposableEffect(webView) {
        webView?.setFindListener { ordinal, count, done ->
            if (done) label = if (count <= 0) "0" else "${ordinal + 1}/$count"
        }
        onDispose { webView?.clearMatches() }
    }
    LaunchedEffect(query, webView) {
        if (query.isBlank()) {
            webView?.clearMatches()
            label = ""
        } else {
            webView?.findAllAsync(query)
        }
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(SledgeTheme.Surface)
            .padding(start = 12.dp, end = 4.dp, top = 4.dp, bottom = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        BasicTextField(
            value = query,
            onValueChange = { query = it },
            singleLine = true,
            textStyle = TextStyle(color = SledgeTheme.Text, fontSize = 15.sp),
            cursorBrush = SolidColor(SledgeTheme.Accent),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            keyboardActions = KeyboardActions(onSearch = { webView?.findNext(true) }),
            modifier = Modifier.weight(1f),
            decorationBox = { inner ->
                Box(contentAlignment = Alignment.CenterStart) {
                    if (query.isEmpty()) {
                        Text(stringResource(R.string.find_in_page), color = SledgeTheme.Muted, fontSize = 15.sp)
                    }
                    inner()
                }
            },
        )
        if (label.isNotEmpty()) {
            Text(label, color = SledgeTheme.Dim, fontSize = 12.sp, modifier = Modifier.padding(horizontal = 8.dp))
        }
        IconButton(onClick = { webView?.findNext(false) }, modifier = Modifier.size(36.dp)) {
            Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.find_previous), tint = SledgeTheme.Dim)
        }
        IconButton(onClick = { webView?.findNext(true) }, modifier = Modifier.size(36.dp)) {
            Icon(Icons.AutoMirrored.Filled.ArrowForward, stringResource(R.string.find_next), tint = SledgeTheme.Dim)
        }
        IconButton(onClick = onClose, modifier = Modifier.size(36.dp)) {
            Icon(Icons.Default.Close, stringResource(R.string.close_find), tint = SledgeTheme.Dim)
        }
    }
}

@Composable
fun TabOverviewSheet(
    desk: TabDesk,
    onSelect: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    var query by remember { mutableStateOf("") }
    val tabs = desk.tabs
    val groups = desk.groups
    val shown = tabs.mapIndexed { index, tab -> index to tab }.filter { (_, tab) ->
        query.isBlank() ||
            tab.title.contains(query, ignoreCase = true) ||
            tab.url.contains(query, ignoreCase = true) ||
            groups.find { it.id == tab.groupId }?.name?.contains(query, ignoreCase = true) == true
    }

    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 20.dp)) {
        Text(
            text = stringResource(R.string.tabs),
            style = MaterialTheme.typography.titleLarge,
            color = SledgeTheme.Text,
        )
        MemoryStatusBar(
            tabs = tabs,
            group = groups.find { it.id == desk.current?.groupId },
            autoMemory = desk.autoMemory,
            canSleep = tabs.indices.any { index ->
                index != desk.currentIndex &&
                    tabs[index].lifecycle != TabLifecycle.Hibernated &&
                    groups.find { it.id == tabs[index].groupId }?.keepActive != true
            },
            onSleep = { desk.sleepBackground() },
            onAutoMemory = { desk.updateAutoMemory(it) },
        )
        SearchField(
            value = query,
            onValueChange = { query = it },
            placeholder = stringResource(R.string.search_tabs),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TextButton(onClick = { desk.wakeAll() }) {
                Text(stringResource(R.string.wake_all), color = SledgeTheme.Accent)
            }
            TextButton(onClick = {
                desk.sleepBackground()
                onDismiss()
            }) {
                Text(stringResource(R.string.sleep_tabs), color = SledgeTheme.Accent)
            }
        }
        if (shown.isEmpty()) {
            Text(
                stringResource(R.string.no_tabs_match),
                color = SledgeTheme.Dim,
                modifier = Modifier.padding(vertical = 24.dp),
            )
        } else {
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth().heightIn(max = 480.dp),
            ) {
                itemsIndexed(shown, key = { _, pair -> pair.second.id }) { _, pair ->
                    val (index, tab) = pair
                    OverviewCard(
                        tab = tab,
                        group = groups.find { it.id == tab.groupId },
                        selected = index == desk.currentIndex,
                        onOpen = { onSelect(index) },
                        onClose = {
                            val live = desk.tabs.indexOfFirst { it.id == tab.id }
                            if (live >= 0) desk.close(live)
                        },
                    )
                }
            }
        }
    }
}

@Composable
private fun OverviewCard(
    tab: Tab,
    group: TabGroup?,
    selected: Boolean,
    onOpen: () -> Unit,
    onClose: () -> Unit,
) {
    val mark = group?.color?.toComposeColor() ?: SledgeTheme.Elevated
    Column(
        modifier = Modifier
            .clip(SledgeTheme.Corner)
            .background(if (selected) SledgeTheme.Elevated else SledgeTheme.Background)
            .clickable(onClick = onOpen),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(4.dp)
                .background(mark),
        )
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(start = 10.dp, top = 8.dp, end = 2.dp)) {
            Text(
                text = tab.title.ifBlank { stringResource(R.string.untitled_tab) },
                color = SledgeTheme.Text,
                fontSize = 14.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            IconButton(onClick = onClose, modifier = Modifier.size(28.dp)) {
                Icon(Icons.Default.Close, stringResource(R.string.close_tab), tint = SledgeTheme.Dim, modifier = Modifier.size(14.dp))
            }
        }
        Text(
            text = displayHost(tab.url).ifBlank { stringResource(R.string.untitled_tab) },
            color = SledgeTheme.Dim,
            fontSize = 12.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(start = 10.dp, end = 10.dp),
        )
        Text(
            text = lifecycleLabel(tab, group),
            color = mark,
            fontSize = 11.sp,
            modifier = Modifier.padding(start = 10.dp, end = 10.dp, top = 4.dp, bottom = 10.dp),
        )
    }
}

@Composable
private fun lifecycleLabel(tab: Tab, group: TabGroup?): String {
    val state = when (tab.lifecycle) {
        TabLifecycle.Active -> stringResource(R.string.state_live)
        TabLifecycle.Frozen -> stringResource(R.string.state_frozen)
        TabLifecycle.Hibernated -> stringResource(R.string.state_asleep)
    }
    return if (group == null) state else "${group.name}  ·  $state"
}

@Composable
fun DevPortsSheet(
    currentUrl: String,
    onOpen: (url: String, newTab: Boolean) -> Unit,
) {
    var newTab by remember { mutableStateOf(false) }
    var custom by remember { mutableStateOf("") }
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 24.dp)) {
        Text(
            text = stringResource(R.string.dev_ports),
            style = MaterialTheme.typography.titleLarge,
            color = SledgeTheme.Text,
        )
        Text(
            text = stringResource(R.string.dev_ports_summary),
            color = SledgeTheme.Dim,
            fontSize = 13.sp,
            modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
        )
        SettingToggle(
            title = stringResource(R.string.open_in_new_tab),
            summary = stringResource(R.string.open_in_new_tab_summary),
            checked = newTab,
            onCheckedChange = { newTab = it },
        )
        DevPorts.chunked(2).forEach { row ->
            Row(
                modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                row.forEach { port ->
                    PortCard(
                        name = port.name,
                        port = port.port,
                        modifier = Modifier.weight(1f),
                        onClick = { onOpen(devServerUrl(currentUrl, port.port), newTab) },
                    )
                }
                if (row.size == 1) Box(Modifier.weight(1f))
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(top = 4.dp)) {
            BasicTextField(
                value = custom,
                onValueChange = { custom = it.filter { ch -> ch.isDigit() }.take(5) },
                singleLine = true,
                textStyle = TextStyle(color = SledgeTheme.Text, fontSize = 15.sp),
                cursorBrush = SolidColor(SledgeTheme.Accent),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Go),
                keyboardActions = KeyboardActions(onGo = {
                    custom.toIntOrNull()?.takeIf { it in 1..65535 }?.let { port ->
                        onOpen(devServerUrl(currentUrl, port), newTab)
                    }
                }),
                modifier = Modifier
                    .weight(1f)
                    .height(42.dp)
                    .clip(SledgeTheme.Corner)
                    .background(SledgeTheme.Background)
                    .padding(horizontal = 12.dp),
                decorationBox = { inner ->
                    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterStart) {
                        if (custom.isEmpty()) {
                            Text(stringResource(R.string.custom_port), color = SledgeTheme.Muted, fontSize = 15.sp)
                        }
                        inner()
                    }
                },
            )
            TextButton(
                onClick = {
                    custom.toIntOrNull()?.takeIf { it in 1..65535 }?.let { port ->
                        onOpen(devServerUrl(currentUrl, port), newTab)
                    }
                },
                modifier = Modifier.padding(start = 8.dp),
            ) {
                Text(stringResource(R.string.open_port), color = SledgeTheme.Accent)
            }
        }
    }
}

@Composable
private fun PortCard(name: String, port: Int, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Column(
        modifier = modifier
            .clip(SledgeTheme.Corner)
            .background(SledgeTheme.Background)
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 12.dp),
    ) {
        Text(name, color = SledgeTheme.Text, fontSize = 15.sp, fontWeight = FontWeight.Medium)
        Text(":$port", color = SledgeTheme.Accent, fontSize = 13.sp, modifier = Modifier.padding(top = 2.dp))
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun TabActionsSheet(desk: TabDesk, index: Int, onDismiss: () -> Unit) {
    val tab = desk.tabs.getOrNull(index) ?: return
    var naming by remember { mutableStateOf(false) }
    var name by remember { mutableStateOf("") }
    var color by remember { mutableStateOf(SledgeTheme.groupColors.first()) }
    val suggestions = stringArrayResource(R.array.group_suggestions)

    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 24.dp)) {
        Text(
            text = tab.title.ifBlank { stringResource(R.string.untitled_tab) },
            color = SledgeTheme.Text,
            style = MaterialTheme.typography.titleLarge,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = displayHost(tab.url),
            color = SledgeTheme.Dim,
            fontSize = 13.sp,
            modifier = Modifier.padding(top = 2.dp, bottom = 12.dp),
        )
        if (tab.lifecycle == TabLifecycle.Hibernated) {
            ActionRow(stringResource(R.string.wake_tab)) {
                desk.wake(index)
                onDismiss()
            }
        } else {
            ActionRow(stringResource(R.string.sleep_this_tab)) {
                desk.hibernate(index)
                onDismiss()
            }
        }
        Text(
            text = stringResource(R.string.group),
            color = SledgeTheme.Dim,
            fontSize = 12.sp,
            modifier = Modifier.padding(top = 12.dp, bottom = 8.dp),
        )
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            desk.groups.forEach { group ->
                val selected = tab.groupId == group.id
                GroupPick(
                    label = group.name,
                    color = group.color.toComposeColor(),
                    selected = selected,
                    onClick = {
                        desk.assignGroup(index, if (selected) null else group.id)
                        onDismiss()
                    },
                )
            }
            GroupPick(
                label = stringResource(R.string.new_group),
                color = SledgeTheme.Accent,
                selected = naming,
                onClick = { naming = !naming },
            )
        }
        if (tab.groupId != null) {
            TextButton(onClick = {
                desk.assignGroup(index, null)
                onDismiss()
            }) {
                Text(stringResource(R.string.remove_from_group), color = SledgeTheme.Dim)
            }
        }
        if (naming) {
            BasicTextField(
                value = name,
                onValueChange = { name = it },
                singleLine = true,
                textStyle = TextStyle(color = SledgeTheme.Text, fontSize = 15.sp),
                cursorBrush = SolidColor(SledgeTheme.Accent),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 12.dp)
                    .height(42.dp)
                    .clip(SledgeTheme.Corner)
                    .background(SledgeTheme.Background)
                    .padding(horizontal = 12.dp),
                decorationBox = { inner ->
                    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterStart) {
                        if (name.isEmpty()) {
                            Text(stringResource(R.string.group_name), color = SledgeTheme.Muted, fontSize = 15.sp)
                        }
                        inner()
                    }
                },
            )
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(top = 10.dp),
            ) {
                suggestions.forEach { suggestion ->
                    Text(
                        text = suggestion,
                        color = SledgeTheme.Dim,
                        fontSize = 13.sp,
                        modifier = Modifier
                            .clip(SledgeTheme.Corner)
                            .background(SledgeTheme.Background)
                            .clickable { name = suggestion }
                            .padding(horizontal = 10.dp, vertical = 6.dp),
                    )
                }
            }
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(top = 10.dp),
            ) {
                SledgeTheme.groupColors.forEach { swatch ->
                    val c = swatch.toComposeColor()
                    Box(
                        modifier = Modifier
                            .size(28.dp)
                            .clip(SledgeTheme.Corner)
                            .background(c)
                            .then(
                                if (swatch == color) Modifier.border(2.dp, SledgeTheme.Text, SledgeTheme.Corner)
                                else Modifier,
                            )
                            .clickable { color = swatch },
                    )
                }
            }
            TextButton(onClick = {
                desk.createGroup(name, color, index)
                onDismiss()
            }) {
                Text(stringResource(R.string.create_group), color = SledgeTheme.Accent)
            }
        }
        ActionRow(stringResource(R.string.close_tab)) {
            desk.close(index)
            onDismiss()
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun GroupActionsSheet(desk: TabDesk, groupId: String, onDismiss: () -> Unit) {
    val group = desk.groups.find { it.id == groupId } ?: return
    var name by remember(group.id) { mutableStateOf(group.name) }
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 24.dp)) {
        Text(group.name, color = group.color.toComposeColor(), style = MaterialTheme.typography.titleLarge)
        BasicTextField(
            value = name,
            onValueChange = { name = it },
            singleLine = true,
            textStyle = TextStyle(color = SledgeTheme.Text, fontSize = 15.sp),
            cursorBrush = SolidColor(SledgeTheme.Accent),
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
            keyboardActions = KeyboardActions(onDone = { desk.renameGroup(groupId, name) }),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 12.dp)
                .height(42.dp)
                .clip(SledgeTheme.Corner)
                .background(SledgeTheme.Background)
                .padding(horizontal = 12.dp),
            decorationBox = { inner ->
                Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterStart) { inner() }
            },
        )
        TextButton(onClick = { desk.renameGroup(groupId, name) }) {
            Text(stringResource(R.string.rename_group), color = SledgeTheme.Accent)
        }
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(bottom = 8.dp)) {
            SledgeTheme.groupColors.forEach { swatch ->
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .clip(SledgeTheme.Corner)
                        .background(swatch.toComposeColor())
                        .then(
                            if (swatch == group.color) Modifier.border(2.dp, SledgeTheme.Text, SledgeTheme.Corner)
                            else Modifier,
                        )
                        .clickable { desk.recolorGroup(groupId, swatch) },
                )
            }
        }
        SettingToggle(
            title = stringResource(R.string.keep_awake),
            summary = stringResource(R.string.keep_awake_summary),
            checked = group.keepActive,
            onCheckedChange = { desk.toggleKeepActive(groupId, it) },
        )
        ActionRow(stringResource(if (group.collapsed) R.string.expand_group else R.string.collapse_group)) {
            desk.toggleCollapsed(groupId)
            onDismiss()
        }
        ActionRow(stringResource(R.string.dissolve_group)) {
            desk.dissolveGroup(groupId)
            onDismiss()
        }
    }
}

@Composable
private fun GroupPick(label: String, color: Color, selected: Boolean, onClick: () -> Unit) {
    Text(
        text = label,
        color = if (selected) SledgeTheme.Background else color,
        fontSize = 13.sp,
        fontWeight = FontWeight.Medium,
        modifier = Modifier
            .clip(SledgeTheme.Corner)
            .background(if (selected) color else color.copy(alpha = 0.16f))
            .clickable(onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 6.dp),
    )
}

@Composable
private fun ActionRow(label: String, onClick: () -> Unit) {
    Text(
        text = label,
        color = SledgeTheme.Text,
        fontSize = 16.sp,
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 12.dp),
    )
}
