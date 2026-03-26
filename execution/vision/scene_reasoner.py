class SceneReasoner:

    def describe_scene(self, detections):

        if not detections:
            return "I cannot see anything clearly."

        objects = [d["name"] for d in detections]

        unique = list(set(objects))

        if len(unique) == 1:
            return f"I see a {unique[0]}."

        joined = ", ".join(unique[:5])

        return f"I can see {joined}."
