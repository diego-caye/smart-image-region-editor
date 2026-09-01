from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage


@dataclass(slots=True)
class RawDetection:
    """A single detection in absolute pixel coordinates of whatever image
    was passed in. No Domain knowledge here — adapters/vision translates
    these into DetectedRegion entities."""

    label: str
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    confidence: float


class YoloDetector:
    """Thin wrapper around one Ultralytics YOLO bounding-box model (e.g.
    face_yolov8n.pt or hand_yolov8n.pt — both single-class models, so
    `label` is supplied by the caller rather than trusted from the model's
    own class names)."""

    def __init__(
        self,
        weights_path: Path,
        *,
        device: str,
        label: str,
        confidence_threshold: float = 0.35,
    ) -> None:
        from ultralytics import YOLO

        self._model = YOLO(str(weights_path))
        self._device = device
        self._label = label
        self._confidence_threshold = confidence_threshold

    def detect(self, image_bytes: bytes) -> list[RawDetection]:
        image = PILImage.open(BytesIO(image_bytes)).convert("RGB")
        results = self._model.predict(
            source=image,
            device=self._device,
            conf=self._confidence_threshold,
            verbose=False,
        )

        detections: list[RawDetection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                x_min, y_min, x_max, y_max = (int(v) for v in box.xyxy[0].tolist())
                if x_max <= x_min or y_max <= y_min:
                    continue
                detections.append(
                    RawDetection(
                        label=self._label,
                        x_min=x_min,
                        y_min=y_min,
                        x_max=x_max,
                        y_max=y_max,
                        confidence=float(box.conf[0]),
                    )
                )
        return detections
