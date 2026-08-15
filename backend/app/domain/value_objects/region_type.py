from enum import StrEnum


class RegionType(StrEnum):
    """Kinds of region the app knows how to detect and edit.

    FACE, LEFT_HAND and RIGHT_HAND are detected in the MVP. MOUTH and EYES are
    defined here already so the rest of the system (operation catalog, edit
    session, API/DB shape) has a stable place for them; wiring an actual
    detector for them later is an additive change that needs no change to
    this enum, to Application, or to the API contract.
    """

    FACE = "face"
    LEFT_HAND = "left_hand"
    RIGHT_HAND = "right_hand"
    MOUTH = "mouth"
    EYES = "eyes"
