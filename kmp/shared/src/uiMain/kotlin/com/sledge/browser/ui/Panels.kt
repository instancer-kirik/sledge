package com.sledge.browser.ui

import com.sledge.browser.Strings

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.sledge.browser.history.HistoryEntry
import com.sledge.browser.model.Bookmark
import com.sledge.browser.model.BrowserSettings

private val NordText = SledgeTheme.Text
private val NordMuted = SledgeTheme.Dim
private val NordAccent = SledgeTheme.Strike
private val NordField = SledgeTheme.Background
private val NordOutline = SledgeTheme.Muted

@Composable
fun HistoryPanel(
    entries: List<HistoryEntry>,
    onOpen: (String) -> Unit,
    onDelete: (Long) -> Unit,
    onClear: () -> Unit,
) {
    var query by rememberSaveable { mutableStateOf("") }
    val shown = if (query.isBlank()) {
        entries
    } else {
        entries.filter {
            it.title.contains(query, ignoreCase = true) ||
                it.url.contains(query, ignoreCase = true)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .padding(bottom = 24.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = Strings.history,
                style = MaterialTheme.typography.titleLarge,
                color = NordText,
                modifier = Modifier.weight(1f),
            )
            if (entries.isNotEmpty()) {
                TextButton(onClick = onClear) {
                    Text(Strings.clear_history, color = NordAccent)
                }
            }
        }
        SearchField(
            value = query,
            onValueChange = { query = it },
            placeholder = Strings.search_history,
        )
        if (shown.isEmpty()) {
            Text(
                text = Strings.no_history,
                color = NordMuted,
                modifier = Modifier.padding(vertical = 28.dp),
            )
        } else {
            LazyColumn(modifier = Modifier.fillMaxWidth().heightIn(max = 480.dp)) {
                items(shown, key = { it.id }) { entry ->
                    PageRow(
                        title = entry.title,
                        url = entry.url,
                        meta = formatAge(entry.visitedAt),
                        onOpen = { onOpen(entry.url) },
                        onRemove = { onDelete(entry.id) },
                    )
                }
            }
        }
    }
}

@Composable
fun BookmarksPanel(
    bookmarks: List<Bookmark>,
    onOpen: (String) -> Unit,
    onDelete: (Long) -> Unit,
) {
    var query by rememberSaveable { mutableStateOf("") }
    val shown = if (query.isBlank()) {
        bookmarks
    } else {
        bookmarks.filter {
            it.title.contains(query, ignoreCase = true) ||
                it.url.contains(query, ignoreCase = true)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .padding(bottom = 24.dp),
    ) {
        Text(
            text = Strings.bookmarks,
            style = MaterialTheme.typography.titleLarge,
            color = NordText,
            modifier = Modifier.padding(bottom = 8.dp),
        )
        SearchField(
            value = query,
            onValueChange = { query = it },
            placeholder = Strings.search_bookmarks,
        )
        if (shown.isEmpty()) {
            Text(
                text = Strings.no_bookmarks,
                color = NordMuted,
                modifier = Modifier.padding(vertical = 28.dp),
            )
        } else {
            LazyColumn(modifier = Modifier.fillMaxWidth().heightIn(max = 480.dp)) {
                items(shown, key = { it.id }) { bookmark ->
                    PageRow(
                        title = bookmark.title,
                        url = bookmark.url,
                        meta = null,
                        onOpen = { onOpen(bookmark.url) },
                        onRemove = { onDelete(bookmark.id) },
                    )
                }
            }
        }
    }
}

@Composable
fun SettingsPanel(
    settings: BrowserSettings,
    status: String,
    locationSites: Int,
    onChange: (BrowserSettings) -> Unit,
    onClearLocations: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .padding(bottom = 28.dp),
    ) {
        Text(
            text = Strings.settings,
            style = MaterialTheme.typography.titleLarge,
            color = NordText,
            modifier = Modifier.padding(bottom = 8.dp),
        )
        SettingToggle(
            title = Strings.block_ads,
            summary = Strings.block_ads_summary( status),
            checked = settings.blockAds,
            onCheckedChange = { onChange(settings.copy(blockAds = it)) },
        )
        SettingToggle(
            title = Strings.javascript,
            summary = Strings.javascript_summary,
            checked = settings.javascriptEnabled,
            onCheckedChange = { onChange(settings.copy(javascriptEnabled = it)) },
        )
        SettingToggle(
            title = Strings.dark_mode,
            summary = Strings.dark_mode_summary,
            checked = settings.darkMode,
            onCheckedChange = { onChange(settings.copy(darkMode = it)) },
        )
        SettingToggle(
            title = Strings.mixed_content,
            summary = Strings.mixed_content_summary,
            checked = settings.blockMixedContent,
            onCheckedChange = { onChange(settings.copy(blockMixedContent = it)) },
        )
        SettingToggle(
            title = Strings.dangerous_ports,
            summary = Strings.dangerous_ports_summary,
            checked = settings.blockDangerousPorts,
            onCheckedChange = { onChange(settings.copy(blockDangerousPorts = it)) },
        )
        if (locationSites > 0) {
            SettingToggle(
                title = Strings.location_sites,
                summary = Strings.location_sites_summary( locationSites),
                checked = true,
                onCheckedChange = { onClearLocations() },
            )
        }
    }
}

@Composable
internal fun SearchField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        singleLine = true,
        placeholder = { Text(placeholder, color = NordOutline) },
        shape = SledgeTheme.Corner,
        colors = OutlinedTextFieldDefaults.colors(
            focusedTextColor = NordText,
            unfocusedTextColor = NordText,
            focusedBorderColor = NordAccent,
            unfocusedBorderColor = NordOutline,
            cursorColor = NordAccent,
            focusedContainerColor = NordField,
            unfocusedContainerColor = NordField,
        ),
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 8.dp),
    )
}

@Composable
private fun PageRow(
    title: String,
    url: String,
    meta: String?,
    onOpen: () -> Unit,
    onRemove: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onOpen)
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title.ifBlank { url },
                color = NordText,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodyLarge,
            )
            Text(
                text = if (meta != null) "$url  ·  $meta" else url,
                color = NordMuted,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodySmall,
            )
        }
        IconButton(onClick = onRemove) {
            Icon(
                imageVector = if (meta != null) Icons.Default.Delete else Icons.Default.Close,
                contentDescription = Strings.delete,
                tint = NordMuted,
            )
        }
    }
}

@Composable
internal fun SettingToggle(
    title: String,
    summary: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onCheckedChange(!checked) }
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f).padding(end = 12.dp)) {
            Text(title, color = NordText, style = MaterialTheme.typography.titleMedium)
            Text(summary, color = NordMuted, style = MaterialTheme.typography.bodySmall)
        }
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(
                checkedTrackColor = NordAccent,
                checkedThumbColor = NordField,
                uncheckedTrackColor = NordOutline,
                uncheckedThumbColor = NordMuted,
                uncheckedBorderColor = NordOutline,
            ),
        )
    }
}

@Composable
fun ExtensionsPanel(
    extensions: ExtensionCatalog,
    onInstall: ((ByteArray) -> Unit) -> Unit,
) {
    var message by rememberSaveable { mutableStateOf("") }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .padding(bottom = 24.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = Strings.extensions,
                style = MaterialTheme.typography.titleLarge,
                color = NordText,
                modifier = Modifier.weight(1f),
            )
            TextButton(onClick = {
                onInstall { bytes ->
                    message = extensions.install(bytes).orEmpty()
                }
            }) {
                Text(Strings.install_extension, color = NordAccent)
            }
        }
        Text(
            text = Strings.extensions_summary,
            color = NordMuted,
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(bottom = 8.dp),
        )
        if (message.isNotEmpty()) {
            Text(message, color = NordAccent, modifier = Modifier.padding(bottom = 8.dp))
        }
        if (extensions.items.isEmpty()) {
            Text(Strings.extensions_empty, color = NordMuted)
        }
        extensions.items.forEach { item ->
            Row(
                modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(item.name, color = NordText)
                    if (item.version.isNotEmpty()) {
                        Text(item.version, color = NordMuted, style = MaterialTheme.typography.bodySmall)
                    }
                }
                Switch(
                    checked = item.enabled,
                    onCheckedChange = { extensions.setEnabled(item.id, it) },
                    colors = SwitchDefaults.colors(
                        checkedTrackColor = NordAccent,
                        checkedThumbColor = NordField,
                        uncheckedTrackColor = NordOutline,
                        uncheckedThumbColor = NordMuted,
                        uncheckedBorderColor = NordOutline,
                    ),
                )
                IconButton(onClick = { extensions.remove(item.id) }) {
                    Icon(Icons.Default.Delete, contentDescription = Strings.remove_extension, tint = NordMuted)
                }
            }
        }
    }
}

private fun formatAge(visitedAt: Long): String {
    val minutes = (System.currentTimeMillis() - visitedAt) / 60_000
    return when {
        minutes < 1 -> "Just now"
        minutes < 60 -> "${minutes}m ago"
        minutes < 60 * 24 -> "${minutes / 60}h ago"
        else -> "${minutes / (60 * 24)}d ago"
    }
}
