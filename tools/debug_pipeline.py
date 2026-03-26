import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time
import traceback
from infrastructure.logger import get_logger

logger = get_logger("debug.navigation_runtime")


class NavigationRuntimeDebugger:
    """
    Tracks repeated navigation execution and TTS loops.
    """

    def __init__(self):
        self.last_message = None
        self.last_time = 0
        self.repeat_count = 0

    def log_tts(self, message):

        now = time.time()

        if message == self.last_message:
            self.repeat_count += 1
        else:
            self.repeat_count = 0

        self.last_message = message
        self.last_time = now

        logger.debug(
            "TTS_EVENT",
            message=message,
            repeat_count=self.repeat_count,
            timestamp=now
        )

        if self.repeat_count > 5:
            logger.error(
                "TTS_LOOP_DETECTED",
                message=message,
                repeat_count=self.repeat_count
            )

    def log_navigation_call(self, action):

        logger.debug(
            "NAVIGATION_CALL",
            action=action,
            timestamp=time.time(),
            stack="".join(traceback.format_stack(limit=6))
        )