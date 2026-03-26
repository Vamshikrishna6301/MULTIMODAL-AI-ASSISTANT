import sounddevice as sd
import queue


class MicrophoneStream:

    def __init__(self):

        self.sample_rate = 16000
        self.frame_duration_ms = 30
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)

        self.q = queue.Queue(maxsize=50)

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.frame_size,
            callback=self._callback
        )

    def _callback(self, indata, frames, time_info, status):

        if status:
            print("Mic status:", status)

        try:
            self.q.put_nowait(indata.copy())
        except queue.Full:

            try:
                self.q.get_nowait()
            except queue.Empty:
                pass

            try:
                self.q.put_nowait(indata.copy())
            except queue.Full:
                pass

    def __enter__(self):

        self.stream.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        self.stream.stop()
        self.stream.close()

    def read(self):

        try:
            data = self.q.get(timeout=1)
            return data.tobytes()
        except queue.Empty:
            return b""

    def get_sample_rate(self):

        return self.sample_rate