package com.sledge.browser.ui

import com.sledge.browser.Strings

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
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
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.BottomSheetDefaults
import androidx.compose.material3.TextButton
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
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.focusProperties
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sledge.browser.adblock.AdBlocker
import com.sledge.browser.AddressInput
import com.sledge.browser.BrowserStore
import com.sledge.browser.addressBarTarget
import com.sledge.browser.openTabMatches
import com.sledge.browser.webSearchUrl
import com.sledge.browser.START_PAGE
import com.sledge.browser.TabDesk
import com.sledge.browser.displayHost
import com.sledge.browser.displayUrl
import com.sledge.browser.security.HostWeight
import com.sledge.browser.security.LookalikeHit
import com.sledge.browser.security.LookalikeKind
import com.sledge.browser.security.lookalike
import com.sledge.browser.model.Tab
import com.sledge.browser.model.TabLifecycle
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private enum class Panel { History, Bookmarks, Settings, Extensions }

/**
 * Root browser screen: address bar, the active [BrowserPage], grouped tab
 * strip, memory status, and the ring menu plus history / bookmarks / settings.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BrowserScreen(
    desk: TabDesk,
    store: BrowserStore,
    adBlocker: AdBlocker,
    brave: ListBlocker,
    extensions: ExtensionCatalog,
    host: ChromeHost,
) {
    val tabs = desk.tabs
    val currentIndex = desk.currentIndex
    val groups = desk.groups
    val focusManager = LocalFocusManager.current
    val keyboard = LocalSoftwareKeyboardController.current
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    host.wire(snackbar)
    val currentTab = tabs.getOrNull(currentIndex)

    val webViewCache = remember { mutableMapOf<String, BrowserPage>() }
    val progressByTab = remember { mutableStateMapOf<String, Int>() }

    var urlInput by remember { mutableStateOf(TextFieldValue("")) }
    var urlFocused by remember { mutableStateOf(false) }
    var suggestionsOpen by remember { mutableStateOf(false) }
    var suggestionBaseline by remember { mutableStateOf("") }
    var showRingMenu by remember { mutableStateOf(false) }
    host.ringGesture { showRingMenu = true }
    var showListMenu by remember { mutableStateOf(false) }
    var panel by remember { mutableStateOf<Panel?>(null) }
    var sheet by remember { mutableStateOf<DeskSheet?>(null) }
    var findOpen by remember { mutableStateOf(false) }
    var devtoolsOpen by remember { mutableStateOf(false) }
    val consoleByTab = remember { mutableStateMapOf<String, androidx.compose.runtime.snapshots.SnapshotStateList<ConsoleLine>>() }
    val networkByTab = remember { mutableStateMapOf<String, androidx.compose.runtime.snapshots.SnapshotStateList<NetworkEntry>>() }
    var skipSettingsReload by remember { mutableStateOf(true) }
    var appliedSettings by remember { mutableStateOf(store.settings) }
    var canBack by remember { mutableStateOf(false) }
    var canForward by remember { mutableStateOf(false) }
    val allowedLookalikes = remember { mutableSetOf<String>() }
    var advisory by remember { mutableStateOf<Pair<LookalikeHit, () -> Unit>?>(null) }

    fun visitWeights(): List<HostWeight> =
        store.history.map { HostWeight(it.url, it.visitCount) }

    fun consider(url: String, proceed: () -> Unit) {
        val hit = lookalike(url, visitWeights())
        if (hit == null || hit.host in allowedLookalikes) {
            proceed()
        } else {
            advisory = hit to proceed
        }
    }

    fun syncNav(webView: BrowserPage?) {
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

    fun createWebView(tab: Tab): BrowserPage = webViewCache.getOrPut(tab.id) {
        val hooks = PageHooks()
        val page = host.openPage(hooks)
        hooks.onPageStarted = { url ->
            desk.update(tab.id, url, null, true)
            networkByTab[tab.id]?.clear()
            page.evaluate(CONSOLE_HOOK)
            page.evaluate(INSPECT_INSTALL)
        }
        hooks.onPageFinished = { url, title ->
            desk.update(tab.id, url, title, false)
            store.recordVisit(url, title ?: "")
            progressByTab[tab.id] = 100
            page.evaluate(CONSOLE_HOOK)
            page.evaluate(INSPECT_INSTALL)
            if (store.settings.javascriptEnabled) {
                extensions.scriptsFor(url).forEach { page.evaluate(it) }
            }
            if (tab.id == desk.current?.id) syncNav(page)
        }
        hooks.onProgress = { progress -> progressByTab[tab.id] = progress }
        hooks.onTitle = { title ->
            desk.update(tab.id, page.url ?: tab.url, title, null)
        }
        hooks.onLookalike = { url ->
            val hit = lookalike(url, visitWeights())
            if (hit == null || hit.host in allowedLookalikes) {
                false
            } else {
                advisory = hit to {
                    allowedLookalikes += hit.host
                    page.loadUrl(url)
                }
                true
            }
        }
        hooks.onCreateTab = { initialUrl ->
            val created = desk.open(initialUrl ?: START_PAGE)
            createWebView(created)
        }
        hooks.onConsole = { level, message, source, line ->
            val lines = consoleByTab.getOrPut(tab.id) { mutableStateListOf() }
            lines.add(ConsoleLine(level, message, source, line))
            if (lines.size > 300) lines.removeRange(0, lines.size - 300)
        }
        hooks.onNetwork = { url, type, blocked ->
            val rows = networkByTab.getOrPut(tab.id) { mutableStateListOf() }
            rows.add(NetworkEntry(url, type, blocked))
            if (rows.size > 400) rows.removeRange(0, rows.size - 400)
        }
        page
    }

    LaunchedEffect(currentTab?.id, currentTab?.lifecycle) {
        val tab = currentTab ?: return@LaunchedEffect
        if (tab.lifecycle == TabLifecycle.Hibernated || tab.url.isBlank()) return@LaunchedEffect
        val view = webViewCache[tab.id] ?: return@LaunchedEffect
        if (!view.url.isNullOrBlank()) return@LaunchedEffect
        consider(tab.url) { view.loadUrl(tab.url) }
    }

    val asleep = currentTab?.lifecycle == TabLifecycle.Hibernated
    val activeWebView: BrowserPage? = currentTab?.takeUnless { asleep }?.let { createWebView(it) }
    val progress = currentTab?.let { progressByTab[it.id] }
        ?: if (currentTab?.isLoading == true) 0 else 100
    val pageUrl = currentTab?.url.orEmpty()
    val canBookmark = pageUrl.startsWith("http://") || pageUrl.startsWith("https://")
    val bookmarked = canBookmark && store.isBookmarked(pageUrl)

    fun rejectBlockedAddress() {
        scope.launch { snackbar.showSnackbar(Strings.address_blocked) }
    }

    fun runAddressAction(raw: String) {
        focusManager.clearFocus()
        keyboard?.hide()
        if (!host.launchAddress(raw)) {
            scope.launch { snackbar.showSnackbar(Strings.address_no_app) }
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
                consider(target.text) {
                    if (asleep) {
                        val id = currentTab?.id ?: return@consider
                        desk.update(id, target.text, null, true)
                        desk.wake(currentIndex)
                    } else {
                        activeWebView?.loadUrl(target.text)
                    }
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
        consider(target) {
            when {
                newTab -> desk.open(target)
                asleep -> {
                    val id = currentTab?.id ?: return@consider
                    desk.update(id, target, null, true)
                    desk.wake(currentIndex)
                }
                else -> activeWebView?.loadUrl(target)
            }
        }
    }

    advisory?.let { (hit, proceed) ->
        AlertDialog(
            onDismissRequest = { advisory = null },
            title = { Text(Strings.lookalike_title) },
            text = {
                Column {
                    Text(hit.host, fontWeight = FontWeight.Medium)
                    Text(
                        lookalikeMessage(hit),
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = { advisory = null }) {
                    Text(Strings.lookalike_back)
                }
            },
            dismissButton = {
                TextButton(onClick = {
                    allowedLookalikes += hit.host
                    advisory = null
                    proceed()
                }) {
                    Text(Strings.lookalike_continue)
                }
            },
        )
    }

    host.backHandler(
        advisory != null || activeWebView?.fullscreen == true || panel != null || sheet != null ||
            showRingMenu || showListMenu || findOpen || devtoolsOpen || activeWebView?.canGoBack() == true,
    ) {
        when {
            advisory != null -> advisory = null
            activeWebView?.fullscreen == true -> activeWebView?.exitFullscreen()
            findOpen -> findOpen = false
            devtoolsOpen -> devtoolsOpen = false
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
                view.destroy()
            }
            webViewCache.clear()
        }
    }


    val bookmarkSaved = Strings.bookmark_added
    val bookmarkRemoved = Strings.bookmark_removed

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
                        description = Strings.go_back,
                        tint = if (canBack) SledgeTheme.Dim else SledgeTheme.Muted,
                    )
                    ChromeButton(
                        onClick = { activeWebView?.goForward() },
                        icon = Icons.AutoMirrored.Filled.ArrowForward,
                        description = Strings.go_forward,
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
                            onValueChange = { next ->
                                urlInput = next
                                if (next.text != suggestionBaseline) suggestionsOpen = true
                            },
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
                                        val shown = displayUrl(pageUrl)
                                        urlInput = TextFieldValue(shown)
                                        suggestionBaseline = shown
                                        suggestionsOpen = true
                                    }
                                    if (!focused) suggestionsOpen = false
                                    urlFocused = focused
                                },
                            decorationBox = { inner ->
                                Box(contentAlignment = Alignment.CenterStart) {
                                    if (urlInput.text.isEmpty()) {
                                        Text(
                                            Strings.enter_url,
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
                            description = Strings.reload,
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
                            description = Strings.bookmark_page,
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
                            description = Strings.menu,
                        )
                        BrowserListMenu(
                            expanded = showListMenu,
                            onDismiss = { showListMenu = false },
                            onNewTab = { desk.open(START_PAGE) },
                            onTabs = { sheet = DeskSheet.Overview },
                            onCloseTab = { desk.close(currentIndex) },
                            onPorts = { sheet = DeskSheet.Ports },
                            onFind = { findOpen = true },
                            onConsole = { devtoolsOpen = true },
                            onBookmarks = { panel = Panel.Bookmarks },
                            onHistory = { panel = Panel.History },
                            onExtensions = { panel = Panel.Extensions },
                            onSettings = { panel = Panel.Settings },
                        )
                    }
                }

                LaunchedEffect(urlFocused, urlInput.text, suggestionBaseline) {
                    if (!urlFocused || urlInput.text != suggestionBaseline) return@LaunchedEffect
                    delay(800)
                    if (urlInput.text == suggestionBaseline) suggestionsOpen = false
                }
                val tabMatches = if (urlFocused && suggestionsOpen) {
                    openTabMatches(urlInput.text, tabs).take(8)
                } else {
                    emptyList()
                }
                if (tabMatches.isNotEmpty()) {
                    val hosts = tabMatches.map { displayHost(tabs[it].url).lowercase() }.distinct()
                    AddressSuggestions(
                        query = urlInput.text.trim(),
                        matches = tabMatches.map { it to tabs[it] },
                        hosts = hosts,
                        onSwitch = { index ->
                            focusManager.clearFocus()
                            keyboard?.hide()
                            if (index != currentIndex) desk.select(index)
                        },
                        onOpenDomain = { host ->
                            focusManager.clearFocus()
                            keyboard?.hide()
                            desk.open("https://$host")
                        },
                        onSearch = {
                            val query = urlInput.text.trim()
                            focusManager.clearFocus()
                            keyboard?.hide()
                            openUrl(webSearchUrl(query))
                        },
                        onClose = { suggestionsOpen = false },
                    )
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

                BoxWithConstraints(modifier = Modifier.weight(1f).fillMaxWidth()) {
                    val available = maxHeight
                    var split by remember { mutableFloatStateOf(0.5f) }
                    Column(Modifier.fillMaxSize()) {
                        if (devtoolsOpen) {
                            DevToolsPanel(
                                page = activeWebView,
                                lines = currentTab?.id?.let { consoleByTab[it] }.orEmpty(),
                                network = currentTab?.id?.let { networkByTab[it] }.orEmpty(),
                                endpoint = store.settings.shareEndpoint,
                                onEndpointChange = { store.updateSettings(store.settings.copy(shareEndpoint = it)) },
                                onClearConsole = { currentTab?.id?.let { consoleByTab[it]?.clear() } },
                                onClearNetwork = { currentTab?.id?.let { networkByTab[it]?.clear() } },
                                onClose = { devtoolsOpen = false },
                                modifier = Modifier.fillMaxWidth().height(available * split),
                            )
                            Box(
                                Modifier
                                    .fillMaxWidth()
                                    .height(8.dp)
                                    .background(SledgeTheme.Elevated)
                                    .pointerInput(available) {
                                        detectVerticalDragGestures { _, drag ->
                                            split = (split + drag / available.toPx()).coerceIn(0.22f, 0.78f)
                                        }
                                    },
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
                                    host.pageSlot(webView, Modifier.fillMaxSize())
                                }
                            }
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

if (activeWebView?.fullscreen == true && activeWebView != null) {
                host.fullscreen(activeWebView, Modifier.fillMaxSize())
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
                Panel.Extensions -> ExtensionsPanel(
                    extensions = extensions,
                    onInstall = host.chooseZip,
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
private fun lookalikeMessage(hit: LookalikeHit): String {
    val visits = hit.neighborVisits
    return when (hit.kind) {
        LookalikeKind.Homoglyph -> if (visits > 0) {
            Strings.lookalike_homoglyph_visits( hit.neighbor, visits)
        } else {
            Strings.lookalike_homoglyph( hit.neighbor)
        }
        LookalikeKind.MixedScript -> Strings.lookalike_mixed( hit.neighbor)
        LookalikeKind.HiddenCharacters -> if (hit.neighbor == hit.host) {
            Strings.lookalike_hidden
        } else if (visits > 0) {
            Strings.lookalike_homoglyph_visits( hit.neighbor, visits)
        } else {
            Strings.lookalike_homoglyph( hit.neighbor)
        }
        LookalikeKind.EmbeddedName -> Strings.lookalike_embedded( hit.neighbor, hit.host)
        LookalikeKind.Kerning -> Strings.lookalike_kerning( hit.neighbor)
        LookalikeKind.Misspelling -> if (visits > 0) {
            Strings.lookalike_misspelling_visits( hit.neighbor, visits)
        } else {
            Strings.lookalike_misspelling( hit.neighbor)
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
    onConsole: () -> Unit,
    onBookmarks: () -> Unit,
    onHistory: () -> Unit,
    onExtensions: () -> Unit,
    onSettings: () -> Unit,
) {
    DropdownMenu(
        expanded = expanded,
        onDismissRequest = onDismiss,
        containerColor = SledgeTheme.Surface,
        shape = SledgeTheme.Corner,
    ) {
        listOf(
            Strings.new_tab to onNewTab,
            Strings.tabs to onTabs,
            Strings.close_tab to onCloseTab,
            Strings.dev_ports to onPorts,
            Strings.find_in_page to onFind,
            Strings.devtools to onConsole,
            Strings.bookmarks to onBookmarks,
            Strings.history to onHistory,
            Strings.extensions to onExtensions,
            Strings.settings to onSettings,
        ).forEach { (label, action) ->
            DropdownMenuItem(
                text = { Text(label, color = SledgeTheme.Text) },
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
    RingMenuAction(Strings.ring_new, onNewTab),
    RingMenuAction(Strings.ring_tabs, onTabs),
    RingMenuAction(Strings.ring_close, onCloseTab),
    RingMenuAction(Strings.ring_ports, onPorts),
    RingMenuAction(Strings.ring_find, onFind),
    RingMenuAction(Strings.ring_bookmarks, onBookmarks),
    RingMenuAction(Strings.ring_history, onHistory),
    RingMenuAction(Strings.ring_settings, onSettings),
)

@Composable
private fun AddressSuggestions(
    query: String,
    matches: List<Pair<Int, Tab>>,
    hosts: List<String>,
    onSwitch: (Int) -> Unit,
    onOpenDomain: (String) -> Unit,
    onSearch: () -> Unit,
    onClose: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = 8.dp, end = 8.dp, bottom = 8.dp)
            .clip(SledgeTheme.Corner)
            .background(SledgeTheme.Elevated),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.End,
        ) {
            IconButton(
                onClick = onClose,
                modifier = Modifier.size(36.dp).focusProperties { canFocus = false },
            ) {
                Icon(Icons.Default.Close, Strings.close_suggestions, tint = SledgeTheme.Dim)
            }
        }
        matches.forEach { (index, tab) ->
            val host = displayHost(tab.url)
            SuggestionRow(
                title = tab.title.ifBlank { host },
                detail = host,
                onClick = { onSwitch(index) },
            )
        }
        hosts.forEach { host ->
            SuggestionRow(
                title = Strings.open_domain_tab(host),
                detail = "",
                onClick = { onOpenDomain(host) },
            )
        }
        SuggestionRow(
            title = Strings.search_for_query(query),
            detail = "",
            onClick = onSearch,
        )
    }
}

@Composable
private fun SuggestionRow(title: String, detail: String, onClick: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 10.dp),
    ) {
        Text(title, color = SledgeTheme.Text, fontSize = 15.sp, maxLines = 1)
        if (detail.isNotBlank() && !title.equals(detail, ignoreCase = true)) {
            Text(detail, color = SledgeTheme.Muted, fontSize = 12.sp, maxLines = 1)
        }
    }
}
