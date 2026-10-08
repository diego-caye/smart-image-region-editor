from enum import StrEnum


class RegionType(StrEnum):
    """Kinds of region the app knows how to detect and edit.

    All eleven are detected: FACE/LEFT_HAND/RIGHT_HAND via YOLOv8, MOUTH/EYES
    via MediaPipe FaceLandmarker (cropped around the detected face box —
    running it on the full image misses small faces, verified against a
    real photo), BODY/TORSO/LEFT_ARM/RIGHT_ARM/LEFT_LEG/RIGHT_LEG via
    MediaPipe PoseLandmarker — BODY is the whole shoulders-to-feet envelope,
    the other five are sub-regions of it, the same "coarse region + finer
    sub-regions coexist" pattern as FACE containing MOUTH/EYES. LEFT_*/
    RIGHT_* follow PoseLandmarker's own anatomical convention, verified to
    already match this project's screen-position convention for hands (a
    subject facing the camera has their anatomical right hand on
    screen-left) — no flipping needed. FACE and all six BODY-derived types
    currently have no operations of their own (see
    region_operation_rules.py) — detected and shown, not yet editable.
    """

    FACE = "face"
    LEFT_HAND = "left_hand"
    RIGHT_HAND = "right_hand"
    MOUTH = "mouth"
    EYES = "eyes"
    BODY = "body"
    TORSO = "torso"
    LEFT_ARM = "left_arm"
    RIGHT_ARM = "right_arm"
    LEFT_LEG = "left_leg"
    RIGHT_LEG = "right_leg"
