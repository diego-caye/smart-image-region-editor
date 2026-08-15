import pytest

from app.domain.value_objects.bounding_box import BoundingBox


def test_rejects_zero_or_negative_size():
    with pytest.raises(ValueError):
        BoundingBox(x_min=10, y_min=10, x_max=10, y_max=20)
    with pytest.raises(ValueError):
        BoundingBox(x_min=10, y_min=10, x_max=20, y_max=5)


def test_rejects_negative_coordinates():
    with pytest.raises(ValueError):
        BoundingBox(x_min=-1, y_min=0, x_max=10, y_max=10)


def test_width_height_area():
    box = BoundingBox(x_min=10, y_min=20, x_max=50, y_max=60)
    assert box.width == 40
    assert box.height == 40
    assert box.area == 1600


def test_expanded_grows_and_clamps_to_image_bounds():
    box = BoundingBox(x_min=10, y_min=10, x_max=20, y_max=20)
    grown = box.expanded(5, image_width=100, image_height=100)
    assert grown.as_xyxy() == (5, 5, 25, 25)

    near_edge = BoundingBox(x_min=2, y_min=2, x_max=8, y_max=8)
    grown_edge = near_edge.expanded(10, image_width=100, image_height=100)
    # clamped at 0, not negative
    assert grown_edge.x_min == 0
    assert grown_edge.y_min == 0


def test_clamped_keeps_box_inside_image():
    box = BoundingBox(x_min=90, y_min=90, x_max=150, y_max=150)
    clamped = box.clamped(image_width=100, image_height=100)
    assert clamped.x_max <= 100
    assert clamped.y_max <= 100
