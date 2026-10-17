package com.sledge.browser.android.ui

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

/**
 * Forged-steel palette. Near-black chrome, square corners, one hot-metal accent.
 */
object SledgeTheme {
    val Background = Color(0xFF0C0C0E)
    val Chrome = Color(0xFF080808)
    val Surface = Color(0xFF161618)
    val Elevated = Color(0xFF242428)
    val Accent = Color(0xFFE7E2D6)
    val Strike = Color(0xFFD4652F)
    val Text = Color(0xFFF3F3F1)
    val Dim = Color(0xFFB5B5B0)
    val Muted = Color(0xFF6A6A66)
    val Yellow = Color(0xFFD6B15A)
    val Orange = Color(0xFFD4652F)
    val Red = Color(0xFFC45050)
    val Green = Color(0xFF7D9A72)

    val Corner = RoundedCornerShape(2.dp)

    val groupColors: List<Long> = listOf(
        0xFFD4652F,
        0xFFC9A36A,
        0xFF8FA37A,
        0xFF7E93A8,
        0xFFA88898,
        0xFFB5B5B0,
        0xFFC45050,
        0xFF8A8A6A,
    )
}

fun Long.toComposeColor(): Color = Color(toInt())
