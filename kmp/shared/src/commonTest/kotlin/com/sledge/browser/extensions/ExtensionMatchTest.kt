package com.sledge.browser.extensions

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class ExtensionMatchTest {
    @Test
    fun matchesChromePatterns() {
        assertTrue(extensionMatches("<all_urls>", "https://example.com/a"))
        assertTrue(extensionMatches("*://*/*", "http://example.com/a"))
        assertFalse(extensionMatches("*://*/*", "file:///tmp/a"))
        assertTrue(extensionMatches("*://*.example.com/*", "https://a.example.com/x"))
        assertTrue(extensionMatches("*://*.example.com/*", "https://example.com/x"))
        assertFalse(extensionMatches("*://*.example.com/*", "https://notexample.com/x"))
        assertTrue(extensionMatches("https://example.com/app/*", "https://example.com/app/1"))
        assertFalse(extensionMatches("https://example.com/app/*", "https://example.com/other"))
        assertFalse(extensionMatches("https://example.com/*", "http://example.com/"))
    }
}
