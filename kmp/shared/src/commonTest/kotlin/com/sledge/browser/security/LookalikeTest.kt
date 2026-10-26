package com.sledge.browser.security

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class LookalikeTest {
    @Test
    fun cyrillicLookalikeOfAKnownSite() {
        val hit = lookalike("https://p\u0430ypal.com/login", emptyList())
        assertEquals(LookalikeKind.Homoglyph, hit?.kind)
        assertEquals("paypal.com", hit?.neighbor)
    }

    @Test
    fun misspellingOfAFrequentSite() {
        val visits = List(4) { HostWeight("google.com", 1) }
        val hit = lookalike("https://gooogle.com", visits)
        assertEquals(LookalikeKind.Misspelling, hit?.kind)
        assertEquals("google.com", hit?.neighbor)
        assertEquals(4, hit?.neighborVisits)
    }

    @Test
    fun brandBuriedUnderAnotherDomain() {
        val hit = lookalike("https://paypal.com.security.example", emptyList())
        assertEquals(LookalikeKind.EmbeddedName, hit?.kind)
        assertEquals("paypal.com", hit?.neighbor)
    }

    @Test
    fun realSubdomainIsNotAnImposter() {
        assertNull(lookalike("https://accounts.google.com/signin", emptyList()))
    }

    @Test
    fun ordinaryCyrillicNameIsLeftAlone() {
        assertNull(lookalike("https://\u044F\u043D\u0434\u0435\u043A\u0441.\u0440\u0444", emptyList()))
    }

    @Test
    fun kerningCollidesWithAKnownName() {
        val hit = lookalike("https://arnazon.com", emptyList())
        assertEquals(LookalikeKind.Kerning, hit?.kind)
        assertEquals("amazon.com", hit?.neighbor)
    }

    @Test
    fun hiddenCharacterInAFamiliarName() {
        val hit = lookalike("https://pay\u200Bpal.com", emptyList())
        assertEquals(LookalikeKind.Homoglyph, hit?.kind)
        assertEquals("paypal.com", hit?.neighbor)
    }

    @Test
    fun punycodeDecodesToALookalike() {
        assertEquals("bücher.example", decodeHost("xn--bcher-kva.example"))
        val hit = lookalike("https://xn--pple-43d.com", emptyList())
        assertEquals(LookalikeKind.Homoglyph, hit?.kind)
        assertEquals("apple.com", hit?.neighbor)
    }
}
