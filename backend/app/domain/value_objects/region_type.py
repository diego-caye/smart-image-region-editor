from enum import StrEnum


class RegionType(StrEnum):
    """Kinds of region the app knows how to detect and edit.

    All ten are detected: FACE/LEFT_HAND/RIGHT_HAND via YOLOv8, MOUTH/EYES
    via MediaPipe FaceLandmarker (cropped around the detected face box —
    running it on the full image misses small faces, verified against a
    real photo), BODY/TORSO/LEFT_ARM/RIGHT_ARM/LEGS via MediaPipe
    PoseLandmarker — BODY is the whole shoulders-to-feet envelope, the other
    four are sub-regions of it, the same "coarse region + finer sub-regions
    coexist" pattern as FACE containing MOUTH/EYES.

    Arms are split per side but legs are not, on purpose: an accessory
    (a watch, a bracelet) belongs on one arm, but a garment covers both
    legs — editing one leg alone would leave one leg in jeans and the other
    in the original pants. LEFT_*/RIGHT_* follow PoseLandmarker's own
    anatomical convention, verified to already match this project's
    screen-position convention for hands (a subject facing the camera has
    their anatomical right hand on screen-left) — no flipping needed.
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
    LEGS = "legs"
