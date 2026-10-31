import pytest

from app.domain.services.operation_options import takes_color
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor
from app.infrastructure.image_editing.comfyui.operation_prompts import prompt_for


def _prompt(operation: EditOperation, color: GarmentColor = GarmentColor.RED) -> str:
    return prompt_for(operation, color if takes_color(operation) else None)


@pytest.mark.parametrize("operation", list(EditOperation))
def test_every_edit_operation_has_a_prompt(operation: EditOperation):
    prompt = _prompt(operation)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_prompts_are_distinct_per_operation():
    prompts = {op: _prompt(op) for op in EditOperation}
    assert len(set(prompts.values())) == len(prompts)


@pytest.mark.parametrize("color", list(GarmentColor))
def test_a_garment_prompt_names_the_chosen_color(color: GarmentColor):
    assert color.value in prompt_for(EditOperation.HOODIE, color)


def test_a_garment_prompt_needs_a_color():
    with pytest.raises(ValueError):
        prompt_for(EditOperation.HOODIE)
