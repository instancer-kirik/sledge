# Sledge Browser

The working browser is the Android app in `kmp/`. The PyQt desktop code remains in the tree as reference. `sledge/browser/core.py` is the previous full desktop window.

## Features

Shipped in the Android app:

- Tab groups, hibernation, and a ring menu
- History, bookmarks, and find-in-page
- Dark mode
- Ad blocking
- Inline and fullscreen video playback
- Downloads, file uploads, and camera, microphone, and location prompts

Held in `sledge/browser/core.py` for reference, and not yet in the Android app:

- Codec setup and media-error handling for embedded video
- Session save and restore
- Workspaces
- DevTools and element inspect
- Settings and URL suggestions
- Extension manager hooks
