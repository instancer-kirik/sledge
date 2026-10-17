package com.sledge.browser.adblock

/**
 * Lightweight ad/tracker blocker that parses a subset of EasyList-style filter syntax.
 *
 * Supported rule format:
 *   - `||domain.example^`  → block all requests whose host matches `domain.example`
 *   - Lines starting with `!` are treated as comments and ignored.
 *   - Lines starting with `##` are cosmetic/CSS rules and are ignored.
 *   - Any other line formats are silently skipped.
 */
class AdBlocker {

    /** Whether ad-blocking is active. When `false`, [shouldBlock] always returns `false`. */
    var enabled: Boolean = true

    private val blockedDomains: MutableSet<String> = mutableSetOf()

    /**
     * Returns `true` if [url] should be blocked.
     *
     * Extracts the host from [url] and checks whether it, or any of its parent domains,
     * appears in the loaded rule set.
     *
     * @param url       The URL of the resource being requested.
     * @param sourceUrl The URL of the page initiating the request (used for future
     *                  first-party/third-party distinction; currently unused).
     */
    fun shouldBlock(url: String, sourceUrl: String): Boolean {
        if (!enabled || blockedDomains.isEmpty()) return false
        val host = extractHost(url) ?: return false
        return isDomainBlocked(host)
    }

    /**
     * Parses [lines] from an EasyList-compatible filter file and populates the internal
     * domain set. Calling this method replaces any previously loaded rules.
     *
     * Only `||domain^` style network rules are extracted; cosmetic rules (`##`) and
     * comment lines (`!`) are ignored.
     */
    fun loadRules(lines: List<String>) {
        blockedDomains.clear()
        for (line in lines) {
            val trimmed = line.trim()
            when {
                trimmed.isEmpty()           -> continue
                trimmed.startsWith('!')     -> continue  // comment
                trimmed.startsWith("##")    -> continue  // cosmetic/CSS rule
                trimmed.startsWith("#@#")   -> continue  // cosmetic exception
                trimmed.startsWith("@@")    -> continue  // exception rules (not yet supported)
                trimmed.startsWith("||")    -> parseNetworkRule(trimmed)
                else                        -> continue  // unsupported syntax
            }
        }
    }

    /** Returns the number of currently loaded blocked domains. */
    val ruleCount: Int get() = blockedDomains.size

    // -----------------------------------------------------------------------------------------
    // Private helpers
    // -----------------------------------------------------------------------------------------

    /**
     * Parses a `||domain^` rule and adds the domain to [blockedDomains].
     *
     * Examples of accepted formats:
     *   `||ads.example.com^`
     *   `||tracker.net^$third-party`   (options after `$` are stripped)
     */
    private fun parseNetworkRule(rule: String) {
        // Strip leading `||`
        var domain = rule.removePrefix("||")

        // Strip trailing anchor `^` and any filter options after `$`
        val dollarIndex = domain.indexOf('$')
        if (dollarIndex != -1) domain = domain.substring(0, dollarIndex)
        domain = domain.trimEnd('^', '/', '*')

        // Skip rules that look like full URL patterns or contain wildcards in the middle
        if (domain.isBlank() || domain.contains('/') || domain.contains('*')) return

        blockedDomains.add(domain.lowercase())
    }

    /**
     * Walks up the host hierarchy and returns `true` if any level matches a blocked domain.
     *
     * e.g. for `sub.ads.example.com` it checks:
     *   `sub.ads.example.com`, `ads.example.com`, `example.com`
     */
    private fun isDomainBlocked(host: String): Boolean {
        var current = host.lowercase()
        while (current.isNotEmpty()) {
            if (current in blockedDomains) return true
            val dotIndex = current.indexOf('.')
            if (dotIndex == -1) break
            current = current.substring(dotIndex + 1)
        }
        return false
    }

    /**
     * Extracts the host portion from a URL string without relying on platform APIs.
     *
     * Handles `scheme://host/path` and bare `host/path` forms.
     * Returns `null` for malformed inputs.
     */
    private fun extractHost(url: String): String? {
        val withoutScheme = if ("://" in url) url.substringAfter("://") else url
        val hostAndRest = withoutScheme.substringBefore('/')
        val host = hostAndRest.substringBefore(':') // strip port if present
        return host.takeIf { it.isNotBlank() }
    }
}
