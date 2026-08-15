from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """An axis-aligned box in absolute pixel coordinates of a specific image.

    x grows right, y grows down — the convention every detector/segmenter
    adapter is expected to normalize to before this value object is built.
    """

    x_min: int
    y_min: int
    x_max: int
    y_max: int

    def __post_init__(self) -> None:
        if self.x_min < 0 or self.y_min < 0:
            raise ValueError("BoundingBox coordinates cannot be negative")
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("BoundingBox must have positive width and height")

    @property
    def width(self) -> int:
        return self.x_max - self.x_min

    @property
    def height(self) -> int:
        return self.y_max - self.y_min

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2

    def expanded(self, margin_px: int, *, image_width: int, image_height: int) -> BoundingBox:
        """Grow the box by margin_px on every side, clamped to the image bounds.

        Used to give an editor extra surrounding context (e.g. wrist/forearm
        around a hand) without ever exceeding the source image.
        """
        if margin_px < 0:
            raise ValueError("margin_px cannot be negative")
        return BoundingBox(
            x_min=max(0, self.x_min - margin_px),
            y_min=max(0, self.y_min - margin_px),
            x_max=min(image_width, self.x_max + margin_px),
            y_max=min(image_height, self.y_max + margin_px),
        )

    def clamped(self, *, image_width: int, image_height: int) -> BoundingBox:
        return BoundingBox(
            x_min=max(0, min(self.x_min, image_width - 1)),
            y_min=max(0, min(self.y_min, image_height - 1)),
            x_max=max(1, min(self.x_max, image_width)),
            y_max=max(1, min(self.y_max, image_height)),
        )

    def as_xyxy(self) -> tuple[int, int, int, int]:
        return self.x_min, self.y_min, self.x_max, self.y_max
