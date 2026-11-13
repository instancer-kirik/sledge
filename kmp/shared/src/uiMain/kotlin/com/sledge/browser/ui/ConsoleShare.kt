package com.sledge.browser.ui

import java.net.InetSocketAddress
import java.net.Socket
import java.net.URI
import java.net.URL
import javax.net.ssl.HttpsURLConnection

internal fun List<ConsoleLine>.asShareText(): String = joinToString("\n") { line ->
    val where = if (line.source.isBlank()) "" else " (${line.source}:${line.line})"
    "${line.level.name.lowercase()}: ${line.message}$where"
}

/**
 * Posts plain text to a URL the user typed. Ordinary page loads still refuse
 * cleartext except localhost. This call is the exception, so a share server on
 * a LAN address can receive the console without opening http browsing.
 */
internal fun postConsole(endpoint: String, body: String): String {
    val trimmed = endpoint.trim()
    val uri = try {
        URI(trimmed)
    } catch (error: IllegalArgumentException) {
        error("That URL is not valid")
    }
    val host = uri.host?.takeIf { it.isNotBlank() } ?: error("The URL needs a host")
    val path = buildString {
        append(uri.rawPath?.takeIf { it.isNotEmpty() } ?: "/")
        if (!uri.rawQuery.isNullOrEmpty()) append('?').append(uri.rawQuery)
    }
    return when (uri.scheme?.lowercase()) {
        "https" -> postHttps(trimmed, body)
        "http" -> postHttp(host, if (uri.port == -1) 80 else uri.port, path, body)
        else -> error("Start the URL with http:// or https://")
    }
}

private fun postHttps(endpoint: String, body: String): String {
    val connection = (URL(endpoint).openConnection() as HttpsURLConnection).apply {
        requestMethod = "POST"
        doOutput = true
        connectTimeout = 8_000
        readTimeout = 8_000
        setRequestProperty("Content-Type", "text/plain; charset=utf-8")
    }
    try {
        connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        return "HTTP ${connection.responseCode}"
    } finally {
        connection.disconnect()
    }
}

private fun postHttp(host: String, port: Int, path: String, body: String): String {
    val payload = body.toByteArray(Charsets.UTF_8)
    val header = buildString {
        append("POST ").append(path).append(" HTTP/1.1\r\n")
        append("Host: ").append(host).append(':').append(port).append("\r\n")
        append("Content-Type: text/plain; charset=utf-8\r\n")
        append("Content-Length: ").append(payload.size).append("\r\n")
        append("Connection: close\r\n\r\n")
    }.toByteArray(Charsets.UTF_8)
    Socket().use { socket ->
        socket.connect(InetSocketAddress(host, port), 8_000)
        socket.soTimeout = 8_000
        val out = socket.getOutputStream()
        out.write(header)
        out.write(payload)
        out.flush()
        val status = socket.getInputStream().bufferedReader().readLine().orEmpty()
        val code = status.substringAfter(' ').substringBefore(' ')
        return if (code.isBlank()) "No response" else "HTTP $code"
    }
}
