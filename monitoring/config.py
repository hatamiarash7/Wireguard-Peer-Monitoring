import sys

import toml
from loguru import logger as log
from toml import TomlDecodeError


class ConfigManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.config = None

    def load(self):
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

    def get(self, group, key):
        return self.config.get(group, {}).get(key)
