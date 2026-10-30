"""Shared helpers for tests that read the golden-dataset manifests."""

from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

from PIL import Image

from app.domain.value_objects.bounding_box import BoundingBox

DATASETS_DIR = Path(__file__).parent / "datasets"


def all_entries() -> list[dict]:
    entries = []
    for manifest_path in sorted(DATASETS_DIR.glob("golden_*.json")):
        entries.extend(json.loads(manifest_path.read_text(encoding="utf-8"))["entries"])
    return entries


def ensure_image(entry: dict) -> Path | None:
    """The entry's image, downloading it from source_url on first use.
    None if it's missing and there's no source_url to fetch it from."""
    image_path = DATASETS_DIR / entry["image_path"]
    if image_path.is_file():
        return image_path
    if "source_url" not in entry:
        return None
    image_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = image_path.with_suffix(image_path.suffix + ".part")
    urllib.request.urlretrieve(entry["source_url"], tmp)
    tmp.replace(image_path)
    return image_path


def square_crop(image_bytes: bytes, box: BoundingBox) -> bytes:
    """A square crop centered on the region. CLIP's processor center-crops to
    a square, so a thin box (a mouth is ~4:1) would otherwise lose its ends."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    side = min(max(box.width, box.height), image.width, image.height)
    cx, cy = box.center
    left = int(min(max(0, cx - side / 2), image.width - side))
    top = int(min(max(0, cy - side / 2), image.height - side))
    buffer = io.BytesIO()
    image.crop((left, top, left + side, top + side)).save(buffer, format="PNG")
    return buffer.getvalue()
