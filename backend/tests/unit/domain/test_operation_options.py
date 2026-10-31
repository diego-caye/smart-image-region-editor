import pytest

from app.domain.services.operation_options import (
    InvalidOperationOptions,
    ensure_valid_options,
    takes_color,
)
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor


def test_garments_that_come_in_colors_take_one():
    assert takes_color(EditOperation.HOODIE)
    assert takes_color(EditOperation.PANTS_COLOR)
    # blue is part of what "blue jeans" are
    assert not takes_color(EditOperation.BLUE_JEANS)
    assert not takes_color(EditOperation.SUNGLASSES)


def test_a_colored_operation_without_a_color_is_rejected():
    with pytest.raises(InvalidOperationOptions):
        ensure_valid_options(EditOperation.JACKET, None)


def test_a_color_on_an_operation_that_takes_none_is_rejected():
    with pytest.raises(InvalidOperationOptions):
        ensure_valid_options(EditOperation.PEACE_SIGN, GarmentColor.RED)


def test_valid_combinations_pass():
    ensure_valid_options(EditOperation.JACKET, GarmentColor.BLACK)
    ensure_valid_options(EditOperation.PEACE_SIGN, None)
