package com.sledge.browser.android.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin

private val NordBg = Color(0xF0101012)
private val NordActive = Color(0xFF242428)
private val NordAccent = Color(0xFFD4652F)
private val NordText = Color(0xFFF3F3F1)
private val NordStroke = Color(0xFF3A3A3E)

/**
 * A ring (pie) menu drawn entirely on a [Canvas].
 *
 * Each segment corresponds to one [RingMenuAction]. Tapping a segment invokes its
 * [RingMenuAction.onSelect] callback and dismisses the menu via [onDismiss].
 *
 * The menu animates in by scaling from 0 → 1 over 200 ms.
 *
 * @param actions   The actions to arrange evenly around the ring.
 * @param onDismiss Called when the user taps outside the ring or selects an action.
 * @param radius    Outer radius of the ring in dp (default 130 dp).
 * @param holeRatio Fraction of [radius] left as an empty centre hole (default 0.35).
 */
data class RingMenuAction(
    val label: String,
    val onSelect: () -> Unit,
)

@Composable
fun RingMenu(
    actions: List<RingMenuAction>,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    radius: Dp = 130.dp,
    holeRatio: Float = 0.35f,
) {
    require(actions.isNotEmpty()) { "RingMenu requires at least one action." }

    val scale = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        scale.animateTo(1f, animationSpec = tween(durationMillis = 200))
    }

    var hoveredSegment by remember { mutableIntStateOf(-1) }
    val textMeasurer = rememberTextMeasurer()

    // Full-screen overlay so taps outside the ring are caught.
    Box(
        modifier = modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        Canvas(
            modifier = Modifier
                .size(radius * 2 + 40.dp)
                .pointerInput(actions) {
                    detectTapGestures(
                        onPress = { offset ->
                            val cx = size.width / 2f
                            val cy = size.height / 2f
                            val dx = offset.x - cx
                            val dy = offset.y - cy
                            val dist = kotlin.math.sqrt(dx * dx + dy * dy)
                            val radiusPx = radius.toPx()
                            val holePx = radiusPx * holeRatio
                            if (dist in holePx..radiusPx) {
                                val angle = (Math.toDegrees(atan2(dy.toDouble(), dx.toDouble()).toDouble()) + 360) % 360
                                val segSize = 360.0 / actions.size
                                hoveredSegment = (angle / segSize).toInt().coerceIn(0, actions.lastIndex)
                            }
                            tryAwaitRelease()
                            hoveredSegment = -1
                        },
                        onTap = { offset ->
                            val cx = size.width / 2f
                            val cy = size.height / 2f
                            val dx = offset.x - cx
                            val dy = offset.y - cy
                            val dist = kotlin.math.sqrt(dx * dx + dy * dy)
                            val radiusPx = radius.toPx()
                            val holePx = radiusPx * holeRatio
                            if (dist < holePx || dist > radiusPx) {
                                onDismiss()
                                return@detectTapGestures
                            }
                            val angle = (Math.toDegrees(atan2(dy.toDouble(), dx.toDouble()).toDouble()) + 360) % 360
                            val segSize = 360.0 / actions.size
                            val idx = (angle / segSize).toInt().coerceIn(0, actions.lastIndex)
                            actions[idx].onSelect()
                            onDismiss()
                        },
                    )
                },
        ) {
            scale(scale.value) {
                drawRingMenu(
                    actions = actions,
                    hoveredSegment = hoveredSegment,
                    radiusPx = radius.toPx(),
                    holeRatio = holeRatio,
                    textMeasurer = textMeasurer,
                )
            }
        }
    }
}

private fun DrawScope.drawRingMenu(
    actions: List<RingMenuAction>,
    hoveredSegment: Int,
    radiusPx: Float,
    holeRatio: Float,
    textMeasurer: androidx.compose.ui.text.TextMeasurer,
) {
    val cx = size.width / 2f
    val cy = size.height / 2f
    val center = Offset(cx, cy)
    val holePx = radiusPx * holeRatio
    val segAngle = 360f / actions.size
    val gapDeg = 2f // thin gap between segments

    actions.forEachIndexed { i, action ->
        val startDeg = i * segAngle + gapDeg / 2f
        val sweepDeg = segAngle - gapDeg

        val fillColor = if (i == hoveredSegment) NordAccent else NordBg

        // Draw the pie segment as a Path (arc + inner arc cutout)
        val path = buildSegmentPath(cx, cy, radiusPx, holePx, startDeg, sweepDeg)
        drawPath(path, fillColor)
        drawPath(path, NordStroke, style = Stroke(width = 1.5.dp.toPx(), cap = StrokeCap.Round))

        // Label at the midpoint of the arc
        val midDeg = startDeg + sweepDeg / 2f
        val midRad = Math.toRadians(midDeg.toDouble())
        val labelR = (radiusPx + holePx) / 2f
        val lx = cx + (labelR * cos(midRad)).toFloat()
        val ly = cy + (labelR * sin(midRad)).toFloat()

        val textColor = if (i == hoveredSegment) NordBg else NordText
        val measured = textMeasurer.measure(
            action.label,
            style = TextStyle(color = textColor, fontSize = 11.sp),
        )
        drawText(
            textLayoutResult = measured,
            topLeft = Offset(lx - measured.size.width / 2f, ly - measured.size.height / 2f),
        )
    }
}

private fun buildSegmentPath(
    cx: Float, cy: Float,
    outerR: Float, innerR: Float,
    startDeg: Float, sweepDeg: Float,
): Path {
    val startRad = Math.toRadians(startDeg.toDouble())
    val endRad   = Math.toRadians((startDeg + sweepDeg).toDouble())
    return Path().apply {
        // Start at inner arc start
        moveTo(
            cx + (innerR * cos(startRad)).toFloat(),
            cy + (innerR * sin(startRad)).toFloat(),
        )
        // Line to outer arc start
        lineTo(
            cx + (outerR * cos(startRad)).toFloat(),
            cy + (outerR * sin(startRad)).toFloat(),
        )
        // Outer arc
        arcTo(
            rect = androidx.compose.ui.geometry.Rect(cx - outerR, cy - outerR, cx + outerR, cy + outerR),
            startAngleDegrees = startDeg,
            sweepAngleDegrees = sweepDeg,
            forceMoveTo = false,
        )
        // Line to inner arc end
        lineTo(
            cx + (innerR * cos(endRad)).toFloat(),
            cy + (innerR * sin(endRad)).toFloat(),
        )
        // Inner arc (reversed)
        arcTo(
            rect = androidx.compose.ui.geometry.Rect(cx - innerR, cy - innerR, cx + innerR, cy + innerR),
            startAngleDegrees = startDeg + sweepDeg,
            sweepAngleDegrees = -sweepDeg,
            forceMoveTo = false,
        )
        close()
    }
}
