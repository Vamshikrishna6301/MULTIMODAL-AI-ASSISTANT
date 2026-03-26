import time


class SceneMemory:

    def __init__(self,
                 disappearance_time=3.0,
                 motion_threshold=25,
                 min_presence_frames=4):

        self.disappearance_time = disappearance_time
        self.motion_threshold = motion_threshold
        self.min_presence_frames = min_presence_frames

        self._active_objects = {}
        self._presence_counter = {}
        self._last_events = []

    # =====================================================

    def update(self, tracked_objects):

        current_time = time.time()
        events = []

        current_ids = set()

        for obj in tracked_objects:

            obj_id = obj["id"]
            current_ids.add(obj_id)

            # Count presence frames
            if obj_id not in self._presence_counter:
                self._presence_counter[obj_id] = 1
            else:
                self._presence_counter[obj_id] += 1

            # New object detected
            if obj_id not in self._active_objects:

                # Only trigger ENTRY if stable for N frames
                if self._presence_counter[obj_id] >= self.min_presence_frames:
                    events.append({
                        "type": "ENTRY",
                        "object": obj
                    })
                    self._active_objects[obj_id] = obj

            else:
                # Check motion
                vx, vy = obj["velocity"]
                motion_magnitude = (vx ** 2 + vy ** 2) ** 0.5

                if motion_magnitude > self.motion_threshold:
                    events.append({
                        "type": "MOTION",
                        "object": obj
                    })

                self._active_objects[obj_id] = obj

        # Detect EXIT
        for obj_id in list(self._active_objects.keys()):
            if obj_id not in current_ids:
                last_seen = self._active_objects[obj_id]["last_seen"]

                if current_time - last_seen > self.disappearance_time:
                    events.append({
                        "type": "EXIT",
                        "object": self._active_objects[obj_id]
                    })

                    del self._active_objects[obj_id]
                    self._presence_counter.pop(obj_id, None)

        self._last_events = events
        return events