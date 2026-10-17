package com.sledge.browser.android

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.view.MotionEvent
import android.view.ViewConfiguration
import android.webkit.WebView
import java.io.File
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.ui.graphics.Color
import com.sledge.browser.adblock.AdBlocker
import com.sledge.browser.android.engine.BraveAdBlock
import com.sledge.browser.android.ui.BrowserScreen

private val SteelBackground = Color(0xFF0C0C0E)
private val SteelSurface = Color(0xFF161618)
private val SteelAccent = Color(0xFFD4652F)
private val SteelOnSurface = Color(0xFFF3F3F1)
private val SteelOnPrimary = Color(0xFF0C0C0E)

/** Material 3 scheme for the forged-steel chrome. */
private val SledgeDarkColorScheme = darkColorScheme(
    primary = SteelAccent,
    onPrimary = SteelOnPrimary,
    background = SteelBackground,
    surface = SteelSurface,
    onSurface = SteelOnSurface,
    onBackground = SteelOnSurface,
    surfaceVariant = Color(0xFF242428),
    onSurfaceVariant = Color(0xFFB5B5B0),
    outline = Color(0xFF3A3A3E),
)

/**
 * Entry-point activity for Sledge on Android.
 *
 * Owns the session [store] and the [desk] (tabs, groups, memory).
 * The [android.webkit.WebView] itself lives inside [BrowserScreen].
 */
class MainActivity : ComponentActivity() {

    private val desk = TabDesk()
    private val store = BrowserStore()
    private val session by lazy { SessionFile(File(filesDir, "session.json")) }
    private val adBlocker = AdBlocker()
    private lateinit var brave: BraveAdBlock
    private lateinit var twoFingerDoubleTap: TwoFingerDoubleTap

    /** Set by the browser screen. Fired on a two-finger double tap. */
    var onTwoFingerDoubleTap: (() -> Unit)? = null

    override fun dispatchTouchEvent(ev: MotionEvent): Boolean {
        if (::twoFingerDoubleTap.isInitialized && twoFingerDoubleTap.detect(ev)) {
            onTwoFingerDoubleTap?.invoke()
        }
        return super.dispatchTouchEvent(ev)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            WebView.startSafeBrowsing(applicationContext) { _ -> }
        }
        twoFingerDoubleTap = TwoFingerDoubleTap.create(ViewConfiguration.get(this))
        brave = BraveAdBlock(applicationContext)

        session.load(desk, store)
        desk.onChanged = { session.save(desk, store) }
        store.onChanged = { session.save(desk, store) }

        adBlocker.loadRules(assets.open("adblock.txt").bufferedReader().readLines())
        adBlocker.enabled = store.settings.blockAds
        brave.enabled = store.settings.blockAds
        brave.start()

        val launch = externalWebUrl(intent?.dataString)
        if (desk.tabs.isEmpty()) desk.open(launch ?: START_PAGE)
        else if (launch != null) desk.open(launch)

        setContent {
            MaterialTheme(colorScheme = SledgeDarkColorScheme) {
                BrowserScreen(
                    desk = desk,
                    store = store,
                    adBlocker = adBlocker,
                    brave = brave,
                )
            }
        }
    }

    override fun onStop() {
        session.save(desk, store)
        super.onStop()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        externalWebUrl(intent.dataString)?.let { desk.open(it) }
    }
}
