"""Utility module"""

import os


def log_formatter(record: dict) -> str:
    """Format log based on record's extra

    Args:
        record (dict): Input record

    Returns:
        str: Format string for loguru
    """

    if len(record.get("extra")) > 0:
        return "<green>{time:YYYY-MM-D HH:mm:ss}</green> - <level>{level}:\t{message} | {extra}</level>\n"

    return "<green>{time:YYYY-MM-D HH:mm:ss}</green> - <level>{level}:\t{message}</level>\n"


def get_env(key: str, default: str = None) -> str:
    """Get environment variable

    Args:
        key (str): Environment variable name
        default (str, optional): Default value if not found. Defaults to None.

    Returns:
        str: Environment variable value
    """

    if key in os.environ:
        return os.environ[key]

    if default:
        return default

    # pylint: disable=W0719
    raise Exception(f"Environment variable {key} not defined")
