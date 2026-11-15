package com.sledge.browser.extensions

/**
 * Chrome match pattern, the subset content scripts use.
 * `*` as a scheme means http or https. A host of `*` matches any host, and
 * `*.example.com` also matches the bare domain.
 */
fun extensionMatches(pattern: String, url: String): Boolean {
    val parsed = splitUrl(url) ?: return false
    if (pattern == "<all_urls>") {
        return parsed.scheme == "http" || parsed.scheme == "https" || parsed.scheme == "file"
    }
    val schemeEnd = pattern.indexOf("://")
    if (schemeEnd <= 0) return false
    val scheme = pattern.substring(0, schemeEnd)
    val rest = pattern.substring(schemeEnd + 3)
    val slash = rest.indexOf('/')
    if (slash < 0) return false
    val host = rest.substring(0, slash)
    val path = rest.substring(slash)
    val schemeOk = when (scheme) {
        "*" -> parsed.scheme == "http" || parsed.scheme == "https"
        else -> scheme == parsed.scheme
    }
    if (!schemeOk || !hostMatches(host, parsed.host)) return false
    return glob(path, parsed.path.ifEmpty { "/" })
}

private data class Parts(val scheme: String, val host: String, val path: String)

private fun splitUrl(url: String): Parts? {
    val schemeEnd = url.indexOf("://")
    if (schemeEnd <= 0) return null
    val scheme = url.substring(0, schemeEnd).lowercase()
    val rest = url.substring(schemeEnd + 3)
    val slash = rest.indexOf('/')
    val authority = if (slash < 0) rest else rest.substring(0, slash)
    val path = if (slash < 0) "/" else rest.substring(slash).substringBefore('?').substringBefore('#')
    return Parts(scheme, authority.substringBefore(':').lowercase(), path)
}

private fun hostMatches(pattern: String, host: String): Boolean = when {
    pattern == "*" -> true
    pattern.startsWith("*.") -> {
        val domain = pattern.substring(2).lowercase()
        host == domain || host.endsWith(".$domain")
    }
    else -> pattern.lowercase() == host
}

private fun glob(pattern: String, value: String): Boolean {
    val parts = pattern.split('*')
    if (parts.size == 1) return pattern == value
    var from = 0
    parts.forEachIndexed { index, part ->
        if (part.isEmpty()) return@forEachIndexed
        val at = value.indexOf(part, from)
        if (at < 0 || (index == 0 && at != 0)) return false
        from = at + part.length
    }
    val tail = parts.last()
    return tail.isEmpty() || value.endsWith(tail)
}
