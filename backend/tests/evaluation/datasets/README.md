# Golden datasets

Each `golden_*.json` file is a manifest of hand-picked `(image, region,
operation)` cases used to regression-test the edit pipeline's core
guarantees against real photos over time — not to grade detection
accuracy (that's `backend/tests/integration/test_vision_live.py`'s job).
Every `golden_*.json` in this directory is picked up automatically.

## Schema

```jsonc
{
  "entries": [
    {
      "id": "short-unique-id",
      // Relative to this datasets/ directory. images/ is gitignored: photos
      // are never committed to this repo.
      "image_path": "images/example.jpg",
      // Optional. If set and the image isn't present yet, the runner
      // downloads it here on first run. Only use images whose license
      // allows it (the bundled entries use Unsplash-licensed photos).
      // Without it, an entry whose image is missing is skipped, not failed
      // — that's how you add your own photos (put them in images/
      // yourself; consent for a real person's photo is your call).
      "source_url": "https://images.unsplash.com/photo-...?fm=jpg&w=1200",
      "credit": "Photographer on Unsplash (Unsplash License)",
      "region_type": "right_hand",
      // Ground truth, not re-detected — this dataset evaluates
      // editing+compositing, not the detector. Pixel coordinates in the
      // image as downloaded (keep the URL's w= fixed so they stay valid).
      "region_box": [694, 855, 928, 1022],
      // Optional: where the face is, to also run identity_preservation.
      "face_box": [610, 380, 760, 560],
      "operation": "peace_sign",
      // Required exactly for operations that take one (shirt_color,
      // t_shirt, jacket, hoodie, pants_color, shorts): red, blue, green,
      // yellow, black, white or gray.
      // "color": "red",
      // All optional.
      "pixel_tolerance": 8,          // region_preservation
      "max_changed_fraction": 0.01,  // region_preservation
      "min_quality_score": 0.5,      // edit_quality
      "max_identity_drift": 0.03,    // identity_preservation
      "grow_px": 40,                 // default: mask_rules.mask_grow_px_for(region_type)
      "feather_px": 12
    }
  ]
}
```

Pick cases where the operation actually changes something visible (a
waving hand → peace sign, not waving → wave): edit_quality checks that the
edit moved the region *toward* the target, so a no-op case can't pass it.

## Running

```powershell
./.venv/Scripts/pip install -e ".[eval]"   # CLIP for edit_quality
./.venv/Scripts/pytest -m live_comfyui tests/evaluation/test_golden_dataset.py
```

Needs the real ComfyUI + SAM2 (same requirements as any other
`live_comfyui`/`live_models` test) since it runs each entry through the
actual segmenter, editor and compositor — not fakes. CLIP
(`openai/clip-vit-base-patch32`, ~600MB) is downloaded on first use and
runs on CPU.

## What's evaluated

- **`region_preservation`** (`../evaluators/region_preservation.py`) —
  pixels outside the (grown+feathered) mask stay unchanged.
- **`edit_quality`** (`../evaluators/edit_quality.py`) — zero-shot CLIP:
  among the operations the domain allows on that region, the edited crop
  must be classified as the requested one, and more confidently than the
  original crop was.
- **`identity_preservation`** (`../evaluators/identity_preservation.py`)
  — for entries with a `face_box`: the face mesh outside the edited area
  keeps its shape (drift ≤ 0.03 of the inter-ocular distance).
