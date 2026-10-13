"""Environment and logging helpers."""

import os
import sys

from loguru import logger as log


def log_formatter(record: dict) -> str:
    """Include structured fields and exception information when available."""
    extra = " | {extra}" if record.get("extra") else ""
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> - <level>{level}: {message}"
        + extra
        + "</level>\n{exception}"
    )


def get_env(key: str, default: str | None = None) -> str:
    """Read an environment variable, accepting an explicitly empty default."""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable {key} not defined")
    return value


def configure_logging() -> None:
    """Configure logging only at application startup."""
    log.remove()
    log.add(
        sys.stdout,
        level=get_env("LOG_LEVEL", "INFO").upper(),
        colorize=get_env("ENV", "local") == "local",
        format=log_formatter,
        backtrace=False,
        diagnose=False,
    )
