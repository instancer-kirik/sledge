import os
import threading
import urllib.request

try:
    import adblock as _adblock  # type: ignore[import]

    _adblock_FilterSet = _adblock.FilterSet
    _adblock_Engine = _adblock.Engine
    _ADBLOCK_AVAILABLE: bool = True
except ImportError:
    _adblock = None  # type: ignore[assignment]
    _adblock_FilterSet = None  # type: ignore[assignment]
    _adblock_Engine = None  # type: ignore[assignment]
    _ADBLOCK_AVAILABLE = False

FILTER_LISTS = [
    "https://easylist.to/easylist/easylist.txt",
    "https://easylist.to/easylist/easyprivacy.txt",
    "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/filters.txt",
]

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "sledge", "adblock")


class AdBlocker:
    """Ad/tracker blocker backed by the Brave adblock engine."""

    def __init__(self):
        self._engine = None
        self._enabled = _ADBLOCK_AVAILABLE
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return _ADBLOCK_AVAILABLE

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value and _ADBLOCK_AVAILABLE

    def load_async(self, filter_urls: list[str] | None = None):
        """Fetch and compile filter lists in a background thread."""
        if not _ADBLOCK_AVAILABLE:
            return
        thread = threading.Thread(
            target=self._load,
            args=(filter_urls or FILTER_LISTS,),
            daemon=True,
        )
        thread.start()

    def should_block(
        self, url: str, source_url: str = "", resource_type: str = "other"
    ) -> bool:
        """Return True if the request should be blocked."""
        if not self._enabled:
            return False
        with self._lock:
            if self._engine is None:
                return False
            result = self._engine.check_network_urls(url, source_url, resource_type)
            return result.matched and not result.exception

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self, filter_urls: list[str]):
        os.makedirs(CACHE_DIR, exist_ok=True)
        filter_set = _adblock_FilterSet()

        for url in filter_urls:
            rules = self._fetch_list(url)
            for rule in rules:
                rule = rule.strip()
                if rule:
                    try:
                        filter_set.add_filter_rule(rule)
                    except Exception:
                        pass

        engine = _adblock_Engine(filter_set)
        with self._lock:
            self._engine = engine

    def _fetch_list(self, url: str) -> list[str]:
        cache_file = os.path.join(CACHE_DIR, url.split("/")[-1])
        # Use cached copy if it's less than 24 h old
        try:
            if os.path.exists(cache_file):
                age = os.path.getmtime(cache_file)
                import time

                if time.time() - age < 86400:
                    with open(cache_file, "r", encoding="utf-8", errors="ignore") as f:
                        return f.readlines()
        except OSError:
            pass

        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(content)
            return content.splitlines()
        except Exception:
            # Fall back to cached copy even if stale
            try:
                with open(cache_file, "r", encoding="utf-8", errors="ignore") as f:
                    return f.readlines()
            except OSError:
                return []
