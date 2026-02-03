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
    def __init__(self, config_path: str | None = None):
        default_cfg = "config.docker.yaml" if os.getenv("APP_ENV") == "docker" else "config.local.yaml"
        self.config_path = Path(config_path or os.getenv("CONFIG_PATH", default_cfg))
        self.data = self._load_config()

    def _resolve_config_path(self) -> str:
        explicit = os.getenv("CONFIG_PATH")
        if explicit:
            return explicit

        env = os.getenv("APP_ENV", "local").strip().lower()
        if env == "docker":
            return os.getenv("DOCKER_CONFIG_PATH", "app/config.docker.yaml")

        return os.getenv("LOCAL_CONFIG_PATH", "app/config.yaml")

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            alt = Path(__file__).resolve().parent.parent / "config.yml"
            if alt.exists():
                self.config_path = alt
            else:
                raise FileNotFoundError(
                    f"Config file not found: {self.config_path.resolve()}\n"
                    f"Please create a valid config.yml before starting the server."
                )
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
        return self.data.get(key, default)


@lru_cache()
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        print(f"[FATAL CONFIG ERROR] {e}")
        raise SystemExit(1)
