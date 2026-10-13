"""WireGuard peer monitoring. Importing this package never starts services."""

import os
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import toml

__app_name__ = "wireguard-peer-monitoring"


@lru_cache(maxsize=1)
def get_version() -> str:
    """Read installed metadata, falling back to the source checkout."""
    if release := os.getenv("APP_VERSION"):
        return release
    try:
        return version(__app_name__)
    except PackageNotFoundError:
        path = Path(__file__).resolve().parent.parent / "pyproject.toml"
        if path.is_file():
            return toml.load(path)["project"]["version"]
        return "unknown"


__version__ = get_version()
