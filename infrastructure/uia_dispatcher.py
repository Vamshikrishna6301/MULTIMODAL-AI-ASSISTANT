import queue
import threading


class UIADispatcher:

    def __init__(self):
        self.queue = queue.Queue()
        self._ready = threading.Event()
        self._thread_id = None
        self.thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="UIADispatcher",
        )
        self.thread.start()
        self._ready.wait()

    def call(self, func, *args, **kwargs):
        if threading.get_ident() == self._thread_id:
            return func(*args, **kwargs)

        result_queue = queue.Queue(maxsize=1)
        self.queue.put((func, args, kwargs, result_queue))
        result = result_queue.get()

        if isinstance(result, Exception):
            raise result

        return result

    def _run(self):
        import pythoncom

        pythoncom.CoInitialize()
        self._thread_id = threading.get_ident()
        self._ready.set()

        try:
            while True:
                func, args, kwargs, result_queue = self.queue.get()

                try:
                    result = func(*args, **kwargs)
                    result_queue.put(result)
                except Exception as exc:
                    result_queue.put(exc)
        finally:
            pythoncom.CoUninitialize()


dispatcher = UIADispatcher()
