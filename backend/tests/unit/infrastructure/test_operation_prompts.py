import pytest

from app.domain.value_objects.edit_operation import EditOperation
from app.infrastructure.image_editing.comfyui.operation_prompts import prompt_for


@pytest.mark.parametrize("operation", list(EditOperation))
def test_every_edit_operation_has_a_prompt(operation: EditOperation):
    prompt = prompt_for(operation)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_prompts_are_distinct_per_operation():
    prompts = {op: prompt_for(op) for op in EditOperation}
    assert len(set(prompts.values())) == len(prompts)
