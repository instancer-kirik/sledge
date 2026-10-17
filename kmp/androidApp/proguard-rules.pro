# WebView clients and the blob bridge are reached from the system WebView and from JS.
-keep class com.sledge.browser.android.engine.SledgeWebView { *; }
-keep class com.sledge.browser.android.engine.SledgeWebViewClient { *; }
-keep class com.sledge.browser.android.engine.SledgeWebChromeClient { *; }
-keep class com.sledge.browser.android.engine.BlobDownloadBridge { *; }
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# Brave adblock JNI wrapper (org.mlm.adblock.AdblockEngine and friends).
-keep class org.mlm.adblock.** { *; }
-keepclasseswithmembernames class * {
    native <methods>;
}
