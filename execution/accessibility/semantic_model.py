class SemanticElement:

    def __init__(self, name, role, bbox=None, source="uia", confidence=1.0):
        self.name = name
        self.role = role
        self.bbox = bbox
        self.source = source
        self.confidence = confidence

    def key(self):
        return (self.name.lower(), self.role)

    def speakable(self):
        return f"{self.role} {self.name}"