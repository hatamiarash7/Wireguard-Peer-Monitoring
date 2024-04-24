"""Top-level package"""

import importlib.metadata
import sys

from loguru import logger as log

from monitoring import config, utils

__app_name__ = "wireguard-peer-monitoring"
__description__ = "Monitor Wireguard peers using kernel events."
__version__ = importlib.metadata.version(__app_name__)
__author__ = "Arash Hatami <info@arash-hatami.ir>"
__epilog__ = "Made with :heart:  in [green]Iran[/green]"

# Configure Logging
log.remove(0)
log.add(
    sink=sys.stdout,
    level=utils.get_env("LOG_LEVEL", "INFO"),
    colorize=True if utils.get_env("ENV", "local") == "local" else False,
    format=utils.log_formatter,
)

CONFIG = config.ConfigManager(utils.get_env("CONFIG_FILE", "/app/config.toml"))
CONFIG.load()
