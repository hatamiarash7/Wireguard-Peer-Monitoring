"""Event-to-storage regression tests, including actual Lua execution."""

from datetime import datetime
from unittest.mock import Mock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from monitoring.handler import Handler
from monitoring.prom import Metrics


@pytest.mark.parametrize("peer", ["1", "12", "12345"])
@pytest.mark.parametrize(
    "message,event",
    [
        ("handshake initiation", "Handshake"),
        ("handshake response", "Handshake"),
        ("keepalive packet", "Keepalive"),
    ],
)
@pytest.mark.parametrize(
    "endpoint,ip",
    [
        ("192.0.2.1:51820", "192.0.2.1"),
        ("[2001:db8::1]:51820", "2001:db8::1"),
    ],
)
def test_event_persists_endpoint_and_timestamp(
    store, metrics, peer, message, event, endpoint, ip
):
    handler = Handler("wg0", store, metrics)
    assert handler.parse(
        f"<6>host kernel: wireguard: wg0: Receiving {message} from peer {peer} ({endpoint})\n"
    )
    saved = store.get_peer(peer)
    assert saved[b"ip"] == ip.encode()
    assert saved[b"port"] == b"51820"
    datetime.strptime(saved[event.lower().encode()].decode(), "%Y-%m-%d %H:%M:%S")
    assert (
        metrics.registry.get_sample_value(
            "wg_peer_monitoring_wg_wireguard_events_total",
            {"peer": peer, "event": event},
        )
        == 1
    )
    assert (
        metrics.registry.get_sample_value(
            "wg_peer_monitoring_wg_last_event_timestamp_seconds",
            {"peer": peer, "event": event},
        )
        > 0
    )


@pytest.mark.parametrize("prefix", ["otherwg0", "wg0.1", "wg00", "my-wg0", "wg1"])
def test_wrong_interface_is_ignored(store, metrics, prefix):
    assert not Handler("wg0", store, metrics).parse(
        f"{prefix}: Receiving keepalive packet from peer 12 (192.0.2.1:1234)"
    )
    assert store.get_peer("12") == {}


def test_interface_regex_is_literal(store, metrics):
    handler = Handler("wg.0", store, metrics)
    message = ": Receiving handshake initiation from peer 12 (192.0.2.1:1234)"
    assert not handler.parse("wgX0" + message)
    assert handler.parse("wg.0" + message)


@pytest.mark.parametrize(
    "message",
    [
        "unrelated",
        "Receiving handshake garbage from peer 12 (192.0.2.1:12)",
        "Receiving keepalive packet from peer x (192.0.2.1:12)",
        "Receiving keepalive packet from peer 12 (192.0.2.1:12) trailing",
        "Receiving keepalive packet from peer 12 (2001:db8::1:12)",
    ],
)
def test_unsupported_events_are_ignored(store, metrics, message):
    assert not Handler("wg0", store, metrics).parse("wg0: " + message)


@pytest.mark.parametrize(
    "endpoint",
    ["not-an-ip:12", "999.0.0.1:12", "[bad::ip]:12", "192.0.2.1:0", "192.0.2.1:65536"],
)
def test_invalid_endpoint_is_rejected(store, metrics, endpoint):
    assert not Handler("wg0", store, metrics).parse(
        f"wg0: Receiving keepalive packet from peer 12 ({endpoint})"
    )
    assert (
        metrics.registry.get_sample_value(
            "wg_peer_monitoring_errors_total", {"reason": "endpoint"}
        )
        == 1
    )


def test_changes_notified_only_after_persistence(store, config, notifier, metrics):
    config.config["manager"]["url"] = "https://example.test/hook"
    notifier.add_job.side_effect = lambda _: store.get_peer("12")[b"ip"]
    store.save_peer("12", "192.0.2.1", "51820")
    first = store.get_peer("12")[b"handshake"]
    store.save_peer("12", "192.0.2.1", "51820")
    assert notifier.add_job.call_count == 1
    store.save_keepalive("12", "192.0.2.2", "51821")
    assert notifier.add_job.call_count == 2
    assert notifier.add_job.call_args.args[0]["payload"] == {"peer": "192.0.2.2:51821"}
    assert store.get_peer("12")[b"handshake"] == first
    assert b"keepalive" in store.get_peer("12")
    assert (
        metrics.registry.get_sample_value(
            "wg_peer_monitoring_wg_peer_changes_total", {"peer": "12"}
        )
        == 2
    )


def test_ipv6_normalization_and_payload(store, config, notifier):
    config.config["manager"]["url"] = "https://example.test/hook"
    store.save_peer("12", "[2001:0db8::1]", "01234")
    store.save_keepalive("12", "[2001:db8::1]", "1234")
    notifier.add_job.assert_called_once_with(
        {"url": "https://example.test/hook", "payload": {"peer": "[2001:db8::1]:1234"}}
    )


def test_disabled_notifications_and_ping(store, notifier):
    store.ping()
    store.save_peer("12", "192.0.2.1", "1234")
    notifier.add_job.assert_not_called()


def test_storage_failure_does_not_notify_or_count_success(
    store, notifier, metrics, monkeypatch
):
    monkeypatch.setattr(store, "_update_peer", Mock(side_effect=RedisConnectionError))
    with pytest.raises(RedisConnectionError):
        Handler("wg0", store, metrics).parse(
            "wg0: Receiving keepalive packet from peer 12 (192.0.2.1:1234)"
        )
    notifier.add_job.assert_not_called()
    assert (
        metrics.registry.get_sample_value(
            "wg_peer_monitoring_wg_wireguard_events_total",
            {"peer": "12", "event": "Keepalive"},
        )
        is None
    )


def test_registries_are_independent():
    one, two = Metrics(), Metrics()
    one.errors.labels("redis").inc()
    assert (
        two.registry.get_sample_value(
            "wg_peer_monitoring_errors_total", {"reason": "redis"}
        )
        is None
    )
