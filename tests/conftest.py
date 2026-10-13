"""Isolated dependencies: no real network or user configuration is needed."""

from unittest.mock import Mock

import fakeredis
import pytest

from monitoring.config import ConfigManager
from monitoring.prom import Metrics
from monitoring.redis_handler import Redis


@pytest.fixture
def config(tmp_path):
    return ConfigManager(tmp_path / "config.toml")


@pytest.fixture
def metrics():
    return Metrics()


@pytest.fixture
def notifier():
    return Mock()


@pytest.fixture
def store(config, notifier, metrics, monkeypatch):
    client = fakeredis.FakeRedis()
    monkeypatch.setattr("monitoring.redis_handler.redis.Redis", lambda **_: client)
    result = Redis(config, notifier, metrics)
    yield result
    result.close()
