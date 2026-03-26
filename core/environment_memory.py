class EnvironmentMemory:

    def __init__(self):
        self.objects = {}

    def update_objects(self, detections):

        for obj in detections:
            name = self._normalize(obj["name"])
            self.objects[name] = obj

    def query(self, name):

        return self.objects.get(self._normalize(name))

    def _normalize(self, name):

        value = (name or "").strip().lower()
        for prefix in ("the ", "a ", "an "):
            if value.startswith(prefix):
                value = value[len(prefix):]
                break
        return value
