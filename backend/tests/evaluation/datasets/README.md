# Golden datasets

Each `golden_*.json` file is a manifest of hand-picked `(image, region,
operation)` cases used to regression-test the edit pipeline's core
guarantees against real photos over time — not to grade detection
accuracy (that's `backend/tests/integration/test_vision_live.py`'s job).

## Schema

```jsonc
{
  "entries": [
    {
      "id": "short-unique-id",
      // Relative to this datasets/ directory. Real photos are NOT
      // committed to this repo (that needs the subject's consent, which
      // is the depositor's call, not something to assume) — add your own
      // locally under datasets/images/ (gitignored) and point entries at
      // them. Entries whose image_path doesn't exist are skipped, not
      // failed.
      "image_path": "images/example.jpg",
      "region_type": "right_hand",
      // Ground truth, not re-detected — this dataset evaluates
      // editing+compositing, not the detector.
      "region_box": [694, 855, 928, 1022],
      "operation": "peace_sign",
      // All optional; default from region_preservation.py if omitted.
      "pixel_tolerance": 8,
      "max_changed_fraction": 0.01,
      "grow_px": 40,
      "feather_px": 12
    }
  ]
}
```

## Running

```powershell
./.venv/Scripts/pytest -m live_comfyui tests/evaluation/test_golden_dataset.py
```

Needs the real ComfyUI + SAM2 (same requirements as any other
`live_comfyui`/`live_models` test) since it runs each entry through the
actual segmenter, editor and compositor — not fakes.

## What's evaluated today

- **`region_preservation`** (`../evaluators/region_preservation.py`) —
  implemented: pixels outside the (grown+feathered) mask stay unchanged.
- **`edit_quality`**, **`identity_preservation`** — not implemented yet;
  see their module docstrings in `../evaluators/` for the intended
  approach. The golden-dataset runner only checks region_preservation for
  now.
