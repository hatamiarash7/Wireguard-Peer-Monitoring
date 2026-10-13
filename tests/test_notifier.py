"""Bounded retries, worker resilience, and shutdown regressions."""

import threading
from unittest.mock import Mock

import httpx
import pytest

from monitoring.notifier import JobManager

JOB = {"url": "https://example.test/hook", "payload": {"peer": "192.0.2.1:1234"}}


def outcome(metrics, result):
    return metrics.registry.get_sample_value(
        "wg_peer_monitoring_notifications_total", {"result": result}
    )


@pytest.fixture
def manager(config, metrics):
    config.config["manager"].update(retry_delay=0.001, timeout=0.1, shutdown_timeout=1)
    instance = JobManager(config, metrics)
    yield instance
    instance.stop()


@pytest.mark.parametrize(
    "statuses,attempts,result",
    [
        ([200], 1, "delivered"),
        ([503, 200], 2, "delivered"),
        ([429, 200], 2, "delivered"),
        ([408, 200], 2, "delivered"),
        ([400], 1, "failed"),
        ([401], 1, "failed"),
        ([302], 1, "failed"),
        ([503, 503, 503, 503], 4, "failed"),
    ],
)
def test_http_retry_policy(manager, metrics, statuses, attempts, result):
    calls = []

    def transport(request):
        calls.append(request)
        return httpx.Response(statuses[len(calls) - 1])

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        manager.process_job(client, JOB)
    assert len(calls) == attempts
    assert outcome(metrics, result) == 1


def test_network_failure_has_finite_retries(manager, metrics):
    client = Mock()
    client.post.side_effect = httpx.ConnectError("offline")
    manager.process_job(client, JOB)
    assert client.post.call_count == 4
    assert outcome(metrics, "failed") == 1


def test_success_after_connection_failure_stops_retrying(manager, metrics):
    client = Mock()
    client.post.side_effect = [httpx.ConnectError("offline"), Mock()]
    manager.process_job(client, JOB)
    assert client.post.call_count == 2
    assert outcome(metrics, "delivered") == 1


def test_queue_overflow_never_blocks(config, metrics):
    config.config["manager"]["queue_size"] = 1
    manager = JobManager(config, metrics)
    assert manager.add_job(JOB)
    assert not manager.add_job(JOB)
    manager.stop()
    manager.stop()
    assert manager.job_queue.unfinished_tasks == 0
    assert not manager.add_job(JOB)
    assert outcome(metrics, "dropped") == 3


def test_worker_survives_bad_job_and_stops(manager, metrics, monkeypatch):
    completed = threading.Event()

    def post(*_, **__):
        completed.set()
        return Mock()

    client = Mock()
    client.post.side_effect = post
    monkeypatch.setattr("monitoring.notifier.httpx.Client", Mock(return_value=client))
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock()
    manager.add_job({})
    manager.add_job(JOB)
    manager.start()
    manager.start()
    assert completed.wait(2)
    manager.stop()
    assert not manager._thread.is_alive()
    assert manager.job_queue.unfinished_tasks == 0
    assert outcome(metrics, "failed") == 1
    assert outcome(metrics, "delivered") == 1


def test_shutdown_interrupts_retry_backoff(manager, metrics):
    manager.settings["retry_delay"] = 30
    attempted = threading.Event()
    client = Mock()

    def fail(*_, **__):
        attempted.set()
        raise httpx.ConnectError("offline")

    client.post.side_effect = fail
    thread = threading.Thread(target=manager.process_job, args=(client, JOB))
    thread.start()
    assert attempted.wait(2)
    manager.stop()
    thread.join(1)
    assert not thread.is_alive()
    assert client.post.call_count == 1
    assert outcome(metrics, "dropped") == 1


def test_stop_before_start(manager, metrics):
    manager.stop()
    manager.start()
    client = Mock()
    manager.process_job(client, JOB)
    client.post.assert_not_called()
    assert manager._thread is None
    assert outcome(metrics, "dropped") == 1


def test_shutdown_deadline(manager):
    manager._thread = Mock()
    manager._thread.is_alive.return_value = True
    manager.stop()
    manager._thread.join.assert_called_once_with(timeout=1)
