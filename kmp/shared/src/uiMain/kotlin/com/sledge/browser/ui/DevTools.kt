package com.sledge.browser.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sledge.browser.Strings
import kotlinx.coroutines.delay

const val CONSOLE_HOOK = """
(function(){
  if (window.__sledgeLogs) return;
  window.__sledgeLogs = [];
  function textOf(args) {
    return Array.prototype.map.call(args, function(item) {
      if (typeof item === "string") return item;
      try { return JSON.stringify(item); } catch (e) { return String(item); }
    }).join(" ");
  }
  function caller() {
    try {
      var parts = String((new Error()).stack || "").split("\n");
      var line = parts.length > 3 ? parts[3] : "";
      return line.replace(/^\s*at\s+/, "");
    } catch (e) { return ""; }
  }
  function push(level, message, where) {
    window.__sledgeLogs.push(level + "\t" + message + "\t" + (where || ""));
    if (window.__sledgeLogs.length > 400) window.__sledgeLogs.shift();
  }
  ["log", "info", "warn", "error", "debug"].forEach(function(level) {
    var original = console[level] ? console[level].bind(console) : function() {};
    console[level] = function() {
      push(level, textOf(arguments), caller());
      original.apply(console, arguments);
    };
  });
  window.addEventListener("error", function(event) {
    var where = (event.filename || "") + ":" + (event.lineno || 0);
    push("error", event.message || "error", where);
  });
  window.addEventListener("unhandledrejection", function(event) {
    var reason = event.reason;
    var message = reason && reason.message ? reason.message : String(reason);
    push("error", "Unhandled promise: " + message, reason && reason.stack ? String(reason.stack).split("\n")[1] || "" : "");
  });
})()
"""

const val CONSOLE_CLEAR = """
(function(){ if (window.__sledgeLogs) window.__sledgeLogs.length = 0; })()
"""

private const val CONSOLE_READ = """
(function(){ return (window.__sledgeLogs || []).join("\n"); })()
"""

private const val ELEMENT_SCRIPT = """
(function(){
  var lines = [];
  var names = ["href","src","alt","type","name","role","placeholder","value","rel","media","content","title","action","method"];
  function field(value) {
    return String(value || "").replace(/[\n\r\t]/g, " ").replace(/\s+/g, " ").trim();
  }
  function attrs(el) {
    var parts = [];
    for (var i = 0; i < names.length; i++) {
      var v = el.getAttribute(names[i]);
      if (!v) continue;
      parts.push(names[i] + "=" + field(v).slice(0, 160));
    }
    return parts.join(" | ");
  }
  function ownText(el) {
    var out = "";
    var nodes = el.childNodes || [];
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].nodeType === 3) out += nodes[i].textContent || "";
    }
    return field(out).slice(0, 180);
  }
  function walk(el, depth) {
    if (!el || el.nodeType !== 1 || el.id === "__sledge_box" || lines.length >= 800 || depth > 16) return;
    var id = el.id ? field(el.id) : "";
    var cls = "";
    if (typeof el.className === "string" && el.className) {
      cls = field(el.className).split(" ").slice(0, 4).join(" ");
    }
    var children = el.children || [];
    var shown = 0;
    var limit = Math.min(children.length, 80);
    lines.push([depth, (el.tagName || "").toLowerCase(), id, cls, attrs(el), ownText(el), children.length].join("\t"));
    for (var i = 0; i < limit && lines.length < 800; i++) {
      walk(children[i], depth + 1);
      shown++;
    }
  }
  if (document.documentElement) walk(document.documentElement, 0);
  return lines.join("\n");
})()
"""

private const val SOURCE_SCRIPT = """
(function(){
  function pack(value) {
    return String(value || "").replace(/\u000b/g, " ").replace(/\t/g, "  ").replace(/\n/g, "\u000b").slice(0, 12000);
  }
  var lines = [];
  var html = document.documentElement ? document.documentElement.outerHTML : "";
  lines.push(["page", document.title || "(untitled)", location.href || "", (document.readyState || "") + "  " + (document.characterSet || ""), pack(html)].join("\t"));
  var scripts = document.scripts || [];
  for (var i = 0; i < scripts.length && lines.length < 60; i++) {
    var s = scripts[i];
    var flags = [];
    if (s.async) flags.push("async");
    if (s.defer) flags.push("defer");
    if (s.type) flags.push(s.type);
    var len = (s.textContent || "").length;
    if (len) flags.push(len + " chars");
    lines.push(["script", s.src || "(inline script)", flags.join("  "), s.src ? "" : pack(s.textContent)].join("\t"));
  }
  var sheets = document.styleSheets || [];
  for (var j = 0; j < sheets.length && lines.length < 80; j++) {
    var sheet = sheets[j];
    var css = "";
    try {
      var rules = sheet.cssRules || [];
      for (var r = 0; r < rules.length && css.length < 12000; r++) css += rules[r].cssText + "\n";
    } catch (e) {
      css = "(stylesheet is not readable from this page)";
    }
    var media = sheet.media && sheet.media.mediaText ? sheet.media.mediaText : "";
    lines.push(["style", sheet.href || "(inline style)", media, pack(css)].join("\t"));
  }
  return lines.join("\n");
})()
"""

private const val NETWORK_SCRIPT = """
(function(){
  function row(entry) {
    var status = entry.responseStatus || 0;
    var size = entry.transferSize || entry.encodedBodySize || entry.decodedBodySize || 0;
    var dur = Math.round(entry.duration || 0);
    var type = entry.initiatorType || entry.entryType || "other";
    var name = String(entry.name || "").replace(/[\n\r\t]/g, " ");
    return [type, status, dur, size, name].join("\t");
  }
  var nav = performance.getEntriesByType("navigation").map(row);
  var res = performance.getEntriesByType("resource").map(row);
  return nav.concat(res).join("\n");
})()
"""

const val INSPECT_INSTALL = """
(function(){
  if (window.__sledgeInspect) return "ok";
  window.__sledgeInspect = { armed: false, locked: false, path: "" };
  function field(value) {
    return String(value == null ? "" : value).replace(/[\n\r\t]/g, " ").replace(/\s+/g, " ").trim();
  }
  function pathOf(el) {
    var parts = [];
    while (el && el.parentElement && el !== document.documentElement) {
      var index = 0;
      var kids = el.parentElement.children || [];
      for (var i = 0; i < kids.length; i++) {
        if (kids[i].id === "__sledge_box") continue;
        if (kids[i] === el) break;
        index++;
      }
      parts.unshift(index);
      el = el.parentElement;
    }
    return parts.join("/");
  }
  function highlight(el) {
    var box = document.getElementById("__sledge_box");
    if (!box) {
      box = document.createElement("div");
      box.id = "__sledge_box";
      box.style.cssText = "position:fixed;z-index:2147483646;pointer-events:none;border:2px solid #d4652f;background:rgba(212,101,47,0.22);box-sizing:border-box;display:none;";
      (document.documentElement || document.body).appendChild(box);
    }
    if (!el || !el.getBoundingClientRect) { box.style.display = "none"; return; }
    var rect = el.getBoundingClientRect();
    box.style.display = "block";
    box.style.left = rect.left + "px";
    box.style.top = rect.top + "px";
    box.style.width = Math.max(rect.width, 1) + "px";
    box.style.height = Math.max(rect.height, 1) + "px";
  }
  window.__sledgeHighlight = highlight;
  try {
    var original = EventTarget.prototype.addEventListener;
    if (!original.__sledge) {
      function wrapped(type) {
        try {
          if (!this.__sledgeListeners) this.__sledgeListeners = [];
          if (this.__sledgeListeners.indexOf(String(type)) < 0 && this.__sledgeListeners.length < 40) {
            this.__sledgeListeners.push(String(type));
          }
        } catch (err) {}
        return original.apply(this, arguments);
      }
      wrapped.__sledge = true;
      EventTarget.prototype.addEventListener = wrapped;
    }
  } catch (err) {}
  function targetAt(event) {
    var el = document.elementFromPoint(event.clientX, event.clientY);
    if (!el || el.id === "__sledge_box") return null;
    return el;
  }
  document.addEventListener("pointermove", function(event) {
    var state = window.__sledgeInspect;
    if (!state || !state.armed || state.locked) return;
    var el = targetAt(event);
    if (!el) return;
    state.path = pathOf(el);
    highlight(el);
  }, true);
  document.addEventListener("pointerdown", function(event) {
    var state = window.__sledgeInspect;
    if (!state || !state.armed) return;
    var el = targetAt(event);
    if (!el) return;
    event.preventDefault();
    event.stopPropagation();
    state.path = pathOf(el);
    state.locked = true;
    state.armed = false;
    highlight(el);
  }, true);
  return "ok";
})()
"""

private const val PICK_ARM = """
(function(){
  if (!window.__sledgeInspect) return "0\t0\t";
  window.__sledgeInspect.armed = true;
  window.__sledgeInspect.locked = false;
  return "1\t0\t" + (window.__sledgeInspect.path || "");
})()
"""

private const val PICK_OFF = """
(function(){
  if (!window.__sledgeInspect) return "0\t0\t";
  window.__sledgeInspect.armed = false;
  if (window.__sledgeHighlight) window.__sledgeHighlight(null);
  return "0\t" + (window.__sledgeInspect.locked ? "1" : "0") + "\t" + (window.__sledgeInspect.path || "");
})()
"""

private const val PICK_READ = """
(function(){
  var state = window.__sledgeInspect;
  if (!state) return "0\t0\t";
  return (state.armed ? "1" : "0") + "\t" + (state.locked ? "1" : "0") + "\t" + (state.path || "");
})()
"""

private const val DESCRIBE_SCRIPT = """
(function(){
  function field(value) {
    return String(value == null ? "" : value).replace(/[\n\r\t]/g, " ").replace(/\s+/g, " ").trim();
  }
  function nodeAt(path) {
    var el = document.documentElement;
    if (!path) return el;
    var parts = path.split("/");
    for (var i = 0; i < parts.length; i++) {
      if (!el) return null;
      var want = parseInt(parts[i], 10);
      var seen = 0;
      var next = null;
      var kids = el.children || [];
      for (var c = 0; c < kids.length; c++) {
        if (kids[c].id === "__sledge_box") continue;
        if (seen === want) { next = kids[c]; break; }
        seen++;
      }
      el = next;
    }
    return el;
  }
  var el = nodeAt("__PATH__");
  if (!el) return "";
  var lines = [];
  var style = getComputedStyle(el);
  var rect = el.getBoundingClientRect();
  function px(name) { return Math.round(parseFloat(style.getPropertyValue(name)) || 0); }
  lines.push(["BOX", Math.round(rect.x), Math.round(rect.y), Math.round(rect.width), Math.round(rect.height),
    px("margin-top"), px("margin-right"), px("margin-bottom"), px("margin-left"),
    px("border-top-width"), px("border-right-width"), px("border-bottom-width"), px("border-left-width"),
    px("padding-top"), px("padding-right"), px("padding-bottom"), px("padding-left")].join("\t"));
  var listeners = el.__sledgeListeners || [];
  for (var n = 0; n < listeners.length; n++) lines.push("L\t" + field(listeners[n]));
  var sheets = document.styleSheets || [];
  var rulesOut = 0;
  for (var s = 0; s < sheets.length && rulesOut < 40; s++) {
    var rules;
    try { rules = sheets[s].cssRules; } catch (e) { continue; }
    if (!rules) continue;
    for (var k = 0; k < rules.length && rulesOut < 40; k++) {
      var rule = rules[k];
      if (!rule || !rule.selectorText || !rule.style) continue;
      var selectors = rule.selectorText.split(",");
      var hit = false;
      for (var q = 0; q < selectors.length; q++) {
        try { if (el.matches(selectors[q].trim())) hit = true; } catch (err) {}
      }
      if (!hit) continue;
      lines.push("R\t" + field(rule.selectorText).slice(0, 220) + "\t" + field(rule.cssText).slice(0, 600));
      rulesOut++;
    }
  }
  for (var i = 0; i < style.length; i++) {
    var prop = style[i];
    var value = style.getPropertyValue(prop);
    if (!value) continue;
    lines.push("C\t" + prop + "\t" + field(value).slice(0, 300));
  }
  return lines.join("\n");
})()
"""

private const val APPLICATION_SCRIPT = """
(function(){
  function field(value) {
    return String(value == null ? "" : value).replace(/[\n\r\t]/g, " ").slice(0, 500);
  }
  var lines = [];
  try {
    for (var i = 0; i < localStorage.length && lines.length < 200; i++) {
      var key = localStorage.key(i);
      lines.push(["local", field(key), field(localStorage.getItem(key))].join("\t"));
    }
  } catch (e) {}
  try {
    for (var j = 0; j < sessionStorage.length && lines.length < 400; j++) {
      var name = sessionStorage.key(j);
      lines.push(["session", field(name), field(sessionStorage.getItem(name))].join("\t"));
    }
  } catch (e) {}
  var cookie = document.cookie || "";
  if (cookie) {
    cookie.split(";").forEach(function(part) {
      var text = part.trim();
      if (!text) return;
      lines.push(["cookie", field(text.split("=")[0]), field(text.split("=").slice(1).join("="))].join("\t"));
    });
  }
  return lines.join("\n");
})()
"""

private const val PERFORMANCE_SCRIPT = """
(function(){
  var nav = performance.getEntriesByType("navigation")[0];
  var lines = [];
  function mark(name, value) { lines.push(name + "\t" + Math.round(value || 0)); }
  if (nav) {
    mark("DNS", nav.domainLookupEnd - nav.domainLookupStart);
    mark("TCP", nav.connectEnd - nav.connectStart);
    mark("TLS", nav.secureConnectionStart > 0 ? nav.connectEnd - nav.secureConnectionStart : 0);
    mark("Waiting for server", nav.responseStart - nav.requestStart);
    mark("Content download", nav.responseEnd - nav.responseStart);
    mark("DOM interactive", nav.domInteractive);
    mark("DOM content loaded", nav.domContentLoadedEventEnd);
    mark("Load", nav.loadEventEnd);
    mark("Transfer bytes", nav.transferSize || 0);
  }
  var paints = performance.getEntriesByType("paint") || [];
  for (var i = 0; i < paints.length; i++) mark(paints[i].name, paints[i].startTime);
  return lines.join("\n");
})()
"""

private enum class DevToolsTab { Elements, Console, Sources, Network, Application, Performance }

private enum class ElementPane { Styles, Computed, Box }

private data class DomNode(
    val depth: Int,
    val tag: String,
    val id: String,
    val classes: String,
    val attrs: String,
    val text: String,
    val childCount: Int,
)

private data class SourceFile(
    val kind: String,
    val name: String,
    val detail: String,
    val body: String,
)

private data class NetRow(
    val type: String,
    val status: Int,
    val durationMs: Int,
    val bytes: Long,
    val url: String,
    val blocked: Boolean,
)

private data class BoxMetrics(
    val x: Int,
    val y: Int,
    val width: Int,
    val height: Int,
    val margin: List<Int>,
    val border: List<Int>,
    val padding: List<Int>,
)

private data class InspectDetail(
    val box: BoxMetrics?,
    val computed: List<Pair<String, String>>,
    val rules: List<Pair<String, String>>,
    val listeners: List<String>,
)

private data class StorageEntry(val kind: String, val key: String, val value: String)

private data class TimingMark(val name: String, val value: Int)

@Composable
fun DevToolsPanel(
    page: BrowserPage?,
    lines: List<ConsoleLine>,
    network: List<NetworkEntry>,
    endpoint: String,
    onEndpointChange: (String) -> Unit,
    onClearConsole: () -> Unit,
    onClearNetwork: () -> Unit,
    onClose: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var tab by remember { mutableStateOf(DevToolsTab.Elements) }
    var elements by remember { mutableStateOf("") }
    var sources by remember { mutableStateOf("") }
    var timings by remember { mutableStateOf("") }
    var storage by remember { mutableStateOf("") }
    var performance by remember { mutableStateOf("") }
    var scraped by remember { mutableStateOf(emptyList<ConsoleLine>()) }
    var loading by remember { mutableStateOf(false) }
    fun load(which: DevToolsTab) {
        val target = page ?: return
        val script = when (which) {
            DevToolsTab.Elements -> ELEMENT_SCRIPT
            DevToolsTab.Sources -> SOURCE_SCRIPT
            DevToolsTab.Console -> CONSOLE_READ
            DevToolsTab.Network -> NETWORK_SCRIPT
            DevToolsTab.Application -> APPLICATION_SCRIPT
            DevToolsTab.Performance -> PERFORMANCE_SCRIPT
        }
        loading = true
        if (which == DevToolsTab.Elements) target.evaluate(INSPECT_INSTALL)
        target.evaluate(script) { raw ->
            val text = unwrapJsString(raw)
            when (which) {
                DevToolsTab.Elements -> elements = text
                DevToolsTab.Sources -> sources = text
                DevToolsTab.Console -> scraped = parseConsole(text)
                DevToolsTab.Network -> timings = text
                DevToolsTab.Application -> storage = text
                DevToolsTab.Performance -> performance = text
            }
            loading = false
        }
    }
    LaunchedEffect(page, page?.url, tab) {
        load(tab)
    }
    Column(modifier.fillMaxSize().background(SledgeTheme.Chrome)) {
        Row(
            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            listOf(
                DevToolsTab.Elements to Strings.devtools_elements,
                DevToolsTab.Console to Strings.console,
                DevToolsTab.Sources to Strings.devtools_sources,
                DevToolsTab.Network to Strings.devtools_network,
                DevToolsTab.Application to Strings.devtools_application,
                DevToolsTab.Performance to Strings.devtools_performance,
            ).forEach { (item, label) ->
                TextButton(onClick = { tab = item }) {
                    Text(label, color = if (tab == item) SledgeTheme.Strike else SledgeTheme.Dim, fontSize = 13.sp)
                }
            }
            TextButton(onClick = { load(tab) }, enabled = !loading) {
                Text(Strings.devtools_refresh, color = SledgeTheme.Dim, fontSize = 13.sp)
            }
            if (tab == DevToolsTab.Network) {
                TextButton(onClick = onClearNetwork) {
                    Text(Strings.clear_console, color = SledgeTheme.Dim, fontSize = 13.sp)
                }
            }
            IconButton(onClick = onClose, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Default.Close, Strings.close_find, tint = SledgeTheme.Dim)
            }
        }
        when (tab) {
            DevToolsTab.Elements -> ElementTree(page, elements, loading)
            DevToolsTab.Console -> ConsolePanel(
                lines = mergedConsole(lines, scraped),
                endpoint = endpoint,
                onEndpointChange = onEndpointChange,
                onClear = {
                    page?.evaluate(CONSOLE_CLEAR)
                    scraped = emptyList()
                    onClearConsole()
                },
                onClose = onClose,
                embedded = true,
            )
            DevToolsTab.Sources -> SourceList(sources, loading)
            DevToolsTab.Network -> NetworkList(mergeNetwork(network, timings), loading && timings.isBlank() && network.isEmpty())
            DevToolsTab.Application -> StorageList(storage, loading)
            DevToolsTab.Performance -> PerformanceList(performance, loading)
        }
    }
}

@Composable
private fun ElementTree(page: BrowserPage?, raw: String, loading: Boolean) {
    val nodes = remember(raw) { parseElements(raw) }
    var expanded by remember(raw) { mutableStateOf(nodes.indices.filter { nodes[it].depth <= 1 }.toSet()) }
    var selected by remember(raw) { mutableStateOf<Int?>(null) }
    var query by remember(raw) { mutableStateOf("") }
    var picking by remember { mutableStateOf(false) }
    var pane by remember { mutableStateOf(ElementPane.Styles) }
    var detail by remember { mutableStateOf<InspectDetail?>(null) }
    val visible = remember(nodes, expanded, query) { visibleNodes(nodes, expanded, query) }
    val listState = rememberLazyListState()
    fun choose(index: Int) {
        selected = index
        if (query.isBlank()) expanded = expanded + ancestorIndexes(nodes, index)
    }
    LaunchedEffect(picking, page) {
        val target = page ?: return@LaunchedEffect
        if (picking) {
            target.evaluate(INSPECT_INSTALL)
            target.evaluate(PICK_ARM)
        } else {
            target.evaluate(PICK_OFF)
        }
    }
    LaunchedEffect(picking, page, nodes) {
        if (!picking) return@LaunchedEffect
        val target = page ?: return@LaunchedEffect
        while (true) {
            delay(160)
            target.evaluate(PICK_READ) { rawPick ->
                val state = unwrapJsString(rawPick).split('\t')
                val locked = state.getOrNull(1) == "1"
                val path = state.getOrNull(2).orEmpty()
                val index = findByPath(nodes, path)
                if (index != null && index != selected) choose(index)
                if (locked) picking = false
            }
        }
    }
    LaunchedEffect(selected, picking, nodes) {
        if (picking) return@LaunchedEffect
        val index = selected ?: return@LaunchedEffect
        val target = page ?: return@LaunchedEffect
        val path = pathOf(nodes, index)
        target.evaluate(describeScript(path)) { rawDetail ->
            detail = parseInspect(unwrapJsString(rawDetail))
        }
    }
    LaunchedEffect(selected, visible) {
        val index = selected ?: return@LaunchedEffect
        val row = visible.indexOf(index)
        if (row >= 0) listState.animateScrollToItem(row)
    }
    Column(Modifier.fillMaxSize()) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            TextButton(onClick = { picking = !picking }) {
                Text(
                    if (picking) Strings.devtools_picking else Strings.devtools_pick,
                    color = if (picking) SledgeTheme.Strike else SledgeTheme.Dim,
                    fontSize = 13.sp,
                )
            }
        }
        FilterField(query) { query = it }
        if (nodes.isEmpty()) {
            EmptyNote(if (loading) "" else Strings.devtools_empty)
        } else if (visible.isEmpty()) {
            EmptyNote(Strings.devtools_no_match)
        } else {
            LazyColumn(state = listState, modifier = Modifier.fillMaxWidth().weight(1f)) {
                items(visible.size) { row ->
                    val index = visible[row]
                    val node = nodes[index]
                    val hasKids = index + 1 < nodes.size && nodes[index + 1].depth > node.depth
                    val open = index in expanded
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(if (selected == index) SledgeTheme.Elevated else SledgeTheme.Chrome)
                            .clickable { choose(index) }
                            .padding(start = (8 + node.depth * 14).dp, end = 8.dp, top = 3.dp, bottom = 3.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            if (!hasKids) " " else if (open) "▾" else "▸",
                            color = SledgeTheme.Muted,
                            fontSize = 12.sp,
                            modifier = Modifier
                                .clickable {
                                    expanded = if (open) expanded - index else expanded + index
                                }
                                .padding(end = 6.dp),
                        )
                        Text(node.tag, color = SledgeTheme.Strike, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                        if (node.id.isNotEmpty()) {
                            Text("#${node.id}", color = SledgeTheme.Yellow, fontSize = 12.sp, fontFamily = FontFamily.Monospace, maxLines = 1)
                        }
                        if (node.classes.isNotEmpty()) {
                            Text(
                                "." + node.classes.replace(" ", "."),
                                color = SledgeTheme.Green,
                                fontSize = 12.sp,
                                fontFamily = FontFamily.Monospace,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                modifier = Modifier.weight(1f, fill = false),
                            )
                        }
                        if (node.text.isNotEmpty()) {
                            Text(
                                "  ${node.text}",
                                color = SledgeTheme.Muted,
                                fontSize = 12.sp,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                }
            }
            val current = selected?.let { nodes.getOrNull(it) }
            if (current != null) {
                Column(Modifier.fillMaxWidth().weight(0.85f).background(SledgeTheme.Surface)) {
                    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
                        listOf(
                            ElementPane.Styles to Strings.devtools_styles,
                            ElementPane.Computed to Strings.devtools_computed,
                            ElementPane.Box to Strings.devtools_box,
                        ).forEach { (item, label) ->
                            TextButton(onClick = { pane = item }) {
                                Text(label, color = if (pane == item) SledgeTheme.Strike else SledgeTheme.Dim, fontSize = 12.sp)
                            }
                        }
                        Text(
                            current.tag + if (current.id.isNotEmpty()) "#${current.id}" else "",
                            color = SledgeTheme.Muted,
                            fontSize = 12.sp,
                            modifier = Modifier.align(Alignment.CenterVertically),
                        )
                    }
                    when (pane) {
                        ElementPane.Styles -> StylePane(current, detail)
                        ElementPane.Computed -> ComputedPane(detail)
                        ElementPane.Box -> BoxPane(detail?.box)
                    }
                }
            }
        }
    }
}

@Composable
private fun StylePane(node: DomNode, detail: InspectDetail?) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp, vertical = 4.dp)) {
        if (node.classes.isNotEmpty()) DetailLine("class", node.classes)
        node.attrs.split(" | ").filter { it.isNotBlank() }.forEach { pair ->
            DetailLine(pair.substringBefore("="), pair.substringAfter("=", ""))
        }
        val listeners = detail?.listeners.orEmpty()
        if (listeners.isNotEmpty()) {
            Text("listeners", color = SledgeTheme.Dim, fontSize = 12.sp, modifier = Modifier.padding(top = 8.dp))
            Text(listeners.joinToString("  "), color = SledgeTheme.Text, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
        }
        val rules = detail?.rules.orEmpty()
        if (rules.isEmpty()) {
            Text(Strings.devtools_empty, color = SledgeTheme.Muted, fontSize = 12.sp, modifier = Modifier.padding(top = 8.dp))
        } else {
            rules.forEach { (selector, css) ->
                Text(selector, color = SledgeTheme.Strike, fontSize = 12.sp, fontFamily = FontFamily.Monospace, modifier = Modifier.padding(top = 8.dp))
                Text(css, color = SledgeTheme.Text, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
            }
        }
    }
}

@Composable
private fun ComputedPane(detail: InspectDetail?) {
    var query by remember { mutableStateOf("") }
    val rows = detail?.computed.orEmpty().filter { (name, value) ->
        query.isBlank() || name.contains(query, true) || value.contains(query, true)
    }
    Column(Modifier.fillMaxSize()) {
        FilterField(query) { query = it }
        if (rows.isEmpty()) {
            EmptyNote(if (detail == null) "" else Strings.devtools_no_match)
        } else {
            LazyColumn(modifier = Modifier.fillMaxWidth().weight(1f)) {
                items(rows.size) { index ->
                    val (name, value) = rows[index]
                    Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 2.dp)) {
                        Text(name, color = SledgeTheme.Dim, fontSize = 12.sp, fontFamily = FontFamily.Monospace, modifier = Modifier.weight(0.46f))
                        Text(value, color = SledgeTheme.Text, fontSize = 12.sp, fontFamily = FontFamily.Monospace, modifier = Modifier.weight(0.54f))
                    }
                }
            }
        }
    }
}

@Composable
private fun BoxPane(box: BoxMetrics?) {
    if (box == null) {
        EmptyNote(Strings.devtools_empty)
        return
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(12.dp)) {
        Text("${box.width} × ${box.height}   at ${box.x}, ${box.y}", color = SledgeTheme.Text, fontSize = 13.sp, fontFamily = FontFamily.Monospace)
        BoxRing("margin", box.margin, SledgeTheme.Elevated)
        BoxRing("border", box.border, SledgeTheme.Surface)
        BoxRing("padding", box.padding, SledgeTheme.Chrome)
    }
}

@Composable
private fun BoxRing(label: String, sides: List<Int>, color: androidx.compose.ui.graphics.Color) {
    Column(Modifier.fillMaxWidth().padding(top = 8.dp).background(color).padding(8.dp)) {
        Text(label, color = SledgeTheme.Muted, fontSize = 11.sp)
        Text(sides.joinToString("   "), color = SledgeTheme.Text, fontSize = 13.sp, fontFamily = FontFamily.Monospace)
        Text("top   right   bottom   left", color = SledgeTheme.Dim, fontSize = 11.sp)
    }
}

@Composable
private fun StorageList(raw: String, loading: Boolean) {
    val rows = remember(raw) { parseStorage(raw) }
    var kind by remember { mutableStateOf("all") }
    var query by remember { mutableStateOf("") }
    val clipboard = LocalClipboardManager.current
    val shown = rows.filter { row ->
        (kind == "all" || row.kind == kind) &&
            (query.isBlank() || row.key.contains(query, true) || row.value.contains(query, true))
    }
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
            listOf("all", "local", "session", "cookie").forEach { name ->
                TextButton(onClick = { kind = name }) {
                    Text(name.replaceFirstChar { it.uppercase() }, color = if (kind == name) SledgeTheme.Strike else SledgeTheme.Dim, fontSize = 12.sp)
                }
            }
        }
        FilterField(query) { query = it }
        if (rows.isEmpty()) {
            EmptyNote(if (loading) "" else Strings.devtools_empty)
        } else if (shown.isEmpty()) {
            EmptyNote(Strings.devtools_no_match)
        } else {
            LazyColumn(modifier = Modifier.fillMaxWidth().weight(1f)) {
                items(shown.size) { index ->
                    val row = shown[index]
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .clickable { clipboard.setText(AnnotatedString("${row.key}=${row.value}")) }
                            .padding(horizontal = 12.dp, vertical = 5.dp),
                    ) {
                        Text(row.kind, color = SledgeTheme.Strike, fontSize = 11.sp)
                        Text(row.key, color = SledgeTheme.Dim, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                        Text(row.value, color = SledgeTheme.Text, fontSize = 12.sp, fontFamily = FontFamily.Monospace, maxLines = 4, overflow = TextOverflow.Ellipsis)
                    }
                }
            }
        }
    }
}

@Composable
private fun PerformanceList(raw: String, loading: Boolean) {
    val marks = remember(raw) { parseTimings(raw) }
    if (marks.isEmpty()) {
        EmptyNote(if (loading) "" else Strings.devtools_empty)
        return
    }
    LazyColumn(modifier = Modifier.fillMaxSize()) {
        items(marks.size) { index ->
            val mark = marks[index]
            val label = if (mark.name.endsWith("bytes")) formatBytes(mark.value.toLong()) else "${mark.value} ms"
            Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp)) {
                Text(mark.name, color = SledgeTheme.Dim, fontSize = 12.sp, modifier = Modifier.weight(1f))
                Text(label, color = SledgeTheme.Text, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
            }
        }
    }
}

@Composable
private fun SourceList(raw: String, loading: Boolean) {
    val files = remember(raw) { parseSources(raw) }
    var selected by remember(raw) { mutableStateOf(0) }
    var query by remember(raw) { mutableStateOf("") }
    val shown = files.indices.filter { index ->
        val file = files[index]
        query.isBlank() || file.name.contains(query, true) || file.kind.contains(query, true) || file.detail.contains(query, true)
    }
    val clipboard = LocalClipboardManager.current
    Column(Modifier.fillMaxSize()) {
        FilterField(query) { query = it }
        if (files.isEmpty()) {
            EmptyNote(if (loading) "" else Strings.devtools_empty)
        } else if (shown.isEmpty()) {
            EmptyNote(Strings.devtools_no_match)
        } else {
            LazyColumn(modifier = Modifier.fillMaxWidth().weight(0.38f)) {
                items(shown.size) { row ->
                    val index = shown[row]
                    val file = files[index]
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .background(if (selected == index) SledgeTheme.Elevated else SledgeTheme.Chrome)
                            .clickable { selected = index }
                            .padding(horizontal = 12.dp, vertical = 6.dp),
                    ) {
                        Text(file.kind, color = SledgeTheme.Strike, fontSize = 11.sp)
                        Text(file.name, color = SledgeTheme.Text, fontSize = 12.sp, fontFamily = FontFamily.Monospace, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        if (file.detail.isNotBlank()) {
                            Text(file.detail, color = SledgeTheme.Muted, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                    }
                }
            }
            val file = files.getOrNull(selected) ?: files[shown.first()]
            Column(Modifier.fillMaxWidth().weight(0.62f).background(SledgeTheme.Surface)) {
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth().padding(start = 12.dp)) {
                    Text(file.name, color = SledgeTheme.Dim, fontSize = 12.sp, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                    TextButton(onClick = { clipboard.setText(AnnotatedString(if (file.body.isBlank()) file.name else file.body)) }) {
                        Text(Strings.copy_console, color = SledgeTheme.Dim, fontSize = 12.sp)
                    }
                }
                Text(
                    text = file.body.ifBlank { file.detail.ifBlank { Strings.devtools_empty } },
                    color = SledgeTheme.Text,
                    fontSize = 12.sp,
                    fontFamily = FontFamily.Monospace,
                    style = TextStyle(lineHeight = 16.sp),
                    modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp, vertical = 4.dp),
                )
            }
        }
    }
}

@Composable
private fun NetworkList(rows: List<NetRow>, loading: Boolean) {
    var query by remember { mutableStateOf("") }
    var group by remember { mutableStateOf("all") }
    var selected by remember { mutableStateOf<Int?>(null) }
    val clipboard = LocalClipboardManager.current
    val shown = rows.mapIndexed { index, row -> index to row }.filter { (_, row) ->
        val groupOk = group == "all" || (group == "blocked" && row.blocked) || netGroup(row.type) == group
        val queryOk = query.isBlank() || row.url.contains(query, true) || row.type.contains(query, true)
        groupOk && queryOk
    }
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
            listOf("all", "document", "script", "style", "image", "fetch", "media", "font", "blocked").forEach { name ->
                TextButton(onClick = { group = name }) {
                    Text(name.replaceFirstChar { it.uppercase() }, color = if (group == name) SledgeTheme.Strike else SledgeTheme.Dim, fontSize = 12.sp)
                }
            }
        }
        FilterField(query) { query = it }
        if (rows.isEmpty()) {
            EmptyNote(if (loading) "" else Strings.devtools_empty)
        } else if (shown.isEmpty()) {
            EmptyNote(Strings.devtools_no_match)
        } else {
            LazyColumn(modifier = Modifier.fillMaxWidth().weight(1f)) {
                items(shown.size) { rowIndex ->
                    val index = shown[rowIndex].first
                    val row = shown[rowIndex].second
                    Column(
                        Modifier
                            .fillMaxWidth()
                            .background(if (selected == index) SledgeTheme.Elevated else SledgeTheme.Chrome)
                            .clickable { selected = if (selected == index) null else index }
                            .padding(horizontal = 12.dp, vertical = 5.dp),
                    ) {
                        Row {
                            Text(
                                if (row.blocked) Strings.devtools_blocked else if (row.status > 0) row.status.toString() else "—",
                                color = if (row.blocked || row.status >= 400) SledgeTheme.Red else SledgeTheme.Green,
                                fontSize = 12.sp,
                                fontFamily = FontFamily.Monospace,
                                modifier = Modifier.padding(end = 8.dp),
                            )
                            Text(netGroup(row.type), color = SledgeTheme.Dim, fontSize = 12.sp, modifier = Modifier.weight(1f))
                            if (row.durationMs >= 0) {
                                Text("${row.durationMs} ms", color = SledgeTheme.Muted, fontSize = 11.sp, modifier = Modifier.padding(end = 8.dp))
                            }
                            if (row.bytes >= 0) Text(formatBytes(row.bytes), color = SledgeTheme.Muted, fontSize = 11.sp)
                        }
                        Text(shortUrl(row.url), color = SledgeTheme.Text, fontSize = 12.sp, fontFamily = FontFamily.Monospace, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                }
            }
            val open = selected?.let { rows.getOrNull(it) }
            if (open != null) {
                Column(Modifier.fillMaxWidth().background(SledgeTheme.Surface).padding(12.dp)) {
                    Text(open.url, color = SledgeTheme.Text, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                    TextButton(onClick = { clipboard.setText(AnnotatedString(open.url)) }) {
                        Text(Strings.copy_console, color = SledgeTheme.Dim, fontSize = 12.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun FilterField(query: String, onQuery: (String) -> Unit) {
    BasicTextField(
        value = query,
        onValueChange = onQuery,
        singleLine = true,
        textStyle = TextStyle(color = SledgeTheme.Text, fontSize = 12.sp),
        cursorBrush = SolidColor(SledgeTheme.Strike),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 4.dp)
            .background(SledgeTheme.Surface)
            .padding(horizontal = 8.dp, vertical = 6.dp),
        decorationBox = { inner ->
            Box {
                if (query.isEmpty()) Text(Strings.devtools_filter, color = SledgeTheme.Muted, fontSize = 12.sp)
                inner()
            }
        },
    )
}

@Composable
private fun EmptyNote(text: String) {
    if (text.isNotEmpty()) {
        Text(text, color = SledgeTheme.Muted, fontSize = 13.sp, modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp))
    }
}

@Composable
private fun DetailLine(name: String, value: String) {
    Row(Modifier.fillMaxWidth().padding(top = 4.dp)) {
        Text(name, color = SledgeTheme.Dim, fontSize = 12.sp, fontFamily = FontFamily.Monospace, modifier = Modifier.padding(end = 8.dp))
        Text(value, color = SledgeTheme.Text, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
    }
}

private fun visibleNodes(nodes: List<DomNode>, expanded: Set<Int>, query: String): List<Int> {
    if (nodes.isEmpty()) return emptyList()
    if (query.isNotBlank()) {
        val needle = query.lowercase()
        val keep = BooleanArray(nodes.size)
        nodes.forEachIndexed { index, node ->
            val blob = "${node.tag} ${node.id} ${node.classes} ${node.attrs} ${node.text}".lowercase()
            if (!blob.contains(needle)) return@forEachIndexed
            keep[index] = true
            var depth = node.depth
            var cursor = index
            while (cursor > 0 && depth > 0) {
                cursor--
                if (nodes[cursor].depth < depth) {
                    keep[cursor] = true
                    depth = nodes[cursor].depth
                }
            }
        }
        return keep.indices.filter { keep[it] }
    }
    val shown = mutableListOf<Int>()
    var hideBelow = Int.MAX_VALUE
    nodes.forEachIndexed { index, node ->
        if (node.depth > hideBelow) return@forEachIndexed
        hideBelow = Int.MAX_VALUE
        shown += index
        val hasKids = index + 1 < nodes.size && nodes[index + 1].depth > node.depth
        if (hasKids && index !in expanded) hideBelow = node.depth
    }
    return shown
}

private fun describeScript(path: String): String {
    val safe = path.filter { it.isDigit() || it == '/' }
    return DESCRIBE_SCRIPT.replace("__PATH__", safe)
}

private fun pathOf(nodes: List<DomNode>, index: Int): String {
    if (index !in nodes.indices || nodes[index].depth == 0) return ""
    val parts = mutableListOf<Int>()
    var target = index
    while (target > 0 && nodes[target].depth > 0) {
        val parentDepth = nodes[target].depth - 1
        var parent = target - 1
        while (parent >= 0 && nodes[parent].depth != parentDepth) parent--
        if (parent < 0) break
        var ordinal = 0
        var cursor = parent + 1
        while (cursor < target) {
            if (nodes[cursor].depth == parentDepth + 1) ordinal++
            cursor++
        }
        parts.add(0, ordinal)
        target = parent
    }
    return parts.joinToString("/")
}

private fun findByPath(nodes: List<DomNode>, path: String): Int? {
    if (nodes.isEmpty()) return null
    if (path.isBlank()) return 0
    var index = 0
    for (part in path.split('/')) {
        val childIndex = part.toIntOrNull() ?: return index
        val parentDepth = nodes[index].depth
        var seen = 0
        var cursor = index + 1
        var found = -1
        while (cursor < nodes.size && nodes[cursor].depth > parentDepth) {
            if (nodes[cursor].depth == parentDepth + 1) {
                if (seen == childIndex) {
                    found = cursor
                    break
                }
                seen++
            }
            cursor++
        }
        if (found < 0) return index
        index = found
    }
    return index
}

private fun ancestorIndexes(nodes: List<DomNode>, index: Int): Set<Int> {
    if (index !in nodes.indices) return emptySet()
    val found = mutableSetOf<Int>()
    var depth = nodes[index].depth
    var cursor = index
    while (cursor > 0 && depth > 0) {
        cursor--
        if (nodes[cursor].depth < depth) {
            found += cursor
            depth = nodes[cursor].depth
        }
    }
    return found
}

private fun parseInspect(text: String): InspectDetail {
    var box: BoxMetrics? = null
    val computed = mutableListOf<Pair<String, String>>()
    val rules = mutableListOf<Pair<String, String>>()
    val listeners = mutableListOf<String>()
    text.lineSequence().forEach { line ->
        val parts = line.split('\t')
        when (parts.firstOrNull()) {
            "BOX" -> if (parts.size >= 17) {
                box = BoxMetrics(
                    x = parts[1].toIntOrNull() ?: 0,
                    y = parts[2].toIntOrNull() ?: 0,
                    width = parts[3].toIntOrNull() ?: 0,
                    height = parts[4].toIntOrNull() ?: 0,
                    margin = parts.subList(5, 9).map { it.toIntOrNull() ?: 0 },
                    border = parts.subList(9, 13).map { it.toIntOrNull() ?: 0 },
                    padding = parts.subList(13, 17).map { it.toIntOrNull() ?: 0 },
                )
            }
            "C" -> if (parts.size >= 3) computed += parts[1] to parts[2]
            "R" -> if (parts.size >= 3) rules += parts[1] to parts[2]
            "L" -> if (parts.size >= 2 && parts[1].isNotBlank()) listeners += parts[1]
        }
    }
    return InspectDetail(box, computed, rules, listeners)
}

private fun parseStorage(text: String): List<StorageEntry> {
    if (text.isBlank()) return emptyList()
    return text.lineSequence().mapNotNull { line ->
        val parts = line.split('\t', limit = 3)
        if (parts.size < 2) return@mapNotNull null
        StorageEntry(parts[0], parts[1], parts.getOrElse(2) { "" })
    }.toList()
}

private fun parseTimings(text: String): List<TimingMark> {
    if (text.isBlank()) return emptyList()
    return text.lineSequence().mapNotNull { line ->
        val name = line.substringBefore('\t')
        val value = line.substringAfter('\t', "").toIntOrNull() ?: return@mapNotNull null
        TimingMark(name, value)
    }.toList()
}

private fun parseElements(text: String): List<DomNode> {
    if (text.isBlank()) return emptyList()
    return text.lineSequence().mapNotNull { line ->
        val parts = line.split('\t')
        if (parts.size < 7) return@mapNotNull null
        DomNode(
            depth = parts[0].toIntOrNull() ?: return@mapNotNull null,
            tag = parts[1],
            id = parts[2],
            classes = parts[3],
            attrs = parts[4],
            text = parts[5],
            childCount = parts[6].toIntOrNull() ?: 0,
        )
    }.toList()
}

private fun parseSources(text: String): List<SourceFile> {
    if (text.isBlank()) return emptyList()
    return text.lineSequence().mapNotNull { line ->
        val parts = line.split('\t', limit = 5)
        if (parts.size < 4) return@mapNotNull null
        SourceFile(parts[0], parts[1], parts[2], parts.getOrElse(3) { "" }.replace('\u000b', '\n'))
    }.toList()
}

private fun parseConsole(text: String): List<ConsoleLine> {
    if (text.isBlank()) return emptyList()
    return text.lineSequence().map { line ->
        val parts = line.split('\t', limit = 3)
        val level = when (parts[0]) {
            "error" -> ConsoleLevel.Error
            "warn" -> ConsoleLevel.Warn
            "info" -> ConsoleLevel.Info
            else -> ConsoleLevel.Log
        }
        val message = parts.getOrElse(1) { line }
        val where = parts.getOrElse(2) { "" }
        val source = where.substringBeforeLast(':')
        val lineNo = where.substringAfterLast(':', "").toIntOrNull() ?: 0
        val file = if (lineNo > 0) source else where
        ConsoleLine(level, message, file, lineNo)
    }.toList()
}

private fun mergedConsole(native: List<ConsoleLine>, scraped: List<ConsoleLine>): List<ConsoleLine> {
    if (scraped.isEmpty()) return native
    if (native.isEmpty()) return scraped
    val extra = scraped.filter { row -> native.none { it.level == row.level && it.message == row.message } }
    return native + extra
}

private fun mergeNetwork(native: List<NetworkEntry>, timings: String): List<NetRow> {
    val measured = timings.lineSequence().mapNotNull { line ->
        val parts = line.split('\t')
        if (parts.size < 5) return@mapNotNull null
        NetRow(
            type = parts[0],
            status = parts[1].toIntOrNull() ?: 0,
            durationMs = parts[2].toIntOrNull() ?: -1,
            bytes = parts[3].toLongOrNull() ?: -1,
            url = parts[4],
            blocked = false,
        )
    }.toList()
    val seen = measured.map { it.url }.toSet()
    val blocked = native.filter { it.blocked && it.url !in seen }.map {
        NetRow(it.type, 0, -1, -1, it.url, blocked = true)
    }
    val flagged = measured.map { row ->
        if (native.any { it.blocked && it.url == row.url }) row.copy(blocked = true) else row
    }
    return flagged + blocked
}

private fun netGroup(type: String): String = when (type.lowercase()) {
    "navigation", "document", "main_frame", "sub_frame" -> "document"
    "script" -> "script"
    "link", "css", "stylesheet" -> "style"
    "img", "image", "icon" -> "image"
    "fetch", "xmlhttprequest", "xhr", "beacon" -> "fetch"
    "font" -> "font"
    "video", "audio", "media" -> "media"
    else -> "other"
}

private fun shortUrl(url: String): String {
    val cut = url.indexOf("://").let { if (it < 0) 0 else it + 3 }
    return url.substring(cut)
}

private fun formatBytes(bytes: Long): String = when {
    bytes < 1024 -> "$bytes B"
    bytes < 1024 * 1024 -> "${bytes / 1024} KB"
    else -> "${bytes / (1024 * 1024)} MB"
}

private fun unwrapJsString(raw: String?): String {
    if (raw.isNullOrBlank() || raw == "null" || raw == "undefined") return ""
    var trimmed = raw.trim()
    if (trimmed.length >= 2 && trimmed.first() == '"' && trimmed.last() == '"') {
        trimmed = trimmed.substring(1, trimmed.length - 1)
            .replace("\\\\", "\\")
            .replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\\\"", "\"")
            .replace("\\u000b", "\u000b")
    }
    return trimmed
}
