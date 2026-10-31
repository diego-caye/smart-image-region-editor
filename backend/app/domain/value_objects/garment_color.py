from enum import StrEnum


class GarmentColor(StrEnum):
    """The fixed palette a garment edit can use. A closed set rather than a
    free value, for the same reason operations are: the user picks, never
    types, and every color has a tested meaning in the editing prompts."""

    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    BLACK = "black"
    WHITE = "white"
    GRAY = "gray"
