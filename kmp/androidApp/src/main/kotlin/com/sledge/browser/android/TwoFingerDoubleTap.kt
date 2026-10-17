package com.sledge.browser.android

import android.view.MotionEvent
import android.view.ViewConfiguration

/**
 * Recognises a stationary two-finger double tap.
 *
 * A pinch or a drag does not count. The detector never consumes the event, so
 * the page still scrolls and zooms.
 */
class TwoFingerDoubleTap(slopPx: Float) {
    private val slopSq = slopPx * slopPx
    private var downAt = 0L
    private var originX = 0f
    private var originY = 0f
    private var moved = false
    private var lastLift = 0L

    /** @return true once, when the second quick two-finger tap lands. */
    fun detect(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_POINTER_DOWN -> if (event.pointerCount == 2) {
                downAt = event.eventTime
                originX = event.getX(0)
                originY = event.getY(0)
                moved = false
            }
            MotionEvent.ACTION_MOVE -> if (event.pointerCount >= 2 && !moved) {
                val dx = event.getX(0) - originX
                val dy = event.getY(0) - originY
                if (dx * dx + dy * dy > slopSq) moved = true
            }
            MotionEvent.ACTION_POINTER_UP -> {
                val heldStill = event.pointerCount == 2 &&
                    !moved &&
                    event.eventTime - downAt <= TAP_MS
                if (!heldStill) return false
                val now = event.eventTime
                val second = now - lastLift in 1..DOUBLE_MS
                lastLift = if (second) 0L else now
                return second
            }
            MotionEvent.ACTION_CANCEL -> {
                moved = true
                lastLift = 0L
            }
        }
        return false
    }

    companion object {
        private const val TAP_MS = 280L
        private const val DOUBLE_MS = 340L

        fun create(configuration: ViewConfiguration) =
            TwoFingerDoubleTap(configuration.scaledTouchSlop.toFloat())
    }
}
