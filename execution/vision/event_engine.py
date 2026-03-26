import time
import math


class EventEngine:

    def __init__(self,
                 cooldown=3.5,
                 motion_threshold=80):

        self.cooldown = cooldown
        self.motion_threshold = motion_threshold

        # 🔥 Only narrate important objects
        self.priority_objects = {
            "person",
            "phone",
            "cell phone",
            "chair",
            "door",
            "laptop"
        }

        # ✅ Per-object cooldown tracking
        self._object_last_spoken = {}

    # =====================================================

    def process_events(self, events, frame_width=None):

        current_time = time.time()

        if not events:
            return None

        for event in events:

            obj = event["object"]
            label = obj["label"]
            event_type = event["type"]
            obj_id = obj["id"]

            # 🔴 Ignore non-priority objects
            if label not in self.priority_objects:
                continue

            # ✅ Per-object cooldown
            last_time = self._object_last_spoken.get(obj_id, 0)

            if current_time - last_time < self.cooldown:
                continue

            # -------------------------------------------------
            # ENTRY
            # -------------------------------------------------

            if event_type == "ENTRY":

                message = self._format_with_position(
                    f"A {label} entered the scene.",
                    obj,
                    frame_width
                )

            # -------------------------------------------------
            # EXIT
            # -------------------------------------------------

            elif event_type == "EXIT":

                message = f"The {label} left the scene."

            # -------------------------------------------------
            # MOTION (only strong movement)
            # -------------------------------------------------

            elif event_type == "MOTION":

                vx, vy = obj["velocity"]
                motion = math.sqrt(vx ** 2 + vy ** 2)

                if motion < self.motion_threshold:
                    continue

                message = self._format_with_position(
                    f"The {label} moved significantly.",
                    obj,
                    frame_width
                )

            else:
                continue

            # ✅ Save last spoken time per object
            self._object_last_spoken[obj_id] = current_time

            return message

        return None

    # =====================================================

    def _format_with_position(self, base_message, obj, frame_width):

        if not frame_width:
            return base_message

        x1, _, x2, _ = obj["bbox"]
        center_x = (x1 + x2) / 2

        zone = self._get_zone(center_x, frame_width)

        return f"{base_message} It is on your {zone}."

    # =====================================================

    def _get_zone(self, x, width):

        third = width / 3

        if x < third:
            return "left"
        elif x < 2 * third:
            return "center"
        else:
            return "right"