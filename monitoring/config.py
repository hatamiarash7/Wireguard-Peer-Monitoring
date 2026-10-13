"""Load and validate configuration before opening any network resources."""

from copy import deepcopy
from math import isfinite
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import toml

DEFAULTS = {
    "app": {
        "host": "127.0.0.1",
        "port": 9999,
        "metrics_host": "127.0.0.1",
        "metrics_port": 9998,
    },
    "wireguard": {"interface": "wg0"},
    "redis": {
        "host": "localhost",
        "port": 6379,
        "db": 3,
        "username": "default",
        "password": "",
        "socket_timeout": 2.0,
    },
    "manager": {
        "url": "",
        "timeout": 5.0,
        "retries": 3,
        "retry_delay": 0.5,
        "queue_size": 1000,
        "shutdown_timeout": 10.0,
    },
}


class ConfigError(ValueError):
    """An unreadable or invalid configuration file."""


class ConfigManager:
    """TOML configuration with defaults and actionable validation errors."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.config = deepcopy(DEFAULTS)

    def load(self) -> None:
        """Load a complete configuration; retain the old one if validation fails."""
        try:
            with self.file_path.open(encoding="utf-8") as source:
                values = toml.load(source)
        except (OSError, ValueError) as exc:
            raise ConfigError(f"Cannot read configuration: {self.file_path}") from exc
        candidate = deepcopy(DEFAULTS)
        for group, fields in values.items():
            if group not in candidate or not isinstance(fields, dict):
                raise ConfigError(f"Unknown or invalid configuration section: {group}")
            for key, value in fields.items():
                if key not in candidate[group]:
                    raise ConfigError(f"Unknown configuration option: {group}.{key}")
                candidate[group][key] = value
        self._validate(candidate)
        self.config = candidate

    @classmethod
    def _validate(cls, values: dict) -> None:
        for group, fields in values.items():
            for key, value in fields.items():
                cls._validate_value(group, key, value)
        for group, key in (
            ("app", "host"),
            ("app", "metrics_host"),
            ("redis", "host"),
        ):
            if not values[group][key].strip():
                raise ConfigError(f"{group}.{key} must not be empty")
        interface = values["wireguard"]["interface"]
        if (
            not interface
            or len(interface.encode()) > 15
            or any(char.isspace() or char in "/:" for char in interface)
        ):
            raise ConfigError(
                "wireguard.interface must be a valid Linux interface name"
            )
        url = values["manager"]["url"]
        if url:
            try:
                parsed = urlsplit(url)
                valid = parsed.scheme in {"http", "https"} and parsed.hostname
                valid = valid and not parsed.fragment and parsed.port != 0
            except ValueError as exc:
                raise ConfigError(
                    "manager.url must be an HTTP(S) URL or empty"
                ) from exc
            if not valid:
                raise ConfigError("manager.url must be an HTTP(S) URL or empty")

    @staticmethod
    def _validate_value(group: str, key: str, value: Any) -> None:
        default = DEFAULTS[group][key]
        name = f"{group}.{key}"
        if isinstance(default, str):
            if not isinstance(value, str):
                raise ConfigError(f"{name} must be a string")
        elif isinstance(default, int):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ConfigError(f"{name} must be an integer")
            minimum = 0 if key in {"db", "retries"} else 1
            if value < minimum or (key.endswith("port") and value > 65535):
                raise ConfigError(f"{name} is out of range")
        elif (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not isfinite(value)
            or value <= 0
        ):
            raise ConfigError(f"{name} must be a finite positive number")

    def get(self, group: str, key: str) -> Any:
        """Return an option, or None for an unknown option."""
        return self.config.get(group, {}).get(key)
