package com.sledge.browser.engine

/**
 * Snapshot of a network request intercepted by the browser engine before it is dispatched.
 *
 * @property url          The fully-qualified URL being requested.
 * @property sourceUrl    The URL of the page (top-level frame) that initiated the request.
 * @property method       HTTP method (uppercase). Defaults to `"GET"`.
 * @property resourceType Semantic category of the resource being fetched.
 */
data class RequestInfo(
    val url: String,
    val sourceUrl: String,
    val method: String = "GET",
    val resourceType: ResourceType = ResourceType.OTHER,
)

/**
 * Mirrors the resource-type categories exposed by WebKit/Chromium WebView intercept APIs,
 * allowing platform bridges to map native constants to this shared enum.
 */
enum class ResourceType {
    /** Top-level navigation (address-bar load, `window.location`, `<a>` click). */
    MAIN_FRAME,

    /** `<iframe>` or `<frame>` sub-document load. */
    SUB_FRAME,

    /** CSS stylesheet (`<link rel="stylesheet">` or `@import`). */
    STYLESHEET,

    /** JavaScript file (`<script src="…">`). */
    SCRIPT,

    /** Raster or vector image (`<img>`, CSS `background-image`, etc.). */
    IMAGE,

    /** Web font (`@font-face`). */
    FONT,

    /** `XMLHttpRequest` or `fetch()` API call. */
    XHR,

    /** Audio or video resource (`<audio>`, `<video>`, Media Source Extensions). */
    MEDIA,

    /** Any resource type not covered by the categories above. */
    OTHER,
}
