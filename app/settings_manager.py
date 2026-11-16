"""
Application Settings and State Persistence Manager.
Saves user preferences, recent transfers, network defaults, and UI themes.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("OneClickLAN.Settings")

SETTINGS_DIR = Path(os.environ.get("LOCALAPPDATA", ".")) / "OneClickLAN"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "theme": "dark",
    "port": 52428,
    "chunk_size_kb": 2048,  # 2 MB buffer size
    "default_save_dir": str(Path.home() / "Downloads" / "OneClickLAN_Transfers"),
    "auto_restore_network": True,
    "verify_sha256": True,
    "auto_retry_count": 5,
    "host_ip": "192.168.50.1",
    "client_ip": "192.168.50.2",
    "recent_transfers": []
}

class SettingsManager:
    def __init__(self, settings_file: Path = SETTINGS_FILE):
        self.settings_file = settings_file
        self.data: Dict[str, Any] = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self) -> None:
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
                logger.info(f"Loaded settings from {self.settings_file}")
            except Exception as e:
                logger.warning(f"Failed to load settings file, using defaults: {e}")
        else:
            self.save()

    def save(self) -> None:
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            logger.info("Saved settings to disk.")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def add_transfer_history(self, record: Dict[str, Any]) -> None:
        history: List[Dict[str, Any]] = self.data.get("recent_transfers", [])
        history.insert(0, record)
        # Keep last 50 entries
        self.data["recent_transfers"] = history[:50]
        self.save()

    def clear_history(self) -> None:
        self.data["recent_transfers"] = []
        self.save()
