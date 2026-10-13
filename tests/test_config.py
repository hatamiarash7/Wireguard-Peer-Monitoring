"""Configuration validation and atomic reload tests."""

import pytest
import toml

from monitoring.config import ConfigError


def test_defaults_and_overrides(config):
    config.file_path.write_text('[wireguard]\ninterface = "wg.test"\n')
    config.load()
    assert config.get("wireguard", "interface") == "wg.test"
    assert config.get("app", "port") == 9999
    assert config.get("missing", "key") is None


@pytest.mark.parametrize(
    "content", [None, "[broken", "app = 1", "[unknown]", "[app]\nwat = 1"]
)
def test_invalid_files(config, content):
    if content is not None:
        config.file_path.write_text(content)
    with pytest.raises(ConfigError):
        config.load()


@pytest.mark.parametrize(
    "group,key,value",
    [
        ("app", "port", True),
        ("app", "port", "9999"),
        ("app", "port", 0),
        ("app", "port", 65536),
        ("app", "host", 12),
        ("app", "host", " "),
        ("redis", "db", -1),
        ("redis", "socket_timeout", 0),
        ("redis", "socket_timeout", "fast"),
        ("redis", "socket_timeout", True),
        ("manager", "timeout", float("inf")),
        ("manager", "timeout", float("nan")),
        ("manager", "queue_size", 0),
        ("manager", "retries", -1),
        ("wireguard", "interface", ""),
        ("wireguard", "interface", "a" * 16),
        ("wireguard", "interface", "wg 0"),
        ("wireguard", "interface", "wg:0"),
        ("wireguard", "interface", "wg/0"),
        ("manager", "url", "ftp://host"),
        ("manager", "url", "https://"),
        ("manager", "url", "https://[bad"),
        ("manager", "url", "https://host:bad"),
        ("manager", "url", "https://host:0"),
        ("manager", "url", "https://host/#fragment"),
    ],
)
def test_invalid_options_preserve_previous_config(config, group, key, value):
    before = config.config
    config.file_path.write_text(toml.dumps({group: {key: value}}))
    with pytest.raises(ConfigError):
        config.load()
    assert config.config is before


@pytest.mark.parametrize(
    "url", ["", "https://example.test/hook", "http://[::1]:8000/hook"]
)
def test_valid_webhook_urls(config, url):
    config.file_path.write_text(toml.dumps({"manager": {"url": url}}))
    config.load()
    assert config.get("manager", "url") == url
