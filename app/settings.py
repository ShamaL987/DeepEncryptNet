from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
import yaml


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

log = logging.getLogger("FlowDaemon")



class Settings:
    """Loads and validates application configuration."""
    def __init__(self, config_path: str | None = None):
        self.config_path = Path(config_path or os.getenv("CONFIG_PATH", "app/config.yaml"))
        self.data = self._load_config()

    def _load_config(self) -> dict:
        """Parses YAML and enforces required sections."""
        if not self.config_path.exists():
            alt = Path(__file__).resolve().parent.parent / "config.yml"
            if alt.exists():
                self.config_path = alt
            else:
                raise FileNotFoundError(f"Config file not found: {self.config_path.resolve()}\nPlease create a valid config.yml before starting the server.")
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML config: {e}")
        if "flow_daemon" not in data:
            raise KeyError("Missing required 'flow_daemon' section in config.yml")
        if "database" not in data:
            raise KeyError("Missing required 'database' section in config.yml")
        return data

    def get(self, key: str, default=None):
        """Returns a top-level config section or default."""
        return self.data.get(key, default)

@lru_cache()
def get_settings() -> Settings:
    """Returns a cached Settings instance or exits on error."""
    try:
        return Settings()
    except Exception as e:
        print(f"[FATAL CONFIG ERROR] {e}")
        raise SystemExit(1)




