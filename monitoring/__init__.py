"""Top-level package"""

import importlib.metadata
import sys
from pathlib import Path
from typing import Any

import toml
from loguru import logger as log

from monitoring import config, notifier, redis_handler, utils

__package_version = "unknown"  # pylint: disable=C0103


def __get_package_version() -> str:
    """Find the version of this package."""
    global __package_version

    if __package_version != "unknown":
        # We already set it at some point in the past,
        # so return that previous value without any
        # extra work.
        return __package_version

    try:
        # Try to get the version of the current package if
        # it is running from a distribution.
        __package_version = importlib.metadata.version("my_package_name")
    except importlib.metadata.PackageNotFoundError:
        # Fall back on getting it from a local pyproject.toml.
        # This works in a development environment where the
        # package has not been installed from a distribution.

        pyproject_toml_file = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_toml_file.exists() and pyproject_toml_file.is_file():
            __package_version = toml.load(pyproject_toml_file)["tool"]["poetry"][
                "version"
            ]

    return __package_version


def __getattr__(name: str) -> Any:
    """Get package attributes."""
    if name in ("version", "__version__"):
        return __get_package_version()

    raise AttributeError(f"No attribute {name} in module {__name__}.")


__app_name__ = "wireguard-peer-monitoring"
__description__ = "Monitor Wireguard peers using kernel events."
__version__ = f"v{__get_package_version()}"
__author__ = "Arash Hatami <info@arash-hatami.ir>"
__epilog__ = "Made with :heart:  in [green]Iran[/green]"


# Configure Logging
log.remove(0)
log.add(
    sink=sys.stdout,
    level=utils.get_env("LOG_LEVEL", "INFO"),
    colorize=utils.get_env("ENV", "local") == "local",
    format=utils.log_formatter,
)

# Configure config manager
CONFIG = config.ConfigManager(utils.get_env("CONFIG_FILE", "/app/config.toml"))
CONFIG.load()

# Configure job manager
NOTIFIER = notifier.JobManager()
NOTIFIER.start()

# Configure Redis
REDIS = redis_handler.Redis(
    config=CONFIG,
    notifier=NOTIFIER,
    host=CONFIG.get("redis", "host"),
    port=CONFIG.get("redis", "port"),
    db=CONFIG.get("redis", "db"),
    username=CONFIG.get("redis", "username"),
    password=CONFIG.get("redis", "password"),
)
