from enum import StrEnum


class RegionType(StrEnum):
    """Kinds of region the app knows how to detect and edit.

    All six are detected: FACE/LEFT_HAND/RIGHT_HAND via YOLOv8, MOUTH/EYES
    via MediaPipe FaceLandmarker (cropped around the detected face box —
    running it on the full image misses small faces, verified against a
    real photo), BODY via MediaPipe PoseLandmarker (shoulders-to-feet
    envelope). FACE and BODY currently have no operations of their own
    (see region_operation_rules.py) — detected and shown, not yet editable.
    """

    FACE = "face"
    LEFT_HAND = "left_hand"
    RIGHT_HAND = "right_hand"
    MOUTH = "mouth"
    EYES = "eyes"
    BODY = "body"
