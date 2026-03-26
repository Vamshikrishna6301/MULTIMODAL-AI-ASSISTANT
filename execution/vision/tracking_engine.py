import time
from collections import Counter


# =====================================================
# IOU CALCULATION
# =====================================================

def compute_iou(boxA, boxB):

    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_area = max(0, xB - xA) * max(0, yB - yA)

    boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    union_area = boxA_area + boxB_area - inter_area

    if union_area == 0:
        return 0

    return inter_area / union_area


# =====================================================
# TRACKING ENGINE
# =====================================================

class TrackingEngine:

    def __init__(self,
                 iou_threshold=0.4,
                 max_missing_time=2.0,
                 label_history_size=5,
                 smoothing_alpha=0.5):

        self.iou_threshold = iou_threshold
        self.max_missing_time = max_missing_time
        self.label_history_size = label_history_size
        self.smoothing_alpha = smoothing_alpha

        self._next_id = 1
        self._tracked_objects = {}
        self._tracked_by_label = {}

    # =====================================================

    def update(self, detections):

        current_time = time.time()
        updated_objects = {}

        for det in detections:

            label = det["label"]
            bbox = det["bbox"]
            confidence = det["confidence"]

            matched_id = None
            best_iou = 0

            # -------------------------------------------------
            # MATCH WITH EXISTING TRACKED OBJECTS
            # -------------------------------------------------

            for obj_id, obj in self._tracked_objects.items():

                iou = compute_iou(bbox, obj["bbox"])

                if iou > best_iou and iou > self.iou_threshold:
                    best_iou = iou
                    matched_id = obj_id

            # -------------------------------------------------
            # UPDATE EXISTING OBJECT
            # -------------------------------------------------

            if matched_id is not None:

                prev_obj = self._tracked_objects[matched_id]
                old_bbox = prev_obj["bbox"]

                # 🔵 Bounding Box Smoothing (EMA)
                alpha = self.smoothing_alpha

                smoothed_bbox = (
                    int(alpha * bbox[0] + (1 - alpha) * old_bbox[0]),
                    int(alpha * bbox[1] + (1 - alpha) * old_bbox[1]),
                    int(alpha * bbox[2] + (1 - alpha) * old_bbox[2]),
                    int(alpha * bbox[3] + (1 - alpha) * old_bbox[3]),
                )

                # 🔵 Label Smoothing
                label_history = prev_obj["label_history"]
                label_history.append(label)

                if len(label_history) > self.label_history_size:
                    label_history.pop(0)

                stable_label = Counter(label_history).most_common(1)[0][0]

                updated_objects[matched_id] = {
                    "id": matched_id,
                    "bbox": smoothed_bbox,
                    "confidence": confidence,
                    "first_seen": prev_obj["first_seen"],
                    "last_seen": current_time,
                    "velocity": self._compute_velocity(old_bbox, smoothed_bbox),
                    "label_history": label_history,
                    "label": stable_label
                }
                self._tracked_by_label[stable_label] = {
                    "last_seen_time": current_time,
                    "last_position": smoothed_bbox,
                }

            # -------------------------------------------------
            # CREATE NEW OBJECT
            # -------------------------------------------------

            else:

                obj_id = self._next_id
                self._next_id += 1

                updated_objects[obj_id] = {
                    "id": obj_id,
                    "bbox": bbox,
                    "confidence": confidence,
                    "first_seen": current_time,
                    "last_seen": current_time,
                    "velocity": (0, 0),
                    "label_history": [label],
                    "label": label
                }
                previous = self._tracked_by_label.get(label)
                if previous and current_time - previous["last_seen_time"] <= 1.0:
                    self._tracked_by_label[label]["last_seen_time"] = current_time
                    self._tracked_by_label[label]["last_position"] = bbox
                else:
                    self._tracked_by_label[label] = {
                        "last_seen_time": current_time,
                        "last_position": bbox,
                    }

        # -------------------------------------------------
        # HANDLE TEMPORARY DISAPPEARANCE
        # -------------------------------------------------

        for obj_id, obj in self._tracked_objects.items():

            if obj_id not in updated_objects:

                if current_time - obj["last_seen"] < self.max_missing_time:
                    updated_objects[obj_id] = obj

        for label, tracked in list(self._tracked_by_label.items()):
            if current_time - tracked["last_seen_time"] > 2.0:
                del self._tracked_by_label[label]

        self._tracked_objects = updated_objects

        return list(self._tracked_objects.values())

    # =====================================================

    def _compute_velocity(self, old_bbox, new_bbox):

        old_center = (
            (old_bbox[0] + old_bbox[2]) / 2,
            (old_bbox[1] + old_bbox[3]) / 2
        )

        new_center = (
            (new_bbox[0] + new_bbox[2]) / 2,
            (new_bbox[1] + new_bbox[3]) / 2
        )

        return (
            new_center[0] - old_center[0],
            new_center[1] - old_center[1]
        )

    # =====================================================

    def get_tracked_objects(self):
        return list(self._tracked_objects.values())
