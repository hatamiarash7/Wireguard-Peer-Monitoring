"""Bounded, best-effort webhook delivery on a single background worker."""

import queue
import threading

import httpx
from loguru import logger as log

from monitoring.config import ConfigManager
from monitoring.prom import Metrics


class JobManager:
    """Reuse HTTP connections, retry transient failures, and bound shutdown time."""

    def __init__(self, config: ConfigManager, metrics: Metrics):
        self.settings = config.config["manager"]
        self.metrics = metrics
        self.job_queue = queue.Queue(maxsize=self.settings["queue_size"])
        self._stopped = threading.Event()
        self._lock = threading.Lock()
        self._thread = None

    def add_job(self, job_data: dict) -> bool:
        """Enqueue without blocking UDP ingestion; report overflow and shutdown drops."""
        with self._lock:
            if not self._stopped.is_set():
                try:
                    self.job_queue.put_nowait(job_data)
                    return True
                except queue.Full:
                    pass
        self.metrics.notifications.labels("dropped").inc()
        log.warning("[NOTIFIER] Queue full or stopping; notification dropped")
        return False

    def process_job(self, client: httpx.Client, job_data: dict) -> None:
        """Try once plus configured retries; never retry permanent HTTP failures."""
        for attempt in range(self.settings["retries"] + 1):
            if self._stopped.is_set():
                self.metrics.notifications.labels("dropped").inc()
                return
            try:
                response = client.post(job_data["url"], json=job_data["payload"])
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if (
                    exc.response.status_code not in {408, 429}
                    and exc.response.status_code < 500
                ):
                    break
            except httpx.RequestError:
                pass
            else:
                self.metrics.notifications.labels("delivered").inc()
                return
            if attempt < self.settings["retries"]:
                self._stopped.wait(
                    min(self.settings["retry_delay"] * 2 ** min(attempt, 6), 30)
                )
        self.metrics.notifications.labels("failed").inc()
        log.warning("[NOTIFIER] Webhook delivery failed")

    def worker(self) -> None:
        """Always account for dequeued tasks, even when an unexpected job fails."""
        with httpx.Client(timeout=self.settings["timeout"]) as client:
            while not self._stopped.is_set():
                try:
                    job = self.job_queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                try:
                    self.process_job(client, job)
                except Exception:  # pylint: disable=broad-exception-caught
                    # One bad job must not terminate the delivery worker.
                    self.metrics.notifications.labels("failed").inc()
                    log.error("[NOTIFIER] Invalid job or unexpected delivery failure")
                finally:
                    self.job_queue.task_done()

    def start(self) -> None:
        """Start once; repeated calls are harmless."""
        with self._lock:
            if self._thread is None and not self._stopped.is_set():
                self._thread = threading.Thread(
                    target=self.worker, name="webhooks", daemon=True
                )
                self._thread.start()

    def stop(self) -> None:
        """Cancel retries and queued jobs; allow an in-flight request time to finish."""
        with self._lock:
            self._stopped.set()
        if self._thread is not None:
            self._thread.join(timeout=self.settings["shutdown_timeout"])
            if self._thread.is_alive():
                log.warning(
                    "[NOTIFIER] Shutdown deadline reached with a request in flight"
                )
        while True:
            try:
                self.job_queue.get_nowait()
            except queue.Empty:
                break
            self.metrics.notifications.labels("dropped").inc()
            self.job_queue.task_done()
