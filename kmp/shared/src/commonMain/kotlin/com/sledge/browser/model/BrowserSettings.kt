package com.sledge.browser.model

/**
 * Immutable snapshot of user-configurable browser settings.
 *
 * Mirrors the Python `VIDEO_DOMAINS` map for Referer/Origin spoofing so the same
 * logic can run on both platforms.
 */
data class BrowserSettings(
    /** Block network requests matched by [com.sledge.browser.adblock.AdBlocker]. */
    val blockAds: Boolean = true,

    /**
     * Block HTTP sub-resources loaded on an HTTPS page (mixed content).
     * Mirrors the browser's built-in mixed-content policy at the intercept layer.
     */
    val blockMixedContent: Boolean = true,

    /**
     * Refuse connections to ports commonly associated with non-HTTP services
     * (e.g. SMTP, FTP, SSH) to prevent cross-protocol attacks.
     */
    val blockDangerousPorts: Boolean = true,

    /**
     * When `false`, links that would open a popup window instead open a new tab.
     * When `true`, the popup is allowed to open as a separate window.
     */
    val popupsOpenNewTab: Boolean = false,

    /** Master switch for JavaScript execution across all tabs. */
    val javascriptEnabled: Boolean = true,

    /** Request dark mode via the `prefers-color-scheme: dark` media feature. */
    val darkMode: Boolean = true,

    /**
     * Override the browser's default `User-Agent` header.
     * `null` means the engine's default UA is used.
     */
    val customUserAgent: String? = null,

    /**
     * Per-domain Referer/Origin spoofing rules used for video embeds.
     *
     * Key   → request host (e.g. `"player.vimeo.com"`)
     * Value → value to set as the `Origin` (and `Referer`) header
     *         (e.g. `"https://vimeo.com"`)
     *
     * Matches the `VIDEO_DOMAINS` dict from the Python back-end so both sides
     * share the same configuration source.
     */
    val videoDomainsConfig: Map<String, String> = DEFAULT_VIDEO_DOMAINS,
) {
    companion object {
        /**
         * Default video-domain spoofing map equivalent to the Python `VIDEO_DOMAINS` dict.
         *
         * Each entry allows the named player/CDN host to receive requests that appear to
         * originate from the expected embedding origin, preventing 403 Forbidden responses
         * that some providers return when the Referer is missing or wrong.
         */
        val DEFAULT_VIDEO_DOMAINS: Map<String, String> = mapOf(
            // YouTube
            "www.youtube.com"           to "https://www.youtube.com",
            "youtu.be"                  to "https://www.youtube.com",
            "youtube.com"               to "https://www.youtube.com",
            "googlevideo.com"           to "https://www.youtube.com",
            "ytimg.com"                 to "https://www.youtube.com",

            // Vimeo
            "player.vimeo.com"          to "https://vimeo.com",
            "vimeo.com"                 to "https://vimeo.com",
            "vimeocdn.com"              to "https://vimeo.com",

            // Twitch
            "player.twitch.tv"          to "https://www.twitch.tv",
            "twitch.tv"                 to "https://www.twitch.tv",
            "twitchsvc.net"             to "https://www.twitch.tv",
            "jtvnw.net"                 to "https://www.twitch.tv",

            // Dailymotion
            "www.dailymotion.com"       to "https://www.dailymotion.com",
            "dailymotion.com"           to "https://www.dailymotion.com",
            "dmcdn.net"                 to "https://www.dailymotion.com",

            // Wistia
            "fast.wistia.com"           to "https://wistia.com",
            "wistia.com"                to "https://wistia.com",
            "wistia.net"                to "https://wistia.com",

            // Brightcove
            "players.brightcove.net"    to "https://www.brightcove.com",
            "brightcove.com"            to "https://www.brightcove.com",

            // JW Player CDN
            "cdn.jwplayer.com"          to "https://www.jwplayer.com",
            "jwplayer.com"              to "https://www.jwplayer.com",

            // Facebook / Instagram video
            "www.facebook.com"          to "https://www.facebook.com",
            "video.xx.fbcdn.net"        to "https://www.facebook.com",
            "instagram.com"             to "https://www.instagram.com",

            // Twitter / X
            "video.twimg.com"           to "https://twitter.com",

            // Streamable
            "streamable.com"            to "https://streamable.com",

            // Rumble
            "rumble.com"                to "https://rumble.com",
        )
    }
}
