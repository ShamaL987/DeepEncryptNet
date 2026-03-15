from __future__ import annotations

import json
import logging
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any
from functools import lru_cache

import yaml


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

log = logging.getLogger("FlowDaemon")


class SettingsManager:
    def __init__(self, yaml_path: str | None = None):
        self._lock = threading.RLock()

        self.yaml_path = Path(yaml_path or self._resolve_yaml_path()).resolve()
        self.yaml_config = self._load_yaml(self.yaml_path)

        flow_daemon_cfg = self.yaml_config.get("flow_daemon", {})
        runtime_json_path = flow_daemon_cfg.get("runtime_json_path")
        if not runtime_json_path:
            raise KeyError("Missing 'flow_daemon.runtime_json_path' in YAML config")

        runtime_json_path_obj = Path(runtime_json_path)
        if not runtime_json_path_obj.is_absolute():
            runtime_json_path_obj = (runtime_json_path_obj).resolve()

        self.runtime_json_path = runtime_json_path_obj
        self.runtime_json_path.parent.mkdir(parents=True, exist_ok=True)

        self.runtime_config = self._load_or_create_runtime_json()
        self.resolved_config = self._build_resolved_config()

    def _resolve_yaml_path(self) -> str:
        explicit = os.getenv("CONFIG_PATH")
        if explicit:
            return str(Path(explicit).resolve())

        base_dir = Path(__file__).resolve().parent

        env = os.getenv("APP_ENV", "local").strip().lower()
        if env == "docker":
            docker_path = os.getenv("DOCKER_CONFIG_PATH")
            return str(
                (Path(docker_path).resolve() if docker_path else (base_dir / "config.docker.yaml").resolve())
            )

        local_path = os.getenv("LOCAL_CONFIG_PATH")
        return str(
            (Path(local_path).resolve() if local_path else (base_dir / "config.local.yaml").resolve())
        )

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"YAML config file not found: {path.resolve()}")

        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML config: {e}") from e

        if "flow_daemon" not in data:
            raise KeyError("Missing required 'flow_daemon' section in YAML config")

        if "database" not in data:
            raise KeyError("Missing required 'database' section in YAML config")

        return data

    def _load_or_create_runtime_json(self) -> dict[str, Any]:
        if not self.runtime_json_path.exists():
            self._write_runtime_json({})
            return {}

        try:
            with self.runtime_json_path.open("r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse runtime JSON config: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("Runtime JSON config must contain a JSON object")

        return data

    def _write_runtime_json(self, data: dict[str, Any]) -> None:
        with self.runtime_json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _build_resolved_config(self) -> dict[str, Any]:
        merged = deepcopy(self.yaml_config)

        yaml_flow_daemon = deepcopy(self.yaml_config.get("flow_daemon", {}))
        yaml_flow_daemon.pop("runtime_json_path", None)

        runtime_flow_daemon = deepcopy(self.runtime_config.get("flow_daemon", {}))
        if not isinstance(runtime_flow_daemon, dict):
            raise ValueError("'flow_daemon' in runtime JSON must be an object")

        yaml_flow_daemon.update(runtime_flow_daemon)
        merged["flow_daemon"] = yaml_flow_daemon

        return merged

    def reload(self) -> None:
        with self._lock:
            self.yaml_config = self._load_yaml(self.yaml_path)
            self.runtime_config = self._load_or_create_runtime_json()
            self.resolved_config = self._build_resolved_config()

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self.resolved_config)

    def get_section(self, section: str, default=None):
        with self._lock:
            value = self.resolved_config.get(section, default)
            return deepcopy(value)

    def get_flow_daemon_config(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self.resolved_config.get("flow_daemon", {}))

    def get_runtime_config(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self.runtime_config)

    def get_runtime_flow_daemon_config(self) -> dict[str, Any]:
        with self._lock:
            value = self.runtime_config.get("flow_daemon", {})
            if not isinstance(value, dict):
                return {}
            return deepcopy(value)

    def update_runtime_flow_daemon_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(updates, dict):
            raise ValueError("Runtime flow daemon updates must be a dictionary")

        with self._lock:
            current_flow_daemon = self.runtime_config.get("flow_daemon", {})
            if not isinstance(current_flow_daemon, dict):
                current_flow_daemon = {}

            for key, value in updates.items():
                if key in current_flow_daemon:
                    current_flow_daemon[key] = value

            self.runtime_config["flow_daemon"] = current_flow_daemon
            self._write_runtime_json(self.runtime_config)
            self.resolved_config = self._build_resolved_config()

            return deepcopy(current_flow_daemon)


@lru_cache()
def get_settings_manager() -> SettingsManager:
    return SettingsManager()