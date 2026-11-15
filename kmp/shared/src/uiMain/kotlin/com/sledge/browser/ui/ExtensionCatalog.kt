package com.sledge.browser.ui

import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.snapshots.SnapshotStateList
import com.sledge.browser.extensions.extensionMatches
import java.io.File
import java.security.MessageDigest
import java.util.zip.ZipInputStream

data class InstalledExtension(
    val id: String,
    val name: String,
    val version: String,
    val enabled: Boolean,
)

/**
 * Unpacked extensions shared by both engines. A `.zip` or `.crx` is stored on
 * disk, and its content scripts are injected when a page finishes loading.
 * Background pages and the `chrome.*` APIs are not part of this.
 */
class ExtensionCatalog(private val root: File) {
    val items: SnapshotStateList<InstalledExtension> = mutableStateListOf()

    init {
        refresh()
    }

    fun refresh() {
        root.mkdirs()
        val found = root.listFiles().orEmpty()
            .filter { File(it, "manifest.json").isFile }
            .mapNotNull { dir ->
                val manifest = readManifest(dir) ?: return@mapNotNull null
                InstalledExtension(
                    id = dir.name,
                    name = manifest.name,
                    version = manifest.version,
                    enabled = !File(dir, "disabled").exists(),
                )
            }
            .sortedBy { it.name.lowercase() }
        items.clear()
        items.addAll(found)
    }

    /** Returns an error the screen can show, or null when the extension is installed. */
    fun install(bytes: ByteArray): String? {
        val payload = zipBytes(bytes) ?: return "Choose a .zip or .crx extension"
        val extracted = LinkedHashMap<String, ByteArray>()
        var total = 0
        ZipInputStream(payload.inputStream()).use { zip ->
            var entry = zip.nextEntry
            var count = 0
            while (entry != null) {
                if (!entry.isDirectory) {
                    val name = entry.name.replace('\\', '/')
                    if (name.startsWith("/") || name.split('/').any { it == ".." }) {
                        return "The archive contains an unsafe path"
                    }
                    val data = zip.readBytes()
                    total += data.size
                    count += 1
                    if (total > MAX_BYTES || count > MAX_FILES) return "The extension is too large"
                    extracted[name] = data
                }
                entry = zip.nextEntry
            }
        }
        val manifestBytes = extracted["manifest.json"] ?: return "The archive has no manifest.json"
        val manifest = readManifest(manifestBytes) ?: return "The manifest could not be read"
        val id = sha256(manifestBytes).take(32)
        val dir = File(root, id)
        val wasDisabled = File(dir, "disabled").exists()
        dir.deleteRecursively()
        extracted.forEach { (name, data) ->
            val file = File(dir, name)
            file.parentFile?.mkdirs()
            file.writeBytes(data)
        }
        if (wasDisabled) File(dir, "disabled").writeText("1")
        refresh()
        return null
    }

    fun setEnabled(id: String, enabled: Boolean) {
        val mark = File(root, "$id/disabled")
        if (enabled) mark.delete() else mark.writeText("1")
        refresh()
    }

    fun remove(id: String) {
        File(root, id).deleteRecursively()
        refresh()
    }

    /** JavaScript to run in a page that just finished loading, in extension order. */
    fun scriptsFor(url: String): List<String> {
        if (!url.startsWith("http://") && !url.startsWith("https://") && !url.startsWith("file:")) {
            return emptyList()
        }
        val scripts = mutableListOf<String>()
        for (item in items) {
            if (!item.enabled) continue
            val manifest = readManifest(File(root, item.id)) ?: continue
            for (block in manifest.blocks) {
                if (block.matches.none { extensionMatches(it, url) }) continue
                if (block.exclude.any { extensionMatches(it, url) }) continue
                for (css in block.css) {
                    val text = readInside(item.id, css) ?: continue
                    scripts += cssScript(text)
                }
                for (js in block.js) {
                    val text = readInside(item.id, js) ?: continue
                    scripts += "(function(){\n$text\n})();"
                }
            }
        }
        return scripts
    }

    private fun readInside(id: String, relative: String): String? {
        val name = relative.replace('\\', '/')
        if (name.startsWith("/") || name.split('/').any { it == ".." }) return null
        val file = File(root, "$id/$name")
        return if (file.isFile) file.readText() else null
    }

    private data class Block(val matches: List<String>, val exclude: List<String>, val css: List<String>, val js: List<String>)
    private data class Manifest(val name: String, val version: String, val blocks: List<Block>)

    private fun readManifest(dir: File): Manifest? = readManifest(File(dir, "manifest.json").readBytes())

    private fun readManifest(bytes: ByteArray): Manifest? {
        val root = parseJson(bytes.toString(Charsets.UTF_8).removePrefix("\uFEFF")) as? Json.Obj ?: return null
        val blocks = (root.map["content_scripts"] as? Json.Arr)?.items.orEmpty().mapNotNull { item ->
            val obj = item as? Json.Obj ?: return@mapNotNull null
            Block(
                matches = strings(obj, "matches"),
                exclude = strings(obj, "exclude_matches"),
                css = strings(obj, "css"),
                js = strings(obj, "js"),
            )
        }
        return Manifest(
            name = (root.map["name"] as? Json.Str)?.text?.ifBlank { null } ?: "Extension",
            version = (root.map["version"] as? Json.Str)?.text.orEmpty(),
            blocks = blocks,
        )
    }

    private fun strings(obj: Json.Obj, key: String): List<String> =
        (obj.map[key] as? Json.Arr)?.items?.mapNotNull { (it as? Json.Str)?.text }.orEmpty()

    private companion object {
        const val MAX_BYTES = 32 * 1024 * 1024
        const val MAX_FILES = 400
    }
}

private fun cssScript(css: String): String =
    "(function(){var s=document.createElement('style');s.textContent=${jsString(css)};" +
        "(document.head||document.documentElement).appendChild(s);})();"

private fun jsString(value: String): String = buildString {
    append('"')
    value.forEach { char ->
        when (char) {
            '\\', '"', '\'' -> append('\\').append(char)
            '\n' -> append("\\n")
            '\r' -> append("\\r")
            '\u2028' -> append("\\u2028")
            '\u2029' -> append("\\u2029")
            else -> append(char)
        }
    }
    append('"')
}

private fun zipBytes(bytes: ByteArray): ByteArray? {
    if (bytes.size >= 2 && bytes[0] == 0x50.toByte() && bytes[1] == 0x4B.toByte()) return bytes
    if (bytes.size < 16 || bytes.copyOfRange(0, 4).toString(Charsets.ISO_8859_1) != "Cr24") return null
    val version = le32(bytes, 4)
    val start = when (version) {
        2 -> 16 + le32(bytes, 8) + le32(bytes, 12)
        3 -> 12 + le32(bytes, 8)
        else -> return null
    }
    if (start < 0 || start >= bytes.size) return null
    return bytes.copyOfRange(start, bytes.size)
}

private fun le32(bytes: ByteArray, at: Int): Int {
    if (at + 4 > bytes.size) return -1
    return (bytes[at].toInt() and 0xFF) or
        ((bytes[at + 1].toInt() and 0xFF) shl 8) or
        ((bytes[at + 2].toInt() and 0xFF) shl 16) or
        ((bytes[at + 3].toInt() and 0xFF) shl 24)
}

private fun sha256(bytes: ByteArray): String =
    MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }

private sealed interface Json {
    data class Obj(val map: Map<String, Json>) : Json
    data class Arr(val items: List<Json>) : Json
    data class Str(val text: String) : Json
    data object Other : Json
}

private fun parseJson(text: String): Json? = try {
    Parser(text).parse()
} catch (_: Exception) {
    null
}

private class Parser(private val text: String) {
    private var index = 0

    fun parse(): Json {
        val value = read()
        skip()
        if (index != text.length) error("trailing")
        return value
    }

    private fun read(): Json {
        skip()
        return when (val char = peek()) {
            '{' -> readObject()
            '[' -> readArray()
            '"' -> Json.Str(readString())
            else -> {
                if (char == null) error("end")
                while (index < text.length && text[index] !in ",}]") index += 1
                Json.Other
            }
        }
    }

    private fun readObject(): Json.Obj {
        index += 1
        val map = linkedMapOf<String, Json>()
        skip()
        if (peek() == '}') {
            index += 1
            return Json.Obj(map)
        }
        while (true) {
            skip()
            if (peek() != '"') error("key")
            val key = readString()
            skip()
            if (peek() != ':') error("colon")
            index += 1
            map[key] = read()
            skip()
            when (peek()) {
                ',' -> index += 1
                '}' -> {
                    index += 1
                    return Json.Obj(map)
                }
                else -> error("object")
            }
        }
    }

    private fun readArray(): Json.Arr {
        index += 1
        val items = mutableListOf<Json>()
        skip()
        if (peek() == ']') {
            index += 1
            return Json.Arr(items)
        }
        while (true) {
            items += read()
            skip()
            when (peek()) {
                ',' -> index += 1
                ']' -> {
                    index += 1
                    return Json.Arr(items)
                }
                else -> error("array")
            }
        }
    }

    private fun readString(): String {
        index += 1
        val out = StringBuilder()
        while (index < text.length) {
            when (val char = text[index++]) {
                '"' -> return out.toString()
                '\\' -> {
                    if (index >= text.length) error("escape")
                    out.append(
                        when (val escaped = text[index++]) {
                            '"', '\\', '/' -> escaped
                            'b' -> '\b'
                            'f' -> '\u000C'
                            'n' -> '\n'
                            'r' -> '\r'
                            't' -> '\t'
                            'u' -> {
                                val hex = text.substring(index, index + 4)
                                index += 4
                                hex.toInt(16).toChar()
                            }
                            else -> escaped
                        },
                    )
                }
                else -> out.append(char)
            }
        }
        error("string")
    }

    private fun skip() {
        while (index < text.length && text[index].isWhitespace()) index += 1
    }

    private fun peek(): Char? = text.getOrNull(index)
}
