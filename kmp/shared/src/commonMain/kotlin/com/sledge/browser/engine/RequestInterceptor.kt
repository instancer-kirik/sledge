package com.sledge.browser.engine

import com.sledge.browser.adblock.AdBlocker
import com.sledge.browser.model.BrowserSettings

/**
 * Evaluates every intercepted network request and returns an [InterceptResult] that
 * instructs the browser engine whether to allow, block, or modify the request.
 *
 * Checks are performed in the following priority order:
 *  1. Ad-block domain list
 *  2. Dangerous port filter
 *  3. Mixed-content filter
 *  4. Video-domain header spoofing
 *
 * @param adBlocker Current [AdBlocker] instance (may be shared and mutated externally).
 * @param settings  Immutable [BrowserSettings] snapshot; replace the instance to pick up
 *                  settings changes.
 */
class RequestInterceptor(
    private val adBlocker: AdBlocker,
    private var settings: BrowserSettings,
) {

    /** Update the active settings snapshot (e.g. after the user changes preferences). */
    fun updateSettings(newSettings: BrowserSettings) {
        settings = newSettings
    }

    /**
     * Evaluates [request] against all active filters and returns the appropriate action.
     */
    fun intercept(request: RequestInfo): InterceptResult {
        // 1. Ad blocking
        if (settings.blockAds && adBlocker.shouldBlock(request.url, request.sourceUrl)) {
            return InterceptResult.Block
        }

        // 2. Dangerous port
        if (settings.blockDangerousPorts && hasDangerousPort(request.url)) {
            return InterceptResult.Block
        }

        // 3. Mixed content: block HTTP sub-resources on HTTPS pages
        if (settings.blockMixedContent &&
            request.resourceType != ResourceType.MAIN_FRAME &&
            request.sourceUrl.startsWith("https://", ignoreCase = true) &&
            request.url.startsWith("http://", ignoreCase = true)
        ) {
            return InterceptResult.Block
        }

        // 4. Video-domain header spoofing
        val spoofedHeaders = buildSpoofHeaders(request.url, request.sourceUrl)
        if (spoofedHeaders != null) {
            return InterceptResult.ModifyHeaders(spoofedHeaders)
        }

        return InterceptResult.Allow
    }

    // -----------------------------------------------------------------------------------------
    // Result type
    // -----------------------------------------------------------------------------------------

    /** Describes what the engine should do with an intercepted request. */
    sealed class InterceptResult {
        /** Let the request proceed unchanged. */
        object Allow : InterceptResult()

        /** Cancel the request; the engine should return an error or empty response. */
        object Block : InterceptResult()

        /**
         * Let the request proceed but replace (or add) the specified HTTP [headers].
         * Headers not listed in this map are forwarded as-is.
         */
        data class ModifyHeaders(val headers: Map<String, String>) : InterceptResult()
    }

    // -----------------------------------------------------------------------------------------
    // Private helpers
    // -----------------------------------------------------------------------------------------

    /**
     * Returns spoofed `Referer` and `Origin` headers if [url]'s host appears in
     * [BrowserSettings.videoDomainsConfig], otherwise returns `null`.
     */
    private fun buildSpoofHeaders(url: String, sourceUrl: String): Map<String, String>? {
        val host = extractHost(url) ?: return null

        // Walk up the host hierarchy looking for a matching config entry.
        var candidate: String? = host
        while (candidate != null) {
            val origin = settings.videoDomainsConfig[candidate]
            if (origin != null) {
                return mapOf(
                    "Origin"  to origin,
                    "Referer" to "$origin/",
                )
            }
            val dot = candidate.indexOf('.')
            candidate = if (dot == -1) null else candidate.substring(dot + 1)
        }
        return null
    }

    /**
     * Returns `true` if [url] specifies a port that is on the [DANGEROUS_PORTS] list.
     * URLs without an explicit port (or with port 80/443) are considered safe.
     */
    private fun hasDangerousPort(url: String): Boolean {
        val withoutScheme = if ("://" in url) url.substringAfter("://") else url
        val hostPart = withoutScheme.substringBefore('/')
        val colonIdx = hostPart.lastIndexOf(':')
        if (colonIdx == -1) return false
        val portStr = hostPart.substring(colonIdx + 1)
        val port = portStr.toIntOrNull() ?: return false
        return port in DANGEROUS_PORTS
    }

    /**
     * Minimal host extractor that avoids platform URL-parsing APIs.
     */
    private fun extractHost(url: String): String? {
        val withoutScheme = if ("://" in url) url.substringAfter("://") else url
        val hostAndRest = withoutScheme.substringBefore('/')
        val host = hostAndRest.substringBefore(':')
        return host.takeIf { it.isNotBlank() }
    }

    // -----------------------------------------------------------------------------------------
    // Constants
    // -----------------------------------------------------------------------------------------

    companion object {
        /**
         * Ports that are dangerous to allow browser requests to reach because they host
         * non-HTTP services. Mirrors the `DANGEROUS_PORTS` set from the Python back-end.
         *
         * Reference: https://fetch.spec.whatwg.org/#bad-port
         */
        val DANGEROUS_PORTS: Set<Int> = setOf(
            1,      // tcpmux
            7,      // echo
            9,      // discard
            11,     // systat
            13,     // daytime
            15,     // netstat
            17,     // qotd
            19,     // chargen
            20,     // ftp-data
            21,     // ftp
            22,     // ssh
            23,     // telnet
            25,     // smtp
            37,     // time
            42,     // name
            43,     // whois
            53,     // dns
            69,     // tftp
            77,     // rje
            79,     // finger
            87,     // ttylink
            95,     // supdup
            101,    // hostname
            102,    // iso-tsap
            103,    // gppitnp
            104,    // acr-nema
            109,    // pop2
            110,    // pop3
            111,    // sunrpc
            113,    // auth
            115,    // sftp
            117,    // uucp-path
            119,    // nntp
            123,    // ntp
            135,    // loc-srv / epmap
            137,    // netbios-ns
            139,    // netbios-ssn
            143,    // imap2
            161,    // snmp
            179,    // bgp
            389,    // ldap
            427,    // afp / SLP
            465,    // smtp+ssl
            512,    // rexec
            513,    // rlogin
            514,    // rsh / syslog
            515,    // printer
            526,    // tempo
            530,    // courier
            531,    // chat
            532,    // netnews
            540,    // uucp
            548,    // afp
            554,    // rtsp
            556,    // remotefs
            563,    // nntp+ssl
            587,    // smtp (submission)
            601,    // syslog
            636,    // ldap+ssl
            989,    // ftps-data
            990,    // ftps
            993,    // imap+ssl
            995,    // pop3+ssl
            1719,   // h323gatestat
            1720,   // h323hostcall
            1723,   // pptp
            2049,   // nfs
            3659,   // apple-sasl
            4045,   // lockd
            4190,   // sieve
            5060,   // sip
            5061,   // sips
            6000,   // x11
            6566,   // sane-port
            6665,   // irc (alternate)
            6666,   // irc (alternate)
            6667,   // irc
            6668,   // irc (alternate)
            6669,   // irc (alternate)
            6679,   // osaut
            6697,   // irc+ssl
            10080,  // amanda
        )
    }
}
