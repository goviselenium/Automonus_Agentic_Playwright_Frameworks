import json
import os
import time
from typing import Optional, Dict, Any
from config.settings import settings


class LocatorRegistry:
    """
    Manages persistent storing, lookup, and patching of healed locators.
    """

    def __init__(self, registry_file: Optional[str] = None):
        self.registry_file = registry_file or settings.REGISTRY_FILE
        self._data: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self) -> None:
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"[LocatorRegistry] Warning: Failed to save registry to {self.registry_file}: {e}")

    def get_healed_locator(self, target_description: str, original_locator: Optional[str] = None) -> Optional[str]:
        """
        Lookup if a healed locator exists for a given target description or original locator.
        """
        key = self._make_key(target_description, original_locator)
        entry = self._data.get(key)
        if entry and entry.get("verified"):
            return entry.get("healed_locator")
        return None

    def register_heal(
        self,
        target_description: str,
        original_locator: str,
        healed_locator: str,
        strategy: str,
        confidence: float = 1.0,
        verified: bool = True
    ) -> None:
        """
        Register a new healed locator entry.
        """
        key = self._make_key(target_description, original_locator)
        self._data[key] = {
            "target_description": target_description,
            "original_locator": original_locator,
            "healed_locator": healed_locator,
            "strategy": strategy,
            "confidence": confidence,
            "verified": verified,
            "updated_at": time.time(),
            "iso_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        self.save()

    def _make_key(self, target_description: str, original_locator: Optional[str]) -> str:
        desc_clean = target_description.strip().lower()
        orig_clean = (original_locator or "").strip().lower()
        return f"{desc_clean}::{orig_clean}"
