import queue
import threading

import httpx
from loguru import logger as log


class JobManager:
    def __init__(self):
        self.job_queue = queue.Queue()
        self.is_running = False

    def add_job(self, job_data):
        self.job_queue.put(job_data)

    def process_job(self, job_data):
        webhook_url = job_data["webhook_url"]
        payload = job_data["payload"]

        try:
            response = httpx.post(webhook_url, json=payload)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        except httpx.RequestError as e:
            log.error(f"[NOTIFIER] Call failed for job: {job_data}", Error=e)
            self.retry_job(job_data)

    def retry_job(self, job_data):
        retry_limit = 3
        retry_count = 0
        while retry_count < retry_limit:
            log.info(f"[NOTIFIER] Retrying job {job_data}", Attempt=(retry_count + 1))
            self.process_job(job_data)
            retry_count += 1

    def worker(self):
        while self.is_running:
            try:
                # Timeout to prevent blocking indefinitely
                job_data = self.job_queue.get(timeout=1)
                self.process_job(job_data)
                self.job_queue.task_done()
            except queue.Empty:
                pass

    def start(self):
        if not self.is_running:
            log.info("[NOTIFIER] Start Job Manager")
            self.is_running = True
            threading.Thread(target=self.worker, daemon=True).start()

    def stop(self):
        log.info("[NOTIFIER] Stop Job Manager")
        self.is_running = False
        self.job_queue.join()  # Wait until all jobs are processed
