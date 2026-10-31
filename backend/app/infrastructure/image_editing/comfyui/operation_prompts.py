"""EditOperation -> Qwen Image Edit instruction text. This is exactly the
kind of "translate a structured choice into a specific model's prompt"
detail the user never sees and Domain never knows about — it belongs here,
in Infrastructure, not in domain/value_objects/edit_operation.py.

Prompts are in English (Qwen Image Edit follows English instructions more
reliably) and all end with the same "preserve everything else" clause —
belt-and-suspenders alongside the compositor, which is what actually
*guarantees* the rest of the image is untouched.
"""

from __future__ import annotations

from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor

_PRESERVE_CLAUSE = (
    " Keep the skin tone, clothing, lighting, art style and background exactly the same."
)
# Garment edits can't use _PRESERVE_CLAUSE — "keep the clothing the same"
# would contradict the instruction itself.
_GARMENT_PRESERVE_CLAUSE = (
    " Keep the person's pose, body shape, skin, hands, lighting, art style and"
    " background exactly the same."
)

_PROMPTS: dict[EditOperation, str] = {
    EditOperation.WAVE: (
        "Change the hand gesture to an open waving hand: fingers extended and "
        "spread naturally, palm facing forward, as if greeting someone."
        + _PRESERVE_CLAUSE
    ),
    EditOperation.PEACE_SIGN: (
        "Change the hand gesture to a peace sign: index and middle fingers "
        "extended and spread in a V shape, other fingers curled into the palm, "
        "thumb resting over the curled fingers."
        + _PRESERVE_CLAUSE
    ),
    EditOperation.THUMBS_UP: (
        "Change the hand gesture to a thumbs up: hand closed into a fist with "
        "the thumb extended straight upward."
        + _PRESERVE_CLAUSE
    ),
    EditOperation.FIST: (
        "Change the hand gesture to a closed fist: all fingers curled tightly "
        "into the palm, thumb wrapped over the fingers."
        + _PRESERVE_CLAUSE
    ),
    EditOperation.GLOVES: (
        "Put a black leather glove on the hand, keeping the exact same gesture "
        "and finger positions."
        + _GARMENT_PRESERVE_CLAUSE
    ),
    EditOperation.SMILE: (
        "Change the mouth to a gentle closed-mouth smile, corners of the lips "
        "turned upward."
        + _PRESERVE_CLAUSE
    ),
    EditOperation.SMILE_WITH_TEETH: (
        "Change the mouth to a wide open smile showing the upper row of teeth."
        + _PRESERVE_CLAUSE
    ),
    EditOperation.CLOSED_MOUTH: (
        "Change the mouth to a neutral closed, relaxed expression with no teeth "
        "visible."
        + _PRESERVE_CLAUSE
    ),
    EditOperation.OPEN_EYES: (
        "Change the eyes to be fully open and alert, looking forward naturally."
        + _PRESERVE_CLAUSE
    ),
    EditOperation.CLOSED_EYES: (
        "Change the eyes to be gently closed, as if blinking or relaxed, eyelids "
        "fully down."
        + _PRESERVE_CLAUSE
    ),
    EditOperation.SUNGLASSES: (
        "Add a pair of dark sunglasses with thin black frames over the eyes, "
        "resting naturally on the nose and following the angle of the face."
        + _PRESERVE_CLAUSE
    ),
    EditOperation.BLUE_JEANS: (
        "Change the pants on both legs into classic blue denim jeans, keeping "
        "the same fit and length, with fabric folds following the pose."
        + _GARMENT_PRESERVE_CLAUSE
    ),
    EditOperation.WRISTWATCH: (
        "Add a classic wristwatch with a round metal case and a dark leather "
        "strap on the wrist."
        + _PRESERVE_CLAUSE
    ),
    EditOperation.BRACELET: (
        "Add a simple thin bracelet around the wrist."
        + _PRESERVE_CLAUSE
    ),
}


# Garment operations that take a GarmentColor (operation_options.py): the
# template gets the color phrase via {color}.
_COLORED_PROMPTS: dict[EditOperation, str] = {
    # Names what to leave alone on purpose: on a subject wearing an open
    # jacket over a T-shirt, an earlier "the shirt, including its sleeves"
    # wording made Qwen paint the *jacket's* sleeves red (the shirt's own
    # sleeves being hidden), leaving a gray vest with red sleeves.
    EditOperation.SHIRT_COLOR: (
        "Change the color of the shirt or T-shirt worn on the upper body to a "
        "solid {color}, keeping its cut, fit and fabric folds. Leave anything "
        "worn over it, such as a jacket or coat, unchanged."
        + _GARMENT_PRESERVE_CLAUSE
    ),
    EditOperation.T_SHIRT: (
        "Change the top on the upper body into a plain {color} crew-neck "
        "T-shirt, fitted naturally to the pose."
        + _GARMENT_PRESERVE_CLAUSE
    ),
    EditOperation.JACKET: (
        "Dress the upper body in a {color} jacket, sleeves included, fitted "
        "naturally to the pose with realistic fabric folds."
        + _GARMENT_PRESERVE_CLAUSE
    ),
    EditOperation.HOODIE: (
        "Change the top on the upper body into a plain {color} hooded "
        "sweatshirt, hood down behind the neck, fitted naturally to the pose."
        + _GARMENT_PRESERVE_CLAUSE
    ),
    EditOperation.PANTS_COLOR: (
        "Change the color of the pants on both legs to a solid {color}, "
        "keeping their cut, fit, length and fabric folds."
        + _GARMENT_PRESERVE_CLAUSE
    ),
    EditOperation.SHORTS: (
        "Change the pants on both legs into {color} knee-length shorts, showing "
        "the lower legs below the knees with natural skin, same shoes."
        + _GARMENT_PRESERVE_CLAUSE
    ),
}

# A slightly more specific phrase than the bare color name, so the shade
# asked for is less open to interpretation.
_COLOR_PHRASES: dict[GarmentColor, str] = {
    GarmentColor.RED: "bright red",
    GarmentColor.BLUE: "royal blue",
    GarmentColor.GREEN: "forest green",
    GarmentColor.YELLOW: "mustard yellow",
    GarmentColor.BLACK: "deep black",
    GarmentColor.WHITE: "pure white",
    GarmentColor.GRAY: "medium gray",
}


def prompt_for(operation: EditOperation, color: GarmentColor | None = None) -> str:
    if operation in _COLORED_PROMPTS:
        if color is None:
            raise ValueError(f"Operation '{operation}' needs a color")
        return _COLORED_PROMPTS[operation].format(color=_COLOR_PHRASES[color])
    try:
        return _PROMPTS[operation]
    except KeyError as exc:
        raise ValueError(f"No Qwen prompt configured for operation '{operation}'") from exc
