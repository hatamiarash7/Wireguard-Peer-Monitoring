"""Top-level package"""

import importlib.metadata
import sys

from loguru import logger as log

from monitoring import config, notifier, redis_handler, utils

__app_name__ = "wireguard-peer-monitoring"
__description__ = "Monitor Wireguard peers using kernel events."
__version__ = f"v{importlib.metadata.version(__app_name__)}"
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
