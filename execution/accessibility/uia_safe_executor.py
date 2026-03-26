from __future__ import annotations

import atexit
from concurrent.futures import ThreadPoolExecutor, TimeoutError


class UIASafeExecutor:

    MAX_WORKERS = 1
    TIMEOUT = 0.35

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)

    def run(self, func, *args, **kwargs):
        future = self.executor.submit(func, *args, **kwargs)

        try:
            return future.result(timeout=self.TIMEOUT)
        except TimeoutError:
            future.cancel()
            return None
        except Exception:
            return None

    def shutdown(self):
        self.executor.shutdown(wait=False, cancel_futures=True)


uia_safe_executor = UIASafeExecutor()
atexit.register(uia_safe_executor.shutdown)
