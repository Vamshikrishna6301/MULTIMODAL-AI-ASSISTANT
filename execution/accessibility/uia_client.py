from __future__ import annotations

import atexit
import multiprocessing as mp
import queue
import threading
import time

from execution.accessibility.uia_worker_process import worker_main


class UIAClient:

    def __init__(self):
        self._lock = threading.RLock()
        self._process = None
        self._input_queue = None
        self._output_queue = None
        self._request_id = 0

    def start_worker(self):
        with self._lock:
            if self._process is not None and self._process.is_alive():
                return
            ctx = mp.get_context("spawn")
            self._input_queue = ctx.Queue()
            self._output_queue = ctx.Queue()
            self._process = ctx.Process(
                target=worker_main,
                args=(self._input_queue, self._output_queue),
                daemon=True,
            )
            self._process.start()

    def stop_worker(self):
        with self._lock:
            process = self._process
            input_queue = self._input_queue
            output_queue = self._output_queue
            self._process = None
            self._input_queue = None
            self._output_queue = None

        if process is None:
            return

        try:
            if input_queue is not None:
                input_queue.put_nowait({"id": -1, "cmd": "__stop__"})
        except Exception:
            pass

        try:
            process.join(timeout=0.5)
        except Exception:
            pass

        if process.is_alive():
            try:
                process.terminate()
                process.join(timeout=0.5)
            except Exception:
                pass

        for q in (input_queue, output_queue):
            if q is None:
                continue
            try:
                q.close()
            except Exception:
                pass

    def call(self, cmd, timeout=0.5, **params):
        with self._lock:
            self.start_worker()
            self._request_id += 1
            request_id = self._request_id
            input_queue = self._input_queue
            output_queue = self._output_queue

            if input_queue is None or output_queue is None:
                return None

            try:
                input_queue.put({"id": request_id, "cmd": cmd, "params": params}, timeout=0.1)
            except Exception:
                self.stop_worker()
                self.start_worker()
                return None

            deadline = time.monotonic() + max(0.1, timeout)
            while time.monotonic() < deadline:
                remaining = max(0.05, deadline - time.monotonic())
                try:
                    response = output_queue.get(timeout=remaining)
                except queue.Empty:
                    continue
                except Exception:
                    break
                if not isinstance(response, dict):
                    continue
                if response.get("id") == request_id:
                    return response.get("result")

            self.stop_worker()
            self.start_worker()
            return None


uia_client = UIAClient()
atexit.register(uia_client.stop_worker)
