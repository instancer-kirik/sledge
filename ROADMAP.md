# Sledge roadmap

Sign-in storage is in place on Android and desktop as of 17 Nov 2026. One piece of that work is still open. After it lands, stop and change topics.

## Now

Save and reload the desktop session beside the cookie flush.

Android already writes tabs, history, bookmarks, and per-site location choices to `session.json`. Desktop has the same file and never loads it, so those start empty every launch even though cookies now persist. Call it from startup and from window close, next to `flushDesktopCookies()`.

## What the app is

Desktop embeds Chromium through JCEF and CEF. The running build is Chromium 147.0.7727.118 on CEF 147.0.10. Android uses `android.webkit.WebView`.

Both of those are the page engine: Blink, the network stack, and a page process. Chrome's browser layer sits above that. Extensions, the Web Store, service workers, and `chrome.*` live in that upper layer. Brave ships it. CEF and Android `WebView` leave it out. There is no extension package to link into the current engines.

The app is a browser for pages, tabs, and sessions. It is not a Chrome or Firefox build with one feature missing.

## Already in place

Tabs, groups, hibernation, history, bookmarks, find-in-page, dark mode, ad blocking, downloads, uploads, and the Android permission prompts. Android session restore. Cookie acceptance and flush on Android. A stable Chromium profile on desktop, with session cookies kept and the cookie key left in the keyring.

Extensions, as they exist today, unpack a `.zip` or `.crx` in `ExtensionCatalog` and inject that package's content scripts after a page finishes loading. The same catalog runs on both targets. Background pages and `chrome.*` are outside it.

## Still missing, besides extensions

- Desktop session restore. This is the open item above.
- Remembered desktop camera and microphone answers. Desktop asks again on every visit, and the in-memory permission gate is not what Chromium calls. Location never reaches the desktop prompt in this JCEF build.
- History in the address bar. Suggestions currently offer open tabs, a new tab on that site, and a web search.
- Passwords and autofill. Cookies keep a session. They do not fill a login form.
- Site notifications. Neither target handles a site asking to notify.
- Adblock exceptions. The blocker skips `@@` rules, so a broken site cannot be allow-listed.
- Workspaces. The old desktop browser had them. The current app has tab groups.
- The desktop download handler. Saving a file can throw `NoSuchMethodError: onBeforeDownload` and exit the process. That crash is what stopped an extension file from being unpacked.

## Security choice

The desktop cookie jar lives in `~/.local/share/sledge`. Chromium encrypts that jar with a key held by the native keyring (GNOME Keyring or KWallet through the Secret Service). Sledge does not pass `--password-store=basic`.

That flag would keep sign-in working when the keyring is locked, and it would also leave the decryption key where any process that can read the profile can use it. The keyring is the practice we want. The session has to be unlocked for cookies to decrypt on the next launch. That is the cost of the choice.

Android does not need a separate keystore for this. WebView cookies stay in the app's private data, and `AndroidBrowserProfile` flushes them in `onStop`.

## Next

Make the desktop app feel like the same browser.

- Remember camera and microphone answers, and get location to the desktop prompt if this JCEF build can deliver it.
- Offer history in the address bar.

## Later

Passwords and autofill. That is a new store and should not start until the desktop session restore is in. If saved passwords are added, their key belongs in the same native keyring, not in the profile directory.

After that, only when a site needs them: notifications, adblock `@@` exceptions, and workspaces.

## Extensions, when we choose to do them

Desktop is the target. Real Chrome extensions mean replacing the desktop engine, not growing `ExtensionCatalog`.

What has to come out is the KCEF startup, `DesktopBrowserPage`, and the JCEF handlers for downloads, files, and permissions. What has to come in is a Chromium browser build that includes the extension service. The shared screen can stay if that engine still implements `BrowserPage`. Installed extensions would live in that browser's profile, beside the cookie jar, instead of being unpacked and injected by Sledge.

Mobile can keep the content-script catalog. It cannot run a Chrome extension on `WebView`, and Chrome on Android does not run them either. A mobile build that did would be a separate Chromium browser for Android, not this `WebView` shell and not the same runtime as the desktop browser.

Until that engine swap, the honest install path remains a `.zip` or `.crx` whose content scripts run after load.
