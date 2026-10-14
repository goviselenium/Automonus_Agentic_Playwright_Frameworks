try:
    from core.browser_manager import BrowserManager
except ImportError:
    BrowserManager = None

try:
    from core.dom_extractor import DOMExtractor
except ImportError:
    DOMExtractor = None

try:
    from core.locator_registry import LocatorRegistry
except ImportError:
    LocatorRegistry = None

try:
    from core.security_masker import SecurityMasker
except ImportError:
    SecurityMasker = None

try:
    from core.reporter import Reporter
except ImportError:
    Reporter = None

__all__ = [
    "BrowserManager",
    "DOMExtractor",
    "LocatorRegistry",
    "SecurityMasker",
    "Reporter"
]
