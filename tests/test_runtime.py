"""Startup failures, datagram isolation, and cleanup paths."""

import importlib
import runpy
import signal
import socket
import threading
from unittest.mock import MagicMock, Mock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from monitoring import main


def test_receive_continues_after_bad_encoding_and_redis_outage(metrics):
    stopped = threading.Event()
    udp_socket = Mock()
    udp_socket.recvfrom.side_effect = [
        socket.timeout,
        (b"\xff", None),
        (b"first", None),
        (b"second", None),
    ]
    handler = Mock(metrics=metrics)

    def parse(data):
        if data == "first":
            raise RedisConnectionError
        stopped.set()

    handler.parse.side_effect = parse
    main.receive(udp_socket, handler, stopped)
    assert handler.parse.call_count == 2
    assert (
        metrics.registry.get_sample_value(
            "wg_peer_monitoring_errors_total", {"reason": "encoding"}
        )
        == 1
    )
    assert (
        metrics.registry.get_sample_value(
            "wg_peer_monitoring_errors_total", {"reason": "redis"}
        )
        == 1
    )
    udp_socket.recvfrom.assert_called_with(65535)


@pytest.fixture
def resources(monkeypatch):
    store, notifier, udp_socket, server, thread = (MagicMock() for _ in range(5))
    udp_socket.__enter__.return_value = udp_socket
    monkeypatch.setattr(main, "Redis", Mock(return_value=store))
    monkeypatch.setattr(main, "JobManager", Mock(return_value=notifier))
    monkeypatch.setattr(main.socket, "socket", Mock(return_value=udp_socket))
    monkeypatch.setattr(main, "start_http_server", Mock(return_value=(server, thread)))
    monkeypatch.setattr(main, "receive", Mock())
    return store, notifier, udp_socket, server, thread


@pytest.mark.parametrize(
    "host,family", [("127.0.0.1", socket.AF_INET), ("::1", socket.AF_INET6)]
)
def test_runtime_releases_all_resources(config, resources, host, family):
    config.config["app"]["host"] = host
    store, notifier, udp_socket, server, thread = resources
    main.run(config, threading.Event())
    main.socket.socket.assert_called_once_with(family, socket.SOCK_DGRAM)
    udp_socket.bind.assert_called_once_with((host, 9999))
    store.ping.assert_called_once()
    store.close.assert_called_once()
    notifier.start.assert_called_once()
    notifier.stop.assert_called_once()
    server.shutdown.assert_called_once()
    server.server_close.assert_called_once()
    thread.join.assert_called_once()
    udp_socket.__exit__.assert_called_once()


@pytest.mark.parametrize("failure", ["redis", "bind", "metrics", "receive"])
def test_partial_startup_failure_cleans_up(config, resources, failure):
    store, notifier, udp_socket, server, _ = resources
    operations = {
        "redis": store.ping,
        "bind": udp_socket.bind,
        "metrics": main.start_http_server,
        "receive": main.receive,
    }
    operations[failure].side_effect = OSError("test failure")
    with pytest.raises(OSError):
        main.run(config, threading.Event())
    store.close.assert_called_once()
    if failure != "redis":
        notifier.stop.assert_called_once()
    if failure == "receive":
        server.shutdown.assert_called_once()


def test_main_installs_signals_and_restores_them(config, monkeypatch):
    config.file_path.write_text("")
    monkeypatch.setenv("CONFIG_FILE", str(config.file_path))
    monkeypatch.setattr(main, "configure_logging", Mock())
    installed = {}

    def install(sig, callback):
        installed[sig] = callback
        return signal.SIG_DFL

    monkeypatch.setattr(main.signal, "signal", install)

    def run(_, stopped):
        installed[signal.SIGTERM](signal.SIGTERM, None)
        assert stopped.is_set()

    monkeypatch.setattr(main, "run", run)
    assert main.main() == 0
    assert all(callback == signal.SIG_DFL for callback in installed.values())


def test_main_missing_configuration_returns_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFIG_FILE", str(tmp_path / "missing.toml"))
    monkeypatch.setattr(main, "configure_logging", Mock())
    assert main.main() == 1


def test_module_entrypoint(monkeypatch):
    monkeypatch.setattr(main, "main", lambda: 7)
    with pytest.raises(SystemExit) as result:
        runpy.run_module("monitoring", run_name="__main__")
    assert result.value.code == 7


def test_importing_entrypoint_does_not_start_service(monkeypatch):
    entrypoint = Mock()
    monkeypatch.setattr(main, "main", entrypoint)
    importlib.import_module("monitoring.__main__")
    entrypoint.assert_not_called()
