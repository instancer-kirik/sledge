package com.sledge.browser.security

/**
 * Visit-weighted hosts. Two hosts are neighbors when their names fold together
 * or sit one or two edits apart. A navigation to a neighbor of a heavier host
 * is treated as an imposter.
 */
data class HostWeight(val host: String, val visits: Int)

enum class LookalikeKind {
    HiddenCharacters,
    Homoglyph,
    MixedScript,
    EmbeddedName,
    Kerning,
    Misspelling,
}

data class LookalikeHit(
    /** Registrable host the user is about to open. */
    val host: String,
    /** Heavier or well-known host this name is imitating. */
    val neighbor: String,
    val neighborVisits: Int,
    val kind: LookalikeKind,
)

private data class Node(val host: String, val skeleton: String, val kerning: String, val visits: Int)

private val multiPartSuffixes = setOf(
    "co.uk", "org.uk", "ac.uk", "com.au", "net.au", "co.jp", "com.br", "co.nz", "com.mx", "co.za",
)

/** Brands that are impersonated often enough to check before any personal history exists. */
private val seedHosts = setOf(
    "google.com", "youtube.com", "facebook.com", "amazon.com", "apple.com",
    "microsoft.com", "paypal.com", "github.com", "netflix.com", "instagram.com",
    "linkedin.com", "duckduckgo.com", "wikipedia.org", "reddit.com", "yahoo.com",
    "whatsapp.com", "icloud.com", "outlook.com", "live.com", "binance.com", "coinbase.com",
)

/**
 * Returns a hit when [url] should not load without the user looking at it.
 * [visits] is the frequency side of the graph, usually one weight per history entry.
 */
fun lookalike(url: String, visits: List<HostWeight>): LookalikeHit? {
    val host = hostOf(url) ?: return null
    val decoded = decodeHost(host)
    val registered = registrable(decoded)
    if (registered.isBlank() || registered.none { it == '.' }) return null

    val hidden = decoded != stripHidden(decoded) || host != stripHidden(host)
    val cleaned = stripHidden(decoded)
    val skeleton = skeleton(cleaned)
    val kerning = kerningFold(skeleton)
    val nodes = graph(visits)

    val same = nodes.firstOrNull { it.host == registered }
    if (same != null && !hidden && cleaned == skeleton && !mixedScript(cleaned)) return null

    embedded(cleaned, registered, nodes)?.let { return it }
    if (hidden) {
        val neighbor = exact(skeleton, registered, nodes) ?: exact(kerning, registered, nodes)
        return LookalikeHit(
            host = registered,
            neighbor = neighbor?.host ?: registered,
            neighborVisits = neighbor?.visits ?: 0,
            kind = if (neighbor != null) LookalikeKind.Homoglyph else LookalikeKind.HiddenCharacters,
        )
    }
    exact(skeleton, registered, nodes)?.let { node ->
        if (cleaned != skeleton || mixedScript(cleaned)) {
            return LookalikeHit(registered, node.host, node.visits, LookalikeKind.Homoglyph)
        }
    }
    exact(kerning, registered, nodes)?.let { node ->
        if (kerning != skeleton && (node.visits >= 3 || node.visits == 0 || node.host in seedHosts)) {
            return LookalikeHit(registered, node.host, node.visits, LookalikeKind.Kerning)
        }
    }
    if (mixedScript(cleaned)) {
        return LookalikeHit(registered, skeleton, 0, LookalikeKind.MixedScript)
    }
    misspelling(skeleton, registered, nodes)?.let { return it }
    return null
}

private fun graph(visits: List<HostWeight>): List<Node> {
    val counts = linkedMapOf<String, Int>()
    for (seed in seedHosts) counts.putIfAbsent(seed, 0)
    for (visit in visits) {
        val host = registrable(decodeHost(visit.host.lowercase()))
        if (host.none { it == '.' }) continue
        counts[host] = (counts[host] ?: 0) + visit.visits.coerceAtLeast(1)
    }
    return counts.map { (host, count) ->
        val bone = skeleton(host)
        Node(host, bone, kerningFold(bone), count)
    }
}

private fun exact(folded: String, registered: String, nodes: List<Node>): Node? =
    nodes.firstOrNull { it.host != registered && (it.skeleton == folded || it.host == folded) }

private fun embedded(cleaned: String, registered: String, nodes: List<Node>): LookalikeHit? {
    val brand = nodes
        .filter { it.visits >= 2 || it.visits == 0 || it.host in seedHosts }
        .filter { node ->
            node.host != registered &&
                !cleaned.endsWith(".${node.host}") &&
                cleaned != node.host &&
                (cleaned.startsWith("${node.host}.") || cleaned.contains(".${node.host}."))
        }
        .maxByOrNull { it.visits + if (it.visits == 0) 1 else 0 }
        ?: return null
    return LookalikeHit(registered, brand.host, brand.visits, LookalikeKind.EmbeddedName)
}

private fun misspelling(skeleton: String, registered: String, nodes: List<Node>): LookalikeHit? {
    var best: Node? = null
    var bestDistance = Int.MAX_VALUE
    for (node in nodes) {
        if (node.host == registered || node.skeleton == skeleton) continue
        if (node.visits == 1 && node.host !in seedHosts) continue
        val distance = levenshtein(skeleton, node.skeleton)
        val limit = if (node.skeleton.length >= 10 && node.visits >= 3) 2 else 1
        if (node.skeleton.length < 5 || distance == 0 || distance > limit) continue
        val better = distance < bestDistance || (distance == bestDistance && node.visits > (best?.visits ?: -1))
        if (better) {
            best = node
            bestDistance = distance
        }
    }
    val neighbor = best ?: return null
    return LookalikeHit(registered, neighbor.host, neighbor.visits, LookalikeKind.Misspelling)
}

internal fun hostOf(url: String): String? {
    val trimmed = url.trim()
    val rest = if ("://" in trimmed) trimmed.substringAfter("://") else return null
    val authority = rest.substringBefore('/').substringBefore('?').substringBefore('#')
    if (authority.startsWith("[")) return null
    val host = authority.substringAfter('@').substringBefore(':').trim('.').lowercase()
    if (host.isBlank() || host.all { it.isDigit() || it == '.' }) return null
    return host
}

internal fun registrable(host: String): String {
    val labels = host.trim('.').split('.').filter { it.isNotEmpty() }
    if (labels.size < 2) return host.trim('.')
    val lastTwo = labels.takeLast(2).joinToString(".")
    if (labels.size >= 3 && lastTwo in multiPartSuffixes) {
        return labels.takeLast(3).joinToString(".")
    }
    return lastTwo
}

internal fun decodeHost(host: String): String =
    host.split('.').joinToString(".") { label ->
        if (label.startsWith("xn--")) punycodeDecode(label.removePrefix("xn--")) ?: label else label
    }

private fun stripHidden(value: String): String = buildString {
    for (ch in value) {
        if (ch in hidden || ch in '\u0300'..'\u036F') continue
        append(ch)
    }
}

private fun skeleton(value: String): String = buildString {
    for (ch in stripHidden(value)) {
        append(confusable[ch] ?: ch.lowercaseChar())
    }
}

/** Letters that collide when drawn tight: rn/m, vv/w, cl/d. */
private fun kerningFold(skeleton: String): String =
    skeleton.replace("rn", "m").replace("vv", "w").replace("cl", "d")

private fun mixedScript(value: String): Boolean {
    var latin = false
    var other = false
    for (ch in value) {
        if (ch in 'a'..'z' || ch in 'A'..'Z') latin = true
        if (ch in '\u0400'..'\u04FF' || ch in '\u0370'..'\u03FF') other = true
    }
    return latin && other
}

private fun levenshtein(left: String, right: String): Int {
    if (left == right) return 0
    if (kotlin.math.abs(left.length - right.length) > 2) return 3
    val prev = IntArray(right.length + 1) { it }
    val curr = IntArray(right.length + 1)
    for (i in left.indices) {
        curr[0] = i + 1
        for (j in right.indices) {
            val cost = if (left[i] == right[j]) 0 else 1
            curr[j + 1] = minOf(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost)
        }
        for (j in prev.indices) prev[j] = curr[j]
    }
    return prev[right.length]
}

private val hidden = setOf(
    '\u00AD', '\u200B', '\u200C', '\u200D', '\u200E', '\u200F', '\u2060', '\uFEFF',
    '\u202A', '\u202B', '\u202C', '\u202D', '\u202E', '\u2066', '\u2067', '\u2068', '\u2069',
)

private val confusable = mapOf(
    'а' to 'a', 'е' to 'e', 'о' to 'o', 'р' to 'p', 'с' to 'c', 'у' to 'y', 'х' to 'x',
    'і' to 'i', 'ѕ' to 's', 'ј' to 'j', 'һ' to 'h', 'ԁ' to 'd', 'ԛ' to 'q', 'ԝ' to 'w',
    'Ӏ' to 'l', 'ɡ' to 'g', 'ν' to 'v',
    'ο' to 'o', 'α' to 'a', 'ε' to 'e', 'ι' to 'i', 'τ' to 't', 'ρ' to 'p',
    '0' to 'o', '1' to 'l', '3' to 'e', '5' to 's', '6' to 'b', '7' to 't',
    'Ａ' to 'a', 'Ｂ' to 'b', 'Ｃ' to 'c', 'Ｅ' to 'e', 'Ｈ' to 'h', 'Ｋ' to 'k',
    'Ｍ' to 'm', 'Ｏ' to 'o', 'Ｐ' to 'p', 'Ｔ' to 't', 'Ｘ' to 'x', 'Ｙ' to 'y',
)

private fun punycodeDecode(input: String): String? {
    val base = 36
    val tMin = 1
    val tMax = 26
    val skew = 38
    val damp = 700
    val initialBias = 72
    val initialN = 128
    val output = StringBuilder()
    val delim = input.lastIndexOf('-')
    if (delim >= 0) output.append(input.substring(0, delim))
    var index = if (delim >= 0) delim + 1 else 0
    var n = initialN
    var i = 0
    var bias = initialBias
    while (index < input.length) {
        val oldI = i
        var w = 1
        var k = base
        while (true) {
            if (index >= input.length) return null
            val digit = punyDigit(input[index++]) ?: return null
            i += digit * w
            val t = when {
                k <= bias -> tMin
                k >= bias + tMax -> tMax
                else -> k - bias
            }
            if (digit < t) break
            w *= base - t
            k += base
        }
        val points = output.length + 1
        bias = adapt(i - oldI, points, oldI == 0, base, tMin, tMax, skew, damp)
        n += i / points
        i %= points
        output.insert(i, n.toChar())
        i++
    }
    return output.toString()
}

private fun punyDigit(ch: Char): Int? = when (ch) {
    in 'a'..'z' -> ch - 'a'
    in '0'..'9' -> ch - '0' + 26
    else -> null
}

private fun adapt(
    deltaIn: Int,
    points: Int,
    first: Boolean,
    base: Int,
    tMin: Int,
    tMax: Int,
    skew: Int,
    damp: Int,
): Int {
    var delta = if (first) deltaIn / damp else deltaIn / 2
    delta += delta / points
    var k = 0
    while (delta > ((base - tMin) * tMax) / 2) {
        delta /= base - tMin
        k += base
    }
    return k + ((base - tMin + 1) * delta) / (delta + skew)
}
