"""Import isolation, release metadata, logging, and liveness probes."""

import importlib
import runpy
import subprocess
import sys
from unittest.mock import MagicMock, Mock

import pytest

import monitoring
from monitoring import healthcheck, utils


def test_imports_have_no_runtime_side_effects():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; os.environ['CONFIG_FILE']='/does/not/exist'; import monitoring.main; import threading; assert len(threading.enumerate()) == 1",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_version_resolution(monkeypatch, tmp_path):
    monitoring.get_version.cache_clear()
    monkeypatch.setenv("APP_VERSION", "v2.0.0")
    assert monitoring.get_version() == "v2.0.0"
    monitoring.get_version.cache_clear()
    monkeypatch.delenv("APP_VERSION")
    monkeypatch.setattr(monitoring, "version", lambda _: "1.2.3")
    assert monitoring.get_version() == "1.2.3"
    monitoring.get_version.cache_clear()
    monkeypatch.setattr(
        monitoring, "version", Mock(side_effect=monitoring.PackageNotFoundError)
    )
    monkeypatch.setattr(
        monitoring, "__file__", str(tmp_path / "monitoring" / "__init__.py")
    )
    assert monitoring.get_version() == "unknown"
    monitoring.get_version.cache_clear()
    (tmp_path / "pyproject.toml").write_text('[project]\nversion="4.5.6"')
    assert monitoring.get_version() == "4.5.6"
    monitoring.get_version.cache_clear()


def test_environment_defaults(monkeypatch):
    monkeypatch.delenv("TEST_MONITOR_OPTION", raising=False)
    assert utils.get_env("TEST_MONITOR_OPTION", "") == ""
    assert utils.get_env("TEST_MONITOR_OPTION", "default") == "default"
    with pytest.raises(ValueError, match="TEST_MONITOR_OPTION"):
        utils.get_env("TEST_MONITOR_OPTION")
    monkeypatch.setenv("TEST_MONITOR_OPTION", "value")
    assert utils.get_env("TEST_MONITOR_OPTION", "default") == "value"


def test_logging(monkeypatch):
    logger = Mock()
    monkeypatch.setattr(utils, "log", logger)
    monkeypatch.setenv("LOG_LEVEL", "debug")
    utils.configure_logging()
    logger.remove.assert_called_once()
    assert logger.add.call_args.kwargs["level"] == "DEBUG"
    assert "{extra}" in utils.log_formatter({"extra": {"peer": 1}})
    assert "{extra}" not in utils.log_formatter({})
    assert "{exception}" in utils.log_formatter({})


@pytest.mark.parametrize(
    "host,expected",
    [("0.0.0.0", "127.0.0.1"), ("::", "::1"), ("localhost", "localhost")],
)
def test_healthcheck_uses_configured_listener(config, monkeypatch, host, expected):
    config.file_path.write_text(f'[app]\nmetrics_host="{host}"\nmetrics_port=12345\n')
    monkeypatch.setenv("CONFIG_FILE", str(config.file_path))
    connect = MagicMock()
    monkeypatch.setattr(healthcheck.socket, "create_connection", connect)
    assert healthcheck.main() == 0
    connect.assert_called_once_with((expected, 12345), timeout=2)


def test_healthcheck_module(config, monkeypatch):
    config.file_path.write_text("")
    monkeypatch.setenv("CONFIG_FILE", str(config.file_path))
    monkeypatch.setattr(healthcheck.socket, "create_connection", MagicMock())
    # Run a fresh module, as the Docker HEALTHCHECK does.
    monkeypatch.delitem(sys.modules, "monitoring.healthcheck")
    with pytest.raises(SystemExit) as result:
        runpy.run_module("monitoring.healthcheck", run_name="__main__")
    assert result.value.code == 0
    importlib.import_module("monitoring.healthcheck")
