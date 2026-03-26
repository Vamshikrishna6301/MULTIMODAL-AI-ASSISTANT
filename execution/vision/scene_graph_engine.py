"""
Scene Graph Engine for Phase 4
Analyzes spatial relationships between detected objects
"""
import numpy as np


class SceneGraphEngine:
    """
    Builds scene understanding through:
    - Object relationship detection
    - Spatial proximity analysis
    - Interaction inference
    """
    
    def __init__(self):
        self.relationship_cache = {}
    
    def analyze_frame(self, detections: list) -> dict:
        """
        Analyze spatial relationships in frame
        
        Returns:
            dict with relationships, proximities, interactions
        """
        if not detections:
            return {"relationships": [], "interactions": []}
        
        relationships = self._find_relationships(detections)
        interactions = self._infer_interactions(detections, relationships)
        
        return {
            "relationships": relationships,
            "interactions": interactions,
            "scene_description": self._generate_description(detections, relationships)
        }
    
    def _find_relationships(self, detections: list) -> list:
        """Find spatial relationships between objects"""
        relationships = []
        
        for i, obj1 in enumerate(detections):
            for obj2 in detections[i+1:]:
                rel = self._compute_relationship(obj1, obj2)
                if rel:
                    relationships.append(rel)
        
        return relationships
    
    def _compute_relationship(self, obj1: dict, obj2: dict) -> dict:
        """Compute spatial relationship between two objects"""
        box1 = obj1.get("bbox", [0, 0, 1, 1])
        box2 = obj2.get("bbox", [0, 0, 1, 1])
        
        # Calculate centers
        center1 = [(box1[0] + box1[2]) / 2, (box1[1] + box1[3]) / 2]
        center2 = [(box2[0] + box2[2]) / 2, (box2[1] + box2[3]) / 2]
        
        # Distance between centers
        distance = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
        
        # Determine relationship
        if distance < 0.15:
            relationship = "overlapping"
        elif distance < 0.3:
            relationship = "very close"
        elif distance < 0.5:
            relationship = "nearby"
        else:
            relationship = "separate"
        
        # Determine relative position
        if center1[0] < center2[0]:
            left_right = "left of"
        else:
            left_right = "right of"
        
        if center1[1] < center2[1]:
            up_down = "above"
        else:
            up_down = "below"
        
        return {
            "object1": obj1.get("label"),
            "object2": obj2.get("label"),
            "spatial_relationship": relationship,
            "relative_position": f"{left_right} and {up_down}",
            "distance": distance
        }
    
    def _infer_interactions(self, detections: list, relationships: list) -> list:
        """Infer possible interactions between objects"""
        interactions = []
        
        for rel in relationships:
            obj1 = rel["object1"]
            obj2 = rel["object2"]
            spatial = rel["spatial_relationship"]
            
            # Rule-based interaction inference
            if spatial in ["overlapping", "very close"]:
                if (obj1 == "person" and obj2 == "phone") or (obj1 == "phone" and obj2 == "person"):
                    interactions.append(f"A person is holding a phone")
                elif (obj1 == "person" and obj2 == "cup") or (obj1 == "cup" and obj2 == "person"):
                    interactions.append(f"A person is holding a cup")
                elif (obj1 == "person" and obj2 == "chair") or (obj1 == "chair" and obj2 == "person"):
                    interactions.append(f"A person is sitting on a chair")
        
        return interactions
    
    def _generate_description(self, detections: list, relationships: list) -> str:
        """Generate natural language scene description"""
        if not detections:
            return "Empty scene"
        
        # Count objects by label
        label_counts = {}
        for det in detections:
            label = det.get("label", "unknown")
            label_counts[label] = label_counts.get(label, 0) + 1
        
        # Build description
        parts = []
        for label, count in label_counts.items():
            if count == 1:
                parts.append(f"1 {label}")
            else:
                parts.append(f"{count} {label}s")
        
        description = "I see: " + ", ".join(parts)
        
        # Add relationships if any
        if relationships:
            spatial_rels = [r for r in relationships if r["spatial_relationship"] != "separate"]
            if spatial_rels:
                description += ". "
                description += spatial_rels[0]["object1"] + " is "
                description += spatial_rels[0]["spatial_relationship"] + " "
                description += spatial_rels[0]["object2"]
        
        return description
