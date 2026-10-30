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
    EditOperation.RED_SHIRT: (
        "Change the shirt on the upper body, including its sleeves, to a solid "
        "bright red color, keeping the same cut, fit and fabric folds."
        + _GARMENT_PRESERVE_CLAUSE
    ),
    EditOperation.BLACK_JACKET: (
        "Dress the upper body in a black jacket, sleeves included, fitted "
        "naturally to the pose with realistic fabric folds."
        + _GARMENT_PRESERVE_CLAUSE
    ),
    EditOperation.WHITE_TSHIRT: (
        "Change the top on the upper body into a plain white crew-neck "
        "T-shirt, fitted naturally to the pose."
        + _GARMENT_PRESERVE_CLAUSE
    ),
    EditOperation.BLUE_JEANS: (
        "Change the pants on both legs into classic blue denim jeans, keeping "
        "the same fit and length, with fabric folds following the pose."
        + _GARMENT_PRESERVE_CLAUSE
    ),
    EditOperation.SHORTS: (
        "Change the pants on both legs into knee-length shorts, showing the "
        "lower legs below the knees with natural skin, same shoes."
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


def prompt_for(operation: EditOperation) -> str:
    try:
        return _PROMPTS[operation]
    except KeyError as exc:
        raise ValueError(f"No Qwen prompt configured for operation '{operation}'") from exc
