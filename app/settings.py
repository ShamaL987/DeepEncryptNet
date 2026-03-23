from __future__ import annotations

import json
import logging
import os
import threading
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

log = logging.getLogger("FlowDaemon")


import os


class EnvNamespace:
    LOCAL_MOCK_DEFAULTS = {
        "ADMIN_BOOTSTRAP_TOKEN": "123456789",
        "JWT_SECRET_KEY": "jwt-secret-local",
        "JWT_ALGORITHM": "HS256",
        "JWT_TIME": 10000,
        "API_TOKEN_ENCRYPTION_KEY": "tPQ2uA9fB4Kaq4F9TwxtoZBp2AQ9KQl6IsfaNH-B7Xc="
    }

    @property
    def app_env(self) -> str:
        raw_env = (os.getenv("APP_ENV") or "").strip().lower()
        return raw_env if raw_env in {"staging", "production"} else "local"

    def __getattr__(self, name: str) -> str | None:
        return self.get(name)

    def __getitem__(self, name: str) -> str | None:
        return self.get(name)

    def get(self, name: str, default: str | None = None, required: bool = False) -> str | None:
        value = os.getenv(name)
        if value:
            return value

        if self.app_env == "local" and name in self.LOCAL_MOCK_DEFAULTS:
            return self.LOCAL_MOCK_DEFAULTS[name]

        if default is not None:
            return default

        if required:
            raise ValueError(f"{name} is not configured")

        return None

    def as_dict(self) -> dict[str, str]:
        merged = dict(os.environ)

        if self.app_env == "local":
            for key, value in self.LOCAL_MOCK_DEFAULTS.items():
                merged.setdefault(key, value)

        merged["APP_ENV"] = self.app_env
        return merged


class SettingsManager:
    def __init__(self, yaml_path: str | None = None):
        self._lock = threading.RLock()
        self.env = EnvNamespace()

        self.app_env = (self.env.get("APP_ENV", "local") or "local").strip().lower()

        self.yaml_path = Path(yaml_path or self._resolve_yaml_path()).resolve()
        self.yaml_config = self._load_yaml(self.yaml_path)

        flow_daemon_cfg = self.yaml_config.get("flow_daemon", {})
        runtime_json_path = flow_daemon_cfg.get("runtime_json_path")
        if not runtime_json_path:
            raise KeyError("Missing 'flow_daemon.runtime_json_path' in YAML config")

        # runtime_json_path_obj = Path(runtime_json_path)
        # if not runtime_json_path_obj.is_absolute():
        #     runtime_json_path_obj = runtime_json_path_obj.resolve()

        self.runtime_json_path =  Path(runtime_json_path)
        self.runtime_json_path.parent.mkdir(parents=True, exist_ok=True)

        self.runtime_config = self._load_or_create_runtime_json()
        self.resolved_config = self._build_resolved_config()

    def _resolve_yaml_path(self) -> str:
        explicit = self.env.get("CONFIG_PATH")
        if explicit:
            return str(Path(explicit).resolve())

        base_dir = Path(__file__).resolve().parent

        config_file_by_env = {
            "staging": "config.local.yaml",
            "production": "config.server.yaml",
        }

        selected_file = config_file_by_env.get(self.app_env, "config.local.yaml")
        return str((base_dir / selected_file).resolve())

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"YAML config file not found: {path.resolve()}")

        try:
            with path.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Failed to parse YAML config: {exc}") from exc

        if "flow_daemon" not in data:
            raise KeyError("Missing required 'flow_daemon' section in YAML config")

        return data

    def _load_or_create_runtime_json(self) -> dict[str, Any]:
        if not self.runtime_json_path.exists():
            self._write_runtime_json({})
            return {}

        try:
            with self.runtime_json_path.open("r", encoding="utf-8") as file:
                data = json.load(file) or {}
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse runtime JSON config: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError("Runtime JSON config must contain a JSON object")

        return data

    def _write_runtime_json(self, data: dict[str, Any]) -> None:
        with self.runtime_json_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

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
            self.app_env = (self.env.get("APP_ENV", "local") or "local").strip().lower()
            self.yaml_path = Path(self._resolve_yaml_path()).resolve()
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

    def get_auth_config(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self.resolved_config.get("auth", {}))

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

    def get_env(self, name: str, default: str | None = None, required: bool = False) -> str | None:
        return self.env.get(name, default=default, required=required)

    @property
    def admin_bootstrap_token(self) -> str:
        return str(self.get_env("ADMIN_BOOTSTRAP_TOKEN", required=True))

    @property
    def jwt_secret_key(self) -> str:
        return str(self.get_env("JWT_SECRET_KEY", required=True))

    @property
    def jwt_algorithm(self) -> str:
        return str(self.get_env("JWT_ALGORITHM", required=True))

    @property
    def jwt_access_token_expire_minutes(self) -> int:
        return int(self.get_env("JWT_TIME", required=True))

    @property
    def api_token_encryption_key(self) -> str:
        return str(self.get_env("API_TOKEN_ENCRYPTION_KEY", required=True))


@lru_cache()
def get_settings_manager() -> SettingsManager:
    return SettingsManager()