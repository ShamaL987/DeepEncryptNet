from __future__ import annotations

import json
import logging
import os
import threading
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any
from dotenv import load_dotenv


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

log = logging.getLogger("FlowDaemon")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_json_path() -> Path:
    return _project_root() / "app" / "runtime_config.json"


def _load_local_env_file_if_applicable() -> None:
    raw_app_env = (os.getenv("APP_ENV") or "").strip().lower()

    if raw_app_env not in {"", "local"}:
        return

    env_path = _project_root() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


class EnvNamespace:
    VALID_ENVS = {"local", "staging", "production"}

    def __init__(self) -> None:
        _load_local_env_file_if_applicable()
        self._app_env = self._resolve_app_env()

    def _resolve_app_env(self) -> str:
        raw_env = (os.getenv("APP_ENV") or "local").strip().lower()
        return raw_env if raw_env in self.VALID_ENVS else "local"

    def reload(self) -> None:
        self._app_env = self._resolve_app_env()

    @property
    def app_env(self) -> str:
        return self._app_env

    def get(self, name: str, default: str | None = None, required: bool = False) -> str | None:
        value = os.getenv(name)

        if value not in {None, ""}:
            return value

        if default is not None:
            return default

        if required:
            raise ValueError(f"{name} is not configured")

        return None


class SettingsManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.env = EnvNamespace()
        self.app_env = self.env.app_env

        self.runtime_json_path = _runtime_json_path()
        self.runtime_json_path.parent.mkdir(parents=True, exist_ok=True)

        self.runtime_config = self._load_or_create_runtime_json()
        self.resolved_config = self._build_resolved_config()

    def _normalize_runtime_config(self, data: dict[str, Any]) -> dict[str, Any]:
        normalized = deepcopy(data)
        flow_daemon = normalized.get("flow_daemon")

        if flow_daemon is None:
            normalized["flow_daemon"] = {}
        elif not isinstance(flow_daemon, dict):
            raise ValueError("'flow_daemon' in runtime JSON must be an object")

        return normalized

    def _load_or_create_runtime_json(self) -> dict[str, Any]:
        if not self.runtime_json_path.exists():
            initial_data = {"flow_daemon": {}}
            self._write_runtime_json(initial_data)
            return initial_data

        with self.runtime_json_path.open("r", encoding="utf-8") as file:
            data = json.load(file) or {}

        if not isinstance(data, dict):
            raise ValueError("Runtime JSON config must contain a JSON object")

        normalized = self._normalize_runtime_config(data)
        if normalized != data:
            self._write_runtime_json(normalized)

        return normalized

    def _write_runtime_json(self, data: dict[str, Any]) -> None:
        with self.runtime_json_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    def _build_database_config(self) -> dict[str, Any]:
        return {
            "host": str(self.get_env("DATABASE_HOST", required=True)),
            "port": int(self.get_env("DATABASE_PORT", default="5432")),
            "name": str(self.get_env("DATABASE_NAME", required=True)),
            "user": str(self.get_env("DATABASE_USER", required=True)),
            "password": str(self.get_env("DATABASE_PASSWORD", required=True)),
        }

    def _build_auth_config(self) -> dict[str, Any]:
        return {
            "jwt_algorithm": str(self.get_env("JWT_ALGORITHM", required=True)),
            "jwt_access_token_expire_minutes": int(self.get_env("JWT_TIME", required=True)),
        }

    def _build_resolved_config(self) -> dict[str, Any]:
        return {
            "flow_daemon": deepcopy(self.runtime_config.get("flow_daemon", {})),
            "database": self._build_database_config(),
            "auth": self._build_auth_config(),
        }

    def reload(self) -> None:
        with self._lock:
            self.env.reload()
            self.app_env = self.env.app_env
            self.runtime_config = self._load_or_create_runtime_json()
            self.resolved_config = self._build_resolved_config()

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self.resolved_config)

    def get_flow_daemon_config(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self.resolved_config.get("flow_daemon", {}))

    def get_runtime_config(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self.runtime_config)

    def get_database_config(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self.resolved_config.get("database", {}))

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

            current_flow_daemon.update(updates)

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