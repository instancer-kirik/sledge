package com.sledge.browser.android.ui

import android.view.ViewGroup
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.BottomSheetDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.sledge.browser.adblock.AdBlocker
import com.sledge.browser.android.AddressInput
import com.sledge.browser.android.BrowserStore
import com.sledge.browser.android.addressBarTarget
import com.sledge.browser.android.MainActivity
import com.sledge.browser.android.R
import com.sledge.browser.android.START_PAGE
import com.sledge.browser.android.TabDesk
import com.sledge.browser.android.displayHost
import com.sledge.browser.android.displayUrl
import com.sledge.browser.android.engine.BraveAdBlock
import com.sledge.browser.android.engine.SledgeWebView
import com.sledge.browser.android.engine.launchAddressAction
import com.sledge.browser.model.Tab
import com.sledge.browser.model.TabLifecycle
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private enum class Panel { History, Bookmarks, Settings }

/**
 * Root browser screen: address bar, the active [SledgeWebView], grouped tab
 * strip, memory status, and the ring menu plus history / bookmarks / settings.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BrowserScreen(
    desk: TabDesk,
    store: BrowserStore,
    adBlocker: AdBlocker,
    brave: BraveAdBlock,
) {
    val tabs = desk.tabs
    val currentIndex = desk.currentIndex
    val groups = desk.groups
    val context = LocalContext.current
    val focusManager = LocalFocusManager.current
    val keyboard = LocalSoftwareKeyboardController.current
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    val currentTab = tabs.getOrNull(currentIndex)

    val webViewCache = remember { mutableMapOf<String, SledgeWebView>() }
    val progressByTab = remember { mutableStateMapOf<String, Int>() }

    var urlInput by remember { mutableStateOf(TextFieldValue("")) }
    var urlFocused by remember { mutableStateOf(false) }
    var showRingMenu by remember { mutableStateOf(false) }
    var showListMenu by remember { mutableStateOf(false) }
    var panel by remember { mutableStateOf<Panel?>(null) }
    var sheet by remember { mutableStateOf<DeskSheet?>(null) }
    var findOpen by remember { mutableStateOf(false) }
    var fullscreenView by remember { mutableStateOf<android.view.View?>(null) }
    var skipSettingsReload by remember { mutableStateOf(true) }
    var appliedSettings by remember { mutableStateOf(store.settings) }
    var canBack by remember { mutableStateOf(false) }
    var canForward by remember { mutableStateOf(false) }
    val pageActions = rememberPageActions(snackbar, store)

    fun syncNav(webView: SledgeWebView?) {
        canBack = webView?.canGoBack() == true
        canForward = webView?.canGoForward() == true
    }

    LaunchedEffect(currentTab?.id, currentTab?.url, urlFocused) {
        if (!urlFocused) urlInput = TextFieldValue(displayHost(currentTab?.url.orEmpty()))
    }

    val tabIds = tabs.map { it.id }
    LaunchedEffect(tabIds) {
        val live = tabIds.toSet()
        webViewCache.keys.filter { it !in live }.forEach { id ->
            webViewCache.remove(id)?.let { view ->
                (view.parent as? ViewGroup)?.removeView(view)
                view.destroy()
            }
            progressByTab.remove(id)
        }
    }

    val lifecycleKey = tabs.joinToString(separator = "|") { "${it.id}:${it.lifecycle}" }
    LaunchedEffect(lifecycleKey, currentTab?.id) {
        val currentId = currentTab?.id
        tabs.forEach { tab ->
            val view = webViewCache[tab.id]
            when (tab.lifecycle) {
                TabLifecycle.Hibernated -> if (view != null) {
                    webViewCache.remove(tab.id)
                    progressByTab.remove(tab.id)
                    (view.parent as? ViewGroup)?.removeView(view)
                    view.destroy()
                }
                TabLifecycle.Frozen -> view?.onPause()
                TabLifecycle.Active -> if (tab.id == currentId) view?.onResume()
            }
        }
        syncNav(currentId?.let { webViewCache[it] })
    }

    LaunchedEffect(desk.autoMemory) {
        if (!desk.autoMemory) return@LaunchedEffect
        while (true) {
            delay(15_000)
            desk.applyMemory()
        }
    }

    LaunchedEffect(store.settings) {
        val updated = store.settings
        adBlocker.enabled = updated.blockAds
        brave.enabled = updated.blockAds
        webViewCache.values.forEach { it.applySettings(updated) }
        val reload = !skipSettingsReload && (
            appliedSettings.javascriptEnabled != updated.javascriptEnabled ||
                appliedSettings.darkMode != updated.darkMode ||
                appliedSettings.blockAds != updated.blockAds
            )
        appliedSettings = updated
        skipSettingsReload = false
        if (reload) webViewCache.values.forEach { it.reload() }
    }

    fun createWebView(tab: Tab): SledgeWebView = webViewCache.getOrPut(tab.id) {
        SledgeWebView(
            context = context,
            settings = store.settings,
            adBlocker = adBlocker,
            brave = brave,
            onCreateTab = { initialUrl ->
                val created = desk.open(initialUrl ?: START_PAGE)
                createWebView(created)
            },
        ).also { wv ->
            wv.onPageStartedCallback = { url ->
                desk.update(tab.id, url, null, true)
            }
            wv.onPageFinishedCallback = { url, title ->
                desk.update(tab.id, url, title, false)
                store.recordVisit(url, title ?: "")
                progressByTab[tab.id] = 100
                if (tab.id == desk.current?.id) syncNav(wv)
            }
            wv.sledgeWebChromeClient.onProgress = { progress ->
                progressByTab[tab.id] = progress
            }
            wv.sledgeWebChromeClient.onTitle = { title ->
                desk.update(tab.id, wv.url ?: tab.url, title, null)
            }
            wv.sledgeWebChromeClient.onEnterFullscreen = { view, _ ->
                fullscreenView = view
            }
            wv.sledgeWebChromeClient.onExitFullscreen = {
                fullscreenView = null
            }
            wv.sledgeWebChromeClient.onShowFileChooser = pageActions.onShowFileChooser
            wv.sledgeWebChromeClient.onPermissionRequest = pageActions.onPermissionRequest
            wv.sledgeWebChromeClient.onGeolocation = pageActions.onGeolocation
            wv.onDownload = { url, userAgent, contentDisposition, mimeType, contentLength ->
                pageActions.onDownload(wv, url, userAgent, contentDisposition, mimeType, contentLength)
            }
            if (tab.url.isNotBlank()) wv.loadUrl(tab.url)
        }
    }

    val asleep = currentTab?.lifecycle == TabLifecycle.Hibernated
    val activeWebView: SledgeWebView? = currentTab?.takeUnless { asleep }?.let { createWebView(it) }
    val progress = currentTab?.let { progressByTab[it.id] }
        ?: if (currentTab?.isLoading == true) 0 else 100
    val pageUrl = currentTab?.url.orEmpty()
    val canBookmark = pageUrl.startsWith("http://") || pageUrl.startsWith("https://")
    val bookmarked = canBookmark && store.isBookmarked(pageUrl)

    fun rejectBlockedAddress() {
        scope.launch { snackbar.showSnackbar(context.getString(R.string.address_blocked)) }
    }

    fun runAddressAction(raw: String) {
        focusManager.clearFocus()
        keyboard?.hide()
        if (!launchAddressAction(context, raw)) {
            scope.launch { snackbar.showSnackbar(context.getString(R.string.address_no_app)) }
        }
    }

    fun submitUrl() {
        when (val target = addressBarTarget(urlInput.text)) {
            AddressInput.Empty -> return
            AddressInput.Blocked -> {
                rejectBlockedAddress()
                return
            }
            is AddressInput.Action -> runAddressAction(target.text)
            is AddressInput.Open -> {
                focusManager.clearFocus()
                keyboard?.hide()
                if (asleep) {
                    val id = currentTab?.id ?: return
                    desk.update(id, target.text, null, true)
                    desk.wake(currentIndex)
                } else {
                    activeWebView?.loadUrl(target.text)
                }
            }
        }
    }

    fun openUrl(url: String, newTab: Boolean = false) {
        val target = when (val parsed = addressBarTarget(url)) {
            is AddressInput.Action -> {
                runAddressAction(parsed.text)
                return
            }
            is AddressInput.Open -> parsed.text
            AddressInput.Blocked -> {
                rejectBlockedAddress()
                return
            }
            AddressInput.Empty -> return
        }
        panel = null
        sheet = null
        when {
            newTab -> desk.open(target)
            asleep -> {
                val id = currentTab?.id ?: return
                desk.update(id, target, null, true)
                desk.wake(currentIndex)
            }
            else -> activeWebView?.loadUrl(target)
        }
    }

    BackHandler(
        enabled = fullscreenView != null || panel != null || sheet != null || showRingMenu ||
            showListMenu || findOpen || activeWebView?.canGoBack() == true,
    ) {
        when {
            fullscreenView != null -> activeWebView?.sledgeWebChromeClient?.exitFullscreen()
            findOpen -> findOpen = false
            showListMenu -> showListMenu = false
            panel != null -> panel = null
            sheet != null -> sheet = null
            showRingMenu -> showRingMenu = false
            else -> activeWebView?.goBack()
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            webViewCache.values.forEach { view ->
                (view.parent as? ViewGroup)?.removeView(view)
                view.destroy()
            }
            webViewCache.clear()
        }
    }

    val activity = context as? MainActivity
    SideEffect {
        activity?.onTwoFingerDoubleTap = { showRingMenu = true }
    }
    DisposableEffect(activity) {
        onDispose { activity?.onTwoFingerDoubleTap = null }
    }

    val bookmarkSaved = stringResource(R.string.bookmark_added)
    val bookmarkRemoved = stringResource(R.string.bookmark_removed)

    Surface(color = SledgeTheme.Background, modifier = Modifier.fillMaxSize()) {
        Box(modifier = Modifier.fillMaxSize()) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .background(SledgeTheme.Chrome)
                    .windowInsetsPadding(WindowInsets.safeDrawing),
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(start = 4.dp, end = 6.dp, top = 8.dp, bottom = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    ChromeButton(
                        onClick = { activeWebView?.goBack() },
                        icon = Icons.AutoMirrored.Filled.ArrowBack,
                        description = stringResource(R.string.go_back),
                        tint = if (canBack) SledgeTheme.Dim else SledgeTheme.Muted,
                    )
                    ChromeButton(
                        onClick = { activeWebView?.goForward() },
                        icon = Icons.AutoMirrored.Filled.ArrowForward,
                        description = stringResource(R.string.go_forward),
                        tint = if (canForward) SledgeTheme.Dim else SledgeTheme.Muted,
                    )
                    Row(
                        modifier = Modifier
                            .weight(1f)
                            .height(44.dp)
                            .clip(SledgeTheme.Corner)
                            .background(SledgeTheme.Surface)
                            .padding(start = 14.dp, end = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            imageVector = when {
                                urlFocused -> Icons.Default.Search
                                pageUrl.startsWith("https://") -> Icons.Default.Lock
                                else -> Icons.Default.Search
                            },
                            contentDescription = null,
                            tint = if (pageUrl.startsWith("https://") && !urlFocused) {
                                SledgeTheme.Accent
                            } else {
                                SledgeTheme.Dim
                            },
                            modifier = Modifier.size(16.dp),
                        )
                        BasicTextField(
                            value = urlInput,
                            onValueChange = { urlInput = it },
                            singleLine = true,
                            textStyle = TextStyle(
                                color = SledgeTheme.Text,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Medium,
                            ),
                            cursorBrush = SolidColor(SledgeTheme.Accent),
                            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Go),
                            keyboardActions = KeyboardActions(
                                onGo = { submitUrl() },
                                onDone = { submitUrl() },
                            ),
                            modifier = Modifier
                                .weight(1f)
                                .padding(horizontal = 8.dp)
                                .onFocusChanged { state ->
                                    val focused = state.isFocused
                                    if (focused && !urlFocused) {
                                        urlInput = TextFieldValue(displayUrl(pageUrl))
                                    }
                                    urlFocused = focused
                                },
                            decorationBox = { inner ->
                                Box(contentAlignment = Alignment.CenterStart) {
                                    if (urlInput.text.isEmpty()) {
                                        Text(
                                            stringResource(R.string.enter_url),
                                            color = SledgeTheme.Muted,
                                            fontSize = 15.sp,
                                            maxLines = 1,
                                        )
                                    }
                                    inner()
                                }
                            },
                        )
                        ChromeButton(
                            onClick = {
                                if (asleep) desk.wake(currentIndex) else activeWebView?.reload()
                            },
                            icon = Icons.Default.Refresh,
                            description = stringResource(R.string.reload),
                        )
                        ChromeButton(
                            onClick = {
                                if (!canBookmark) return@ChromeButton
                                val added = store.toggleBookmark(
                                    pageUrl,
                                    currentTab?.title?.ifBlank { pageUrl }.orEmpty(),
                                )
                                scope.launch {
                                    snackbar.showSnackbar(if (added) bookmarkSaved else bookmarkRemoved)
                                }
                            },
                            icon = if (bookmarked) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                            description = stringResource(R.string.bookmark_page),
                            tint = when {
                                !canBookmark -> SledgeTheme.Muted
                                bookmarked -> SledgeTheme.Accent
                                else -> SledgeTheme.Dim
                            },
                        )
                    }
                    Box {
                        ChromeButton(
                            onClick = { showListMenu = true },
                            icon = Icons.Default.Menu,
                            description = stringResource(R.string.menu),
                        )
                        BrowserListMenu(
                            expanded = showListMenu,
                            onDismiss = { showListMenu = false },
                            onNewTab = { desk.open(START_PAGE) },
                            onTabs = { sheet = DeskSheet.Overview },
                            onCloseTab = { desk.close(currentIndex) },
                            onPorts = { sheet = DeskSheet.Ports },
                            onFind = { findOpen = true },
                            onBookmarks = { panel = Panel.Bookmarks },
                            onHistory = { panel = Panel.History },
                            onSettings = { panel = Panel.Settings },
                        )
                    }
                }

                if (findOpen) {
                    FindBar(webView = activeWebView, onClose = { findOpen = false })
                }

                if (!asleep && progress < 100) {
                    LinearProgressIndicator(
                        progress = { progress / 100f },
                        color = SledgeTheme.Strike,
                        trackColor = Color.Transparent,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(2.dp),
                    )
                }

                Box(modifier = Modifier.weight(1f).background(SledgeTheme.Background)) {
                    val tab = currentTab
                    val webView = activeWebView
                    when {
                        tab != null && asleep -> SleepingTab(
                            tab = tab,
                            onWake = { desk.wake(currentIndex) },
                            modifier = Modifier.fillMaxSize(),
                        )
                        tab != null && webView != null -> key(tab.id) {
                            AndroidView(
                                factory = {
                                    (webView.parent as? ViewGroup)?.removeView(webView)
                                    webView
                                },
                                modifier = Modifier.fillMaxSize(),
                            )
                        }
                    }
                }

                TabBar(
                    tabs = tabs,
                    groups = groups,
                    currentIndex = currentIndex,
                    onTabSelect = { desk.select(it) },
                    onTabClose = { desk.close(it) },
                    onTabLongPress = { sheet = DeskSheet.TabActions(it) },
                    onGroupClick = { desk.toggleCollapsed(it) },
                    onGroupLongPress = { sheet = DeskSheet.GroupActions(it) },
                    onNewTab = { desk.open(START_PAGE) },
                    onOverview = { sheet = DeskSheet.Overview },
                    modifier = Modifier.fillMaxWidth(),
                )
            }

            fullscreenView?.let { fsView ->
                AndroidView(
                    factory = {
                        (fsView.parent as? ViewGroup)?.removeView(fsView)
                        fsView.apply {
                            layoutParams = ViewGroup.LayoutParams(
                                ViewGroup.LayoutParams.MATCH_PARENT,
                                ViewGroup.LayoutParams.MATCH_PARENT,
                            )
                        }
                    },
                    modifier = Modifier.fillMaxSize(),
                )
            }

            SnackbarHost(
                hostState = snackbar,
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 72.dp),
            )

            if (showRingMenu) {
                RingMenu(
                    actions = ringMenuActions(
                        onNewTab = { desk.open(START_PAGE) },
                        onTabs = { sheet = DeskSheet.Overview },
                        onCloseTab = { desk.close(currentIndex) },
                        onPorts = { sheet = DeskSheet.Ports },
                        onFind = { findOpen = true },
                        onBookmarks = { panel = Panel.Bookmarks },
                        onHistory = { panel = Panel.History },
                        onSettings = { panel = Panel.Settings },
                    ),
                    onDismiss = { showRingMenu = false },
                    radius = 156.dp,
                    modifier = Modifier
                        .fillMaxSize()
                        .align(Alignment.Center),
                )
            }
        }
    }

    val activeSheet = sheet
    if (activeSheet != null) {
        ModalBottomSheet(
            onDismissRequest = { sheet = null },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            containerColor = SledgeTheme.Surface,
            contentColor = SledgeTheme.Text,
            shape = SledgeTheme.Corner,
            dragHandle = { BottomSheetDefaults.DragHandle(color = SledgeTheme.Strike) },
        ) {
            when (activeSheet) {
                DeskSheet.Overview -> TabOverviewSheet(
                    desk = desk,
                    onSelect = {
                        desk.select(it)
                        sheet = null
                    },
                    onDismiss = { sheet = null },
                )
                DeskSheet.Ports -> DevPortsSheet(
                    currentUrl = pageUrl,
                    onOpen = { url, newTab -> openUrl(url, newTab) },
                )
                is DeskSheet.TabActions -> TabActionsSheet(
                    desk = desk,
                    index = activeSheet.index,
                    onDismiss = { sheet = null },
                )
                is DeskSheet.GroupActions -> GroupActionsSheet(
                    desk = desk,
                    groupId = activeSheet.groupId,
                    onDismiss = { sheet = null },
                )
            }
        }
    }

    if (panel != null) {
        ModalBottomSheet(
            onDismissRequest = { panel = null },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            containerColor = SledgeTheme.Surface,
            contentColor = SledgeTheme.Text,
            shape = SledgeTheme.Corner,
            dragHandle = { BottomSheetDefaults.DragHandle(color = SledgeTheme.Strike) },
        ) {
            when (panel) {
                Panel.History -> HistoryPanel(
                    entries = store.history,
                    onOpen = { openUrl(it) },
                    onDelete = { id -> store.deleteHistory(id) },
                    onClear = { store.clearHistory() },
                )
                Panel.Bookmarks -> BookmarksPanel(
                    bookmarks = store.bookmarks,
                    onOpen = { openUrl(it) },
                    onDelete = { id -> store.deleteBookmark(id) },
                )
                Panel.Settings -> SettingsPanel(
                    settings = store.settings,
                    status = brave.status,
                    locationSites = store.locationChoices.size,
                    onChange = { store.updateSettings(it) },
                    onClearLocations = { store.clearLocationChoices() },
                )
                null -> Unit
            }
        }
    }
}

@Composable
private fun ChromeButton(
    onClick: () -> Unit,
    icon: ImageVector,
    description: String,
    tint: Color = SledgeTheme.Dim,
) {
    IconButton(onClick = onClick, modifier = Modifier.size(36.dp)) {
        Icon(
            imageVector = icon,
            contentDescription = description,
            tint = tint,
            modifier = Modifier.size(20.dp),
        )
    }
}

@Composable
private fun BrowserListMenu(
    expanded: Boolean,
    onDismiss: () -> Unit,
    onNewTab: () -> Unit,
    onTabs: () -> Unit,
    onCloseTab: () -> Unit,
    onPorts: () -> Unit,
    onFind: () -> Unit,
    onBookmarks: () -> Unit,
    onHistory: () -> Unit,
    onSettings: () -> Unit,
) {
    DropdownMenu(
        expanded = expanded,
        onDismissRequest = onDismiss,
        containerColor = SledgeTheme.Surface,
        shape = SledgeTheme.Corner,
    ) {
        listOf(
            R.string.new_tab to onNewTab,
            R.string.tabs to onTabs,
            R.string.close_tab to onCloseTab,
            R.string.dev_ports to onPorts,
            R.string.find_in_page to onFind,
            R.string.bookmarks to onBookmarks,
            R.string.history to onHistory,
            R.string.settings to onSettings,
        ).forEach { (label, action) ->
            DropdownMenuItem(
                text = { Text(stringResource(label), color = SledgeTheme.Text) },
                onClick = {
                    onDismiss()
                    action()
                },
            )
        }
    }
}

@Composable
private fun ringMenuActions(
    onNewTab: () -> Unit,
    onTabs: () -> Unit,
    onCloseTab: () -> Unit,
    onPorts: () -> Unit,
    onFind: () -> Unit,
    onBookmarks: () -> Unit,
    onHistory: () -> Unit,
    onSettings: () -> Unit,
): List<RingMenuAction> = listOf(
    RingMenuAction(stringResource(R.string.ring_new), onNewTab),
    RingMenuAction(stringResource(R.string.ring_tabs), onTabs),
    RingMenuAction(stringResource(R.string.ring_close), onCloseTab),
    RingMenuAction(stringResource(R.string.ring_ports), onPorts),
    RingMenuAction(stringResource(R.string.ring_find), onFind),
    RingMenuAction(stringResource(R.string.ring_bookmarks), onBookmarks),
    RingMenuAction(stringResource(R.string.ring_history), onHistory),
    RingMenuAction(stringResource(R.string.ring_settings), onSettings),
)
