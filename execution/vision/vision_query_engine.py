from core.response_model import UnifiedResponse


class VisionQueryEngine:

    def __init__(self, camera_detector):
        self.camera_detector = camera_detector

    # =====================================================

    def handle(self, decision):

        query_type = decision.get("parameters", {}).get("query_type")
        target = decision.get("target")

        tracked_objects = self.camera_detector.get_tracked_objects()

        if not tracked_objects:
            return UnifiedResponse.success_response(
                category="vision",
                spoken_message="I do not see anything right now."
            )

        # --------------------------------------------------
        # LOCATION QUERY
        # --------------------------------------------------

        if query_type == "location":

            for obj in tracked_objects:
                if obj["label"] == target:
                    zone = self._get_zone(obj)
                    return UnifiedResponse.success_response(
                        category="vision",
                        spoken_message=f"Your {target} is on your {zone}."
                    )

            return UnifiedResponse.success_response(
                category="vision",
                spoken_message=f"I cannot see your {target} right now."
            )

        # --------------------------------------------------
        # COUNT QUERY
        # --------------------------------------------------

# --------------------------------------------------
# COUNT QUERY
# --------------------------------------------------


        if query_type == "presence":

            for obj in tracked_objects:
                if obj["label"] == "person":
                    return UnifiedResponse.success_response(
                        category="vision",
                        spoken_message="Yes, there is someone in the room."
                    )

            return UnifiedResponse.success_response(
                category="vision",
                spoken_message="No, I do not see anyone."
            )

        # --------------------------------------------------
        # SUMMARY QUERY
        # --------------------------------------------------

        if query_type == "summary":

            labels = [obj["label"] for obj in tracked_objects]
            unique = list(set(labels))

            summary = ", ".join(unique)

            return UnifiedResponse.success_response(
                category="vision",
                spoken_message=f"I can see {summary}."
            )

        return UnifiedResponse.success_response(
            category="vision",
            spoken_message="I am not sure how to answer that."
        )

    # =====================================================

    def _get_zone(self, obj):

        x1, _, x2, _ = obj["bbox"]
        center_x = (x1 + x2) / 2

        frame_width = 1280  # assume default

        third = frame_width / 3

        if center_x < third:
            return "left"
        elif center_x < 2 * third:
            return "center"
        else:
            return "right"