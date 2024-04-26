"""Config manager"""

import sys
from typing import Any

import toml
from loguru import logger as log
from toml import TomlDecodeError


class ConfigManager:
    """This class is responsible for loading and getting config values."""

    def __init__(self, file_path):
        self.file_path = file_path
        self.config = None

    def load(self) -> None:
        """Load config.toml file"""

        try:
            log.debug(f"[CONFIG] Loading config from `{self.file_path}`")
            with open(
                file=self.file_path,
                mode="r",
                encoding="UTF-8",
            ) as f:
                self.config = toml.load(f)
        except FileNotFoundError:
            log.error(f"[CONFIG] File `{self.file_path}` not found.")
            sys.exit(1)
        except (TypeError, TomlDecodeError):
            log.error(f"[CONFIG] File `{self.file_path}` has problem.")
            sys.exit(1)

    def get(self, group: str, key: str) -> Any:
        """This function returns the value of the key in the group.

        Args:
            group (str): TOML's group name
            key (str): TOML's key

        Returns:
            Any: The value of the key
        """

        return self.config.get(group, {}).get(key)
