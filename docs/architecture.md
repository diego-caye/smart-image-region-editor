# Architecture

## Principle

- **Domain** — what is true about the business (entities, value objects,
  pure rules). Zero imports of FastAPI, SQLAlchemy, PyTorch, ComfyUI, OpenCV,
  SAM, Hugging Face, LangGraph, or any external SDK.
- **Application** — what the app can do (use cases orchestrating Ports).
  Same restrictions as Domain.
- **Adapters** — how information comes in and goes out (HTTP, SQL
  persistence, translating vision/editing results into domain entities).
- **Infrastructure** — how each thing is technically implemented (concrete
  HTTP clients, ML models, database engine, configuration).

Dependencies always point inward: Infrastructure → Adapters → Application →
Domain, never the other way around.

## Backend

```
app/
  domain/
    entities/        Image, DetectedRegion, Mask, Edit, EditSession
    value_objects/    BoundingBox, RegionType, EditOperation
    ports/            image_repository, image_storage, image_detector,
                       image_segmenter, image_editor, image_compositor
    services/          region_operation_rules.py — which operations are
                       valid for which region type (business rule);
                       mask_rules.py — how far past its outline an edit
                       to each region type may reach
  application/
    use_cases/         upload_image, analyze_image, get_detected_regions,
                       list_operations_for_region, edit_region,
                       confirm_edit, discard_edit
    dto/               plain input/output objects for each use case
    ports/              agent_orchestrator.py — reserved port, no
                       implementation (see "Agents" below)
  adapters/
    http/               controllers (FastAPI routers) + schemas (Pydantic)
    persistence/         SqlAlchemyImageRepository — translates domain
                       entities ↔ SQLModel tables
    vision/              YoloImageDetector, Sam2ImageSegmenter,
                       MediaPipeRegionDetector, CompositeImageDetector —
                       translate raw YOLO/SAM2/MediaPipe output into
                       DetectedRegion/Mask
    image_editing/         ComfyUIImageEditor — uploads the crop, runs the
                       workflow, rescales the output back to the crop size
    imaging/               PillowImageCompositor — grows/feathers the
                       mask and composites; the one that guarantees
                       "seamless"
  infrastructure/
    vision/               device.py, model_registry.py, YoloDetector,
                       Sam2MaskPredictor, MediaPipeLandmarker — raw
                       wrappers around Ultralytics/SAM2/MediaPipe, knowing
                       nothing about Domain
    image_editing/comfyui/ client.py (HTTP + the /ws websocket for
                       per-node progress), workflow.py (loads the JSON
                       template and substitutes parameters),
                       workflows/qwen_edit.json, operation_prompts.py
                       (EditOperation → instruction)
    progress/             InMemoryEditProgressTracker — where a running
                       edit publishes its stage for polling requests
    storage/              FilesystemImageStorage
    database/             engine, SQLModel models, init_db
    config/               settings.py — single source of environment
                       variables
  main.py                composition root: builds adapters, injects them
                       into use cases, mounts the routers
```

`backend/Dockerfile`, `frontend/Dockerfile`, and `docker-compose.yml` (root)
deploy both services — see the "Docker" section below.

### Why `ImageCompositor` exists (not in the original tree)

Compositing pixels requires an image library, and Domain/Application can't
depend on any. The *rule* ("outside the mask, everything must stay the
same, with a feathered edge") is expressible in Application's terms; the
*implementation* (Pillow/numpy) lives behind this Port in
Adapters/Infrastructure — same as `ImageEditor`. This Port is what
guarantees "seamless" with our own code, not by hoping Qwen preserves the
rest of the image on its own.

### `EditSession` — why edits don't destroy each other

`EditSession.current_image_ref` starts out pointing at the original image.
Each `Edit` stores `source_image_ref` (which image it was applied to) and,
once confirmed, its `final_ref` becomes the session's new
`current_image_ref`. So "right hand → peace" followed by "mouth → smile"
applies the second edit on top of the first one's result, not the original.
Discarding an edit doesn't touch the session at all.

Undo is the same chain walked backwards: the last confirmed edit becomes
`REVERTED` and the session goes back to that edit's `source_image_ref`.
Nothing is deleted, so the history still shows it (struck through), and a
new edit after an undo simply builds on the restored image. One rule keeps
this honest: a preview can only be accepted while the image it was made
on is still the current one (`EditSession.is_current`). Otherwise a
preview generated before an undo — or before another edit was accepted —
would silently bring back, or drop, a change.

### Detection/segmentation: our own stack in the backend, not via ComfyUI

A deliberate design decision. Trade-off: backend and ComfyUI share a single
GPU (developed on an RTX 5080, 16GB). Mitigated in `infrastructure/config/settings.py`:

- `detection_device` (YOLOv8n face/hand) defaults to `cpu` — tiny model,
  fast, no VRAM footprint.
- `segmentation_device` (SAM2) defaults to `cuda` for quality, but is freed
  (`torch.cuda.empty_cache()`) immediately after each `analyze`, so there's
  free VRAM by the time ComfyUI loads Qwen Image Edit later in the flow.
- YOLO weights are reused from
  `C:\ComfyUI\models\ultralytics\bbox\{face,hand}_yolov8n.pt` if that file
  exists (same format, no duplicate download); if not (a fresh clone
  without a native ComfyUI install, or the Docker deployment without that
  bind mount), `model_registry.resolve_weights_file()` downloads the same
  files from `Bingsu/adetailer` on Hugging Face — verified byte-for-byte
  identical to the native install's. This makes the backend self-contained:
  it works with no ComfyUI installed at all.
- ComfyUI's SAM2 checkpoint is packaged as `.safetensors` for its own node,
  incompatible with the official `sam2` pip package — the backend
  downloads/caches its own copy via Hugging Face Hub
  (`facebook/sam2-hiera-base-plus`) the first time.

**Verified, not just implemented**: `torch==2.10.0+cu130` (identical to the
build ComfyUI itself uses) recognizes the RTX 5080 (`compute capability
(12, 0)`, Blackwell). Against a real photo: `YoloImageDetector` detected the
face + both hands with confidences 0.87/0.75/0.56, and the left/right
heuristic assigned them correctly; `Sam2ImageSegmenter`, fed the detected
face box, produced a real mask cropped to the hair/face contour (not a
rectangle) in ~16s including the checkpoint download. `sam2`'s real API
(not guessed) was confirmed by reading `sam2/sam2_image_predictor.py` and
`sam2/build_sam.py` from the installed package:
`SAM2ImagePredictor.from_pretrained(model_id, device=...)` →
`predictor.set_image(rgb_ndarray)` → `predictor.predict(box=xyxy_array,
multimask_output=False)`. The checkpoint is downloaded via
`huggingface_hub.hf_hub_download`, whose cache location can only be
controlled via the `HF_HOME` environment variable (no `cache_dir` parameter
anywhere in the call chain) — hence why `Sam2MaskPredictor` sets `HF_HOME`
instead of passing a kwarg.

**Left/right heuristic**: `hand_yolov8n.pt` detects "a hand", with no
laterality. With two hands, the leftmost one on screen is assigned as the
subject's right hand (mirror convention) and vice versa; with a single one,
its center is compared against the image's horizontal midpoint. Documented
as a known limitation in
`adapters/vision/yolo_sam2_image_detector.py::_assign_hand_sides` —
improving it (e.g. with a pose model that gives real laterality via
wrist/elbow) is a change contained to that function.

### Mouth/Eyes/Body/Torso/Limbs: MediaPipe, two-stage for the face, direct for the body

`MediaPipeRegionDetector` (adapters/vision) translates output from
`MediaPipeLandmarker` (infrastructure/vision, a wrapper around
`mediapipe`'s real Tasks API — its legacy `mediapipe.solutions` API doesn't
exist in the installed version, 1.0.1) into `DetectedRegion`.
`CompositeImageDetector` combines this with `YoloImageDetector` (face/hands)
behind a single `ImageDetector`; it's the only place that knows there are
two different ML stacks involved.

**Why mouth/eyes need YOLO's face box first**: verified against a real
photo (`person.jpg`, 466×658px, a face of ~46×68px) — `FaceLandmarker` on
the full image finds 0 faces, but cropping around YOLO's box (margin
`face_landmark_crop_margin_px=60px`) does find 1 face with 478 landmarks.
Two-stage detection, same pattern as YOLO→SAM2:
`MediaPipeRegionDetector.detect_mouth_and_eyes()` receives the already
detected FACE region's `bounding_box`, crops, runs `FaceLandmarker` on the
crop, and converts the indices of
`FaceLandmarksConnections.FACE_LANDMARKS_LIPS`/`_LEFT_EYE`/`_RIGHT_EYE`
(real constants from the installed package, not hand-copied) into boxes,
offsetting back from crop-local to full-image coordinates.

**Body and its sub-regions, no prior crop**: `PoseLandmarker` does find the
pose on the full image (33 landmarks, verified). A single
`detect_body()` call now returns BODY (the whole shoulders-to-feet
envelope, using the indices from `PoseLandmark.LEFT_SHOULDER` (11) onward,
excluding the purely facial landmarks 0-10 already covered by
face/mouth/eyes) **plus** four finer sub-regions derived from the same
landmarks — TORSO (shoulders+hips), LEFT_ARM/RIGHT_ARM
(shoulder→elbow→wrist→fingers), LEGS (both hips→knees→ankles→feet) — the
same "coarse region + finer sub-regions coexist" pattern already used for
FACE containing MOUTH/EYES. Each region's index set comes from a
`(RegionType, indices_fn, padding_ratio)` table (`_BODY_PART_SPECS`) so
adding another sub-region later is a one-line addition, not a new method.

**Why arms are split per side but legs aren't**: legs started out as
LEFT_LEG/RIGHT_LEG too, and were merged into one LEGS region once they got
operations. A garment covers both legs — editing one alone would leave one
leg in jeans and the other in the original pants. An accessory (watch,
bracelet), by contrast, genuinely belongs on one arm.

**LEFT_*/RIGHT_* convention, verified not assumed**: `PoseLandmark`'s
`LEFT_*`/`RIGHT_*` naming is MediaPipe's own anatomical convention (the
subject's actual left/right). Before relying on it, this was checked
against ground truth: `person.jpg`'s already-known YOLO-detected
`right_hand` box sits at x≈151-204, and `PoseLandmarker`'s `RIGHT_WRIST`
landmark resolved to x≈167 — inside that same box (`LEFT_WRIST` similarly
landed inside the `left_hand` box). So a subject facing the camera has
their anatomical right hand on screen-left, exactly matching this
project's existing `RegionType.RIGHT_HAND`/`LEFT_HAND` convention — no
flipping needed between the two detectors' outputs.

**Padding per region type** (`bbox_from_points`, a pure function with no
MediaPipe dependency, tested with synthetic landmarks): mouth 0.35, eyes
0.6, body 0.05, torso 0.15, arms 0.3, legs 0.15 — proportional to the raw
landmark box's size, not a fixed pixel margin. Arms need more padding than
the rest because their landmarks are centerline points
(shoulder/elbow/wrist) on a naturally thin limb, so the raw box undershoots
the sleeve's actual visible width; both legs together already span hip to
hip. Confidence fixed at 0.9 for landmark-based
regions: MediaPipe Tasks doesn't expose a single aggregate confidence score
the way YOLO does; it's a documented value, not a calibrated one.

**Verified against the real photo, twice**: first in the native venv, then
against the full stack in Docker (`docker compose up` with the
`libegl1`/`libgles2` fix already applied) — the exact same result both
times: every region type in a single call to
`CompositeImageDetector.detect()` — with visually correct, geometrically
plausible boxes (each arm box contains its corresponding hand box; legs
span from hip height to the bottom of the frame). On a half-body photo,
LEGS is correctly absent rather than a made-up box (see the zero-size
guard in `bbox_from_points`). The eyes box came out very thin (62×7px) in
one photo because the source face is already small (46×68px); that's a
consequence of the source resolution, not a code bug — with a larger face
in pixels, the eyes box scales proportionally.

**Body-part operations**: TORSO gets shirt color / T-shirt / jacket /
hoodie, each arm gets wristwatch / bracelet, LEGS gets blue jeans / pants
color / shorts; EYES also get sunglasses and hands gloves. FACE and the
whole-body BODY region stay detection-only: no single operation on them
makes sense yet without a much larger, riskier edit. Garment prompts use
their own preserve clause, since the shared one says "keep the clothing
exactly the same" — which would contradict the instruction itself.

**Garment colors**: rather than one operation per color (the first version
had RED_SHIRT, BLACK_JACKET, WHITE_TSHIRT), garments that come in colors
take a `GarmentColor` option. Which operations take one is a domain rule
(`domain/services/operation_options.py`), checked by the use case next to
the region rule — a garment without a color, or a color on a peace sign,
is a 422 before anything runs. The catalog lists the palette per
operation, so the UI shows swatches without knowing that rule itself. The
color is stored on the Edit; `init_db` adds the new nullable column to an
existing database and rewrites edits made with the three old operations
(`red_shirt` → `shirt_color` + red, and so on), so old histories still
load. The ComfyUI prompts fill a template with a slightly more specific
color phrase than the bare name ("royal blue", "pure white"), so the
shade asked for is less open to interpretation.

### ComfyUI — real API (not invented)

Confirmed by reading a real install's `server.py` (ComfyUI's own source,
not its docs):

```
POST /prompt            queue a workflow (API-format, not the UI format
                         with subgraphs)
GET  /history/{id}      result + possible node_errors
GET  /queue              queue status
POST /upload/image        upload an input image
GET  /view?filename=…&subfolder=…&type=…   download a result
GET  /object_info[/{class}]  schema of each installed node
GET  /system_stats        GPU/VRAM info
POST /interrupt            cancel the running execution
GET  /ws?clientId=…        real-time events for prompts queued with that
                         client_id — what the client follows a run with
                         (see "Edit progress" below)
```

Models already installed and confirmed on disk:
`qwen_image_edit_2511_fp8mixed.safetensors` + 4-step Lightning LoRA +
`qwen_2.5_vl_7b_fp8_scaled` (encoder) + `qwen_image_vae`.

### The editing graph — why it does NOT use inpainting nodes

`infrastructure/image_editing/comfyui/workflows/qwen_edit.json` is the real
workflow (API format, verified node by node against `/object_info` and
against a real run, not guessed): `LoadImage` → `FluxKontextImageScale` →
(`TextEncodeQwenImageEditPlus` × 2, positive/negative, each followed by
`FluxKontextMultiReferenceLatentMethod`) + `VAEEncode` → `UNETLoader` →
`ModelSamplingAuraFlow` → `CFGNorm` → `LoraLoaderModelOnly` (4-step
Lightning LoRA) → `KSampler` → `VAEDecode` → `SaveImage`. It's the same
graph as the reference workflow that ships with the checkpoint itself
(`image_qwen_image_edit_2511.json`), without the image2/image3 branches
(reserved for a future gesture reference image).

Deliberately **does not** use `InpaintModelConditioning`/
`VAEEncodeForInpaint` (classic inpainting nodes): Qwen Image Edit is an
instruction-based editor, not a UNet with a dedicated mask channel — the
reference image is injected via the *text encoder*
(`TextEncodeQwenImageEditPlus`), not via a mask in the graph.
`ComfyUIImageEditor` sends ComfyUI the **full crop** (region + context
margin, no mask) with the instruction as text, and lets Qwen edit the whole
crop; the mask never enters ComfyUI's graph. What enforces "only change
what was selected" is `PillowImageCompositor`, afterward, with the real
mask — exactly the rule the original spec asked for ("don't assume Qwen
will preserve the rest on its own").

### Mask: why the mask has to be *grown* before compositing

First live attempt: closed fist → "peace sign". Result: semi-transparent
"ghost" fingers instead of a clean gesture. Cause: SAM2's mask follows the
contour of the **original fist**; the new gesture's extended fingers fall
outside that contour, so compositing clips them (or leaves them half-done
because of the edge feathering). `Mask.grow_px` already existed on the
entity but wasn't applied to any pixel — it was dead metadata.

Fix: `ImageCompositor.composite()` now receives `grow_px`, and
`PillowImageCompositor` dilates the mask (`ImageFilter.MaxFilter`) before
feathering it (`GaussianBlur`). `EditRegionUseCase` uses
`DEFAULT_MASK_GROW_PX = 40` (was 8) — deliberately generous, because an
edit can change the region's silhouette (an open hand from a fist takes up
more space than the fist did). Verified: the same case (fist → peace) with
the fix gives a clean gesture, no ghosting; the left hand, face, hair, and
clothes stay intact. There's a slight residual softening where the hand
crosses strands of hair — acceptable for the MVP, adjustable by raising
`grow_px` or another approach (edge-aware masking) if needed later.

**Per region type, not one global value** (`domain/services/mask_rules.py`):
40px is right for a gesture but wrong for a garment. Recoloring a shirt
doesn't change the silhouette, and 40px of grown mask around a torso
reaches into the arms and background — anything Qwen changed there would
leak into the composite. So gesture regions (hands, mouth, eyes) keep 40px
and garment/accessory regions (torso, arms, legs) use 16px. It's keyed by
region type rather than operation because a region's mask is computed once
and cached with its grow_px, and every operation on a given region type
falls in the same category anyway.

### Inner-layer mask: a shirt edit can't touch the jacket over it

The TORSO mask is the union of SAM2's box mask (on the suit photo, the
open jacket with its sleeves: 57% of the box) and its center-point mask
(the T-shirt: another 24%). That's right for a jacket edit, but it also
*allowed* a hoodie edit to repaint the jacket's sleeves — and a real one
did, in 1 of 4 runs, leaving a vest. Prompting against it backfired:
"leave the jacket unchanged, including its sleeves" made it 7 of 7.

So the fix is structural, like the compositor itself. `mask_rules.py`
gives tops worn under something (shirt color, T-shirt, hoodie)
`MaskScope.INNER_LAYER`: the center-point mask alone, plus a strip straight
above its neckline (10% of the region's height) minus the jacket, because a
hoodie's hood rests behind the neck — with the bare shirt mask it vanished
and CLIP's hoodie score went 0.06 → 0.15; with the strip, 0.06 → 0.29.
Without a jacket the point's mask is the whole top, so nothing is lost; if
the point lands on something tiny (under 5% of the box) it falls back to
the whole region. Masks are cached per (region, scope); the region keeps
linking to its whole-region one. Measured on real edits: 6 of 6 kept the
jacket intact, and the golden torso cases pass with it.

### Resolution: Qwen's output isn't the crop's size

Qwen Image Edit returns the image at its own preferred resolution, not
necessarily the sent crop's. `ComfyUIImageEditor` rescales the result back
to `region_box_used`'s exact size (Lanczos) before returning it — so
`PillowImageCompositor` never needs to know anything about the model's
internal resolution, it only works with pixels that already match the
cropped mask.

### Edit progress — stages that say what's really happening

An edit takes ~95s in Docker with the default GPU-sharing settings, so the
UI shows a progress bar with the current stage. The stages come from a
measurement, not assumptions. Following one real run over ComfyUI's
websocket (`/ws`, events confirmed in its `execution.py`/`main.py`):

| Time | Event |
|---|---|
| 0.3s | the three model **loader** nodes come back `execution_cached` |
| 1.1–11.7s | the two `TextEncodeQwenImageEditPlus` nodes (~5s each) |
| 11.7s | `KSampler` starts… |
| 41.6s | …and reports its first sampling step: **~30s of model loading** |
| 41.6–48.8s | steps 1–4 |
| 49.6–53.3s | `VAEDecode`, `SaveImage` → output available |
| 63.4s | the run is marked finished — after ComfyUI unloads the models |

With `--disable-smart-memory` the loader nodes don't load anything; weights
load lazily inside the first node that uses them. So "KSampler started"
means *loading the model*, and only its step events mean *generating* —
labelling the whole KSampler phase "generating 0/4" would have shown a
frozen bar for 30s. `ComfyUIImageEditor` maps node events to the domain's
`EditorStage`s (reading the instruction, loading the model, generating
step n/m, decoding); `EditRegionUseCase` adds its own around them
(segmenting with SAM2 before, compositing after).

How the progress reaches the browser: the POST that creates an edit only
answers once it's done, so the client picks a `progress_id` up front, sends
it with the POST, and polls `GET /edits/progress/{progress_id}` every
second meanwhile. The use case publishes each stage to an
`EditProgressTracker` port; the in-memory implementation is enough for one
backend process (several workers would need a shared store behind the same
port). The bar's fraction is stage-based rather than a time estimate,
because model load time varies too much (cached vs. not) for an estimate to
be honest; an elapsed-seconds counter shows it's alive during long stages.

Two side effects of switching the client from polling `/history` to the
websocket: the output is picked up as soon as `SaveImage` runs, instead of
~10s later when the history entry completes (~4s faster end to end in a
measured run, since downloading the image overlaps ComfyUI's cleanup); and
the first real recording of the UI showed the SAM2 masking step taking
~20s, invisible behind the old spinner — SAM2 is loaded and released on
every edit to free VRAM for Qwen.

### Before/after slider

The preview is compared in place: the edited image is stacked on the
original and clipped (`clip-path: inset(...)`) at a divider the user drags.
For a local edit this shows exactly what changed, and that nothing else
did, far better than two images side by side. The divider is a native
`<input type="range">` laid invisibly over the image, which gives mouse,
touch and arrow-key control without custom event handling.

The same slider (`BeforeAfterSlider`) also compares the original upload
with the result of every accepted edit, in the History card — the place
to check that several stacked edits still look like one photo. It only
shows once something has been applied, and disappears again when undo
gets back to the original.

### Persistence

SQLite for the MVP (`backend/data/app.db`), via SQLModel. The
`ImageRepository` Port is the only contract Application knows about;
migrating to Postgres later just means changing `database_url` in
`Settings` and the engine construction in
`infrastructure/database/engine.py` — no other file changes.

### Agents / LangGraph

`application/ports/agent_orchestrator.py` defines the contract
(`AgentOrchestrator.suggest_edit(...)`) but **has no implementation and
isn't wired up to anything**. The deterministic flow (upload → analyze →
select region → select operation → edit → composite) works with no LLM at
all. If an agent adds real value down the line, its implementation
(LangGraph, Google ADK, a custom loop) lives entirely in Infrastructure
behind this Port, just like any other adapter.

## Frontend

```
src/
  domain/         entities (UploadedImage, Region), value-objects
                  (BoundingBox), types (RegionType, EditOperation — mirror
                  the backend's enums, no presentation metadata)
  application/     use-cases (uploadImage, analyzeImage,
                  listOperationsForRegion, …) + ports (ImageApiPort — no
                  fetch)
  adapters/        http/HttpImageApi (implements ImageApiPort, the only
                  module that knows the backend's snake_case JSON) +
                  ui/regionPresentation.ts (region → label/color; separate
                  from the pure type in domain/types)
  infrastructure/  api/httpClient (the only place that knows the base URL
                  and handles HTTP errors) + state/EditSessionContext
                  (Context + reducer — enough for a linear flow, no Redux)
  presentation/    components/ (ImageUploader, RegionOverlay,
                  OperationGallery, ui/ — shadcn primitives) + lib/utils.ts
                  (cn(), generated by shadcn) + pages/ (EditorPage) +
                  hooks/useEditSession (the only thing components call)
```

Rule reinforced by the structure: component → hook → use case → port →
adapter (`adapters/http`, using `infrastructure/api`). No component imports
`fetch` or knows a backend route directly.

### shadcn/ui

Components generated with `npx shadcn@latest add <name>` (Radix +
Tailwind v4, "Nova" style). `components.json` (root of `frontend/`) has its
`aliases` reconfigured to land inside the hexagonal structure instead of
shadcn's default paths:

```json
"aliases": {
  "components": "@/presentation/components",
  "utils": "@/presentation/lib/utils",
  "ui": "@/presentation/components/ui",
  "lib": "@/presentation/lib",
  "hooks": "@/presentation/hooks"
}
```

`RegionOverlay` (colored, clickable boxes over the image, positioned as
percentages of `imageWidth`/`imageHeight` — they stay correctly aligned at
any rendered size, no `ResizeObserver` needed) and `OperationGallery` (a
`Card` grid with emoji + label, never plain text) are custom components
built on top of `presentation/components/ui/`'s primitives. Verified
visually end-to-end (headless Playwright against the real stack in Docker:
upload a real photo → `Analyze image` → region boxes correctly aligned over
face/left-hand/right-hand → click a region → gallery with the backend's
real emoji → click an operation → confirmation card).

## Testing

- `backend/tests/unit/domain/` — BoundingBox, region↔operation rules,
  `Edit` transitions. No mocks, pure logic.
- `backend/tests/unit/application/` — use cases against
  `tests/unit/application/fakes.py` (in-memory implementations of each
  Port). They also serve as living documentation of each contract.
- `backend/tests/integration/` — `SqlAlchemyImageRepository` against a real
  SQLite (tmp file) and the full API via `TestClient` with
  `dependency_overrides` to isolate storage/DB per test.
- `backend/tests/unit/adapters/` — `YoloImageDetector` (left/right
  heuristic, translation to `DetectedRegion`) against test doubles with the
  same interface as `YoloDetector`; no real torch/ultralytics, runs in
  milliseconds. `test_mediapipe_region_detector.py` covers
  `bbox_from_points` (pure function, synthetic landmarks) and
  `MediaPipeRegionDetector` against a fake `MediaPipeLandmarker` (same
  pattern, no real model). `test_composite_image_detector.py` covers
  `CompositeImageDetector`'s own wiring (YOLO's FACE box is passed into the
  MediaPipe stage; without FACE, that stage is skipped; all regions get
  concatenated) with both sub-detectors faked.
- `backend/tests/unit/adapters/test_pillow_image_compositor.py` — the
  "outside the mask, everything stays the same" guarantee at the pixel
  level (numpy), and the concrete case that reproduced the real "ghost
  fingers" bug (ungrown mask vs. growing it).
- `backend/tests/unit/infrastructure/` — the Qwen workflow template
  (placeholder substitution, numbers vs. strings, valid node references)
  and that every `EditOperation` has a prompt. `test_comfyui_client.py`
  feeds the websocket handling a scripted message sequence modeled on the
  measured run (other prompts' events ignored, binary preview frames
  skipped, errors raised, the history fallback). Progress is also covered
  from end to end without a GPU: node events → editor stages
  (`test_comfyui_image_editor_progress.py`), the use case's stage order
  (`test_edit_region.py`), and the `progress_id` API
  (`test_edits_api.py`).
- `backend/tests/integration/test_edits_api.py` — `/images/{id}/edits`,
  `/edits/{id}/confirm|discard` via `TestClient`, with the same
  detector/segmenter/editor fakes as the application tests plus the real
  `PillowImageCompositor` (fast, no GPU) for genuine pixel-composition
  coverage.
- `backend/tests/integration/test_vision_live.py` — opt-in
  (`pytest -m live_models`), against the real YOLO/SAM2 models.
- `backend/tests/integration/test_comfyui_edit_live.py` — opt-in
  (`pytest -m live_comfyui`), against real ComfyUI + Qwen Image Edit.
  Neither runs by default (`addopts` in `pyproject.toml` excludes them).
- `backend/tests/evaluation/` — golden dataset. Two real evaluators:
  - `evaluators/region_preservation.py`: numpy diff outside the mask, with
    its own synthetic tests in `test_region_preservation_evaluator.py`.
  - `evaluators/edit_quality.py`: zero-shot CLIP
    (`openai/clip-vit-base-patch32`, on CPU so it never competes for VRAM).
    The edited crop must be classified as the requested operation among
    the ones `region_operation_rules.py` allows on that region, and score
    at least 0.10 higher than the original crop did. That margin exists
    because CLIP is noisy on some untouched crops: calibrating on the real
    demo photos, it gave "an arm wearing a wristwatch" 0.64 on an arm with
    no watch. Its decision logic is unit-tested with a fake scorer
    (`test_edit_quality_evaluator.py`), and `test_edit_quality_live.py`
    (`-m live_models`) checks the real model recognizes an unedited waving
    hand as "wave".

  `identity_preservation.py` compares MediaPipe's 478-point face mesh on
  the original and the final image, on the same crop around the face.
  Landmarks where the blend mask is at 50% or more (in either image) are
  dropped — a smile is supposed to move the mouth — the rest are aligned with a similarity
  transform (Procrustes), and the RMS residual over the original's
  inter-ocular distance is the drift. It is a shape check, not a
  recognition one: face-recognition embeddings would also catch appearance
  changes, but the usual pretrained weights (insightface's packs, for
  example) are non-commercial, while MediaPipe and its model are Apache
  2.0 and already a backend dependency. Calibrated on real images, with
  the real blend masks, before picking the 0.03 threshold:

  | Case | drift |
  |---|---|
  | Garment, hand and arm edits (face untouched) | 0.0000–0.0010 |
  | Mouth → Smile with teeth (two runs) | 0.0083–0.0123 |
  | Eyes → Sunglasses (two runs) | 0.0163–0.0165 |
  | Same photo, JPEG q70 / Gaussian blur 1.5 | 0.0030–0.0082 |
  | Another person's face pasted over the face | 0.0466–0.0503 |

  The 50% cut matters: counting every pixel the mask touches, the mouth
  edit's 40px grow plus feathering left 19 of 478 landmarks, too few to
  say anything; at 50% it's 117.

  The geometry is unit-tested with a fake landmark finder
  (`test_identity_preservation_evaluator.py`): no drift for a moved,
  scaled or tilted copy, drift for a reshaped one, masked landmarks
  ignored, a face lost in the edit failing.
  `test_golden_dataset.py` (opt-in, `pytest -m live_comfyui`) runs every
  entry in `datasets/golden_*.json` through the real pipeline and checks
  both evaluators. The bundled entries point at Unsplash-licensed photos
  via `source_url` and are downloaded on first run (into a gitignored
  folder), so the dataset works on a fresh clone without committing any
  photo.
- `frontend/src/**/*.test.{ts,tsx}` — `HttpImageApi` with `fetch` mocked
  (includes `requestEdit`/`confirmEdit`/`discardEdit`), `EditorPage` with a
  `FakeImageApiPort` injected into the Context (covers the full flow:
  upload → analyze → select region → select operation → generate preview →
  accept/discard, including that switching region or operation clears any
  previous preview, and that accepting updates the displayed image and
  leaves the region ready for a second edit). Progress: `HttpImageApi`
  polls the right URL while the POST is pending and stops once it settles
  (fake timers), and `EditorPage` shows each stage's label and percent then
  drops the bar when the preview arrives. `PreviewComparison` checks the
  slider moves the clip of the "after" image.

## Docker

`docker-compose.yml` (root) builds three images:

- **comfyui** (`comfyui/Dockerfile`): vanilla ComfyUI, cloned directly from
  `comfyanonymous/ComfyUI` (tag `v0.37.0`) — **no custom_nodes**. Verified
  node by node (`grep` against the real source code) that all 13 node
  classes `qwen_edit.json` uses live in core `nodes.py`/`comfy_extras/`,
  none in a custom node package; the only thing needed from a native
  ComfyUI setup was the model files, not its custom node install. `entrypoint.sh`
  runs `download_models.sh` (downloads the 4 Qwen Image Edit files —
  verified via the real Hugging Face API, byte-for-byte identical to the
  ones already installed natively — into a named volume `comfyui_data`,
  only the first time) and then `python main.py --listen 0.0.0.0 --port
  8188`. It exists specifically so that **cloning this repo is enough**:
  without this container, someone without ComfyUI already installed would
  have to set up the whole Qwen Image Edit pipeline by hand.

  **Sharing the GPU**: it was developed on a machine running several other
  GPU containers (TTS, LLMs, another ComfyUI), where an idle ComfyUI
  holding ~14GB of VRAM would starve them — but reloading the models on
  every edit made each one take ~93s. The middle ground: keep them loaded
  while the user is editing, release them once they stop.
  `infrastructure/idle_release.py`'s `IdleReleaser` restarts a timer on
  every use; when `MODELS_IDLE_UNLOAD_SECONDS` (default 180) pass without
  one, the backend drops its SAM2 predictor and asks ComfyUI to unload
  through its real `POST /free` endpoint (`unload_models` +
  `free_memory`). Measured: 93.2s for the first edit, 24.4s and 26.5s for
  the next two, VRAM ~13GB while editing and back to the 2.4GB baseline
  after the timer. A release still pending when the process exits runs
  then — a golden-dataset run that ended before its timer fired once left
  ComfyUI holding 11.7GB with nobody left to free it. ComfyUI also runs
  with `--reserve-vram 4` (`COMFYUI_EXTRA_ARGS`) to keep 4GB free for
  other software.

  **Resumable model download**: `download_models.sh` uses `curl -C -`, so
  a container restart halfway through the ~31GB first-start download picks
  up where it left off instead of starting the 20GB model over (verified:
  Hugging Face answers the resumed request with `206 Partial Content`).

  **Real bug found on first startup**: with a freshly created `/data`
  volume (no custom nodes), `main.py` does
  `os.listdir(folder_paths.get_folder_paths("custom_nodes")[0])` with no
  existence check beforehand — crash-loops with `FileNotFoundError: [Errno
  2] No such file or directory: '/data/custom_nodes'`. Every other
  directory under `--base-directory`
  (`models`/`input`/`output`/`user`/`temp`) is created lazily via
  `os.makedirs(..., exist_ok=True)`; only `custom_nodes` isn't. Fixed with
  a simple `mkdir -p /data/custom_nodes` in `entrypoint.sh` before invoking
  `main.py` — confirmed by reading the real `folder_paths.py`/`main.py`
  inside the built image, not guessed.

  **Verified end-to-end, with all three real containers**: upload
  `person.jpg` → `/analyze` (real detection, all 6 region types) →
  `/edits` with `right_hand`'s `region_id` + `peace_sign` → real SAM2 +
  real Qwen Image Edit running *inside* the `comfyui` container (backend
  pointed at `COMFYUI_BASE_URL=http://comfyui:8188`, with no native ComfyUI
  install running at all) → `status: "preview_ready"` with a real image
  back. The rest of the photo (face, left hand, clothes, background) stayed
  intact in the preview, confirming `PillowImageCompositor` keeps working
  the same no matter where ComfyUI comes from.
- **backend** (`backend/Dockerfile`): `python:3.12-slim` — not an
  `nvidia/cuda` image, because PyTorch's `cu130` wheels bundle their own
  CUDA runtime as pip dependencies; all that's needed from the host is for
  it to expose the GPU to the container. `torch`/`torchvision` are
  installed **before** the rest (same `cu130` pin as native) so that
  `ultralytics`/`sam2`'s own unpinned `torch` dependency doesn't silently
  replace this build with one lacking support for this GPU. GPU access via
  `deploy.resources.reservations.devices` (Compose Spec, works with a
  normal `docker compose up`, no swarm needed) — confirmed working on the
  development machine (`docker run --gpus all ... nvidia-smi` sees the RTX
  5080).

  **Real bug when adding mediapipe**: its compiled Tasks API bindings
  `dlopen()` `libEGL.so.1` and `libGLESv2.so.2` when importing
  `mediapipe.tasks.python.vision.core.image`, even for purely CPU
  inference with no GPU/display involved — confirmed with two real
  `OSError`s, one at a time, against the running container (`ldd` on
  `mediapipe/tasks/c/libmediapipe.so` showed exactly which ones were
  missing). `python:3.12-slim` ships neither; the fix was adding
  `libegl1`/`libgles2` (alongside `libgl1`/`libglib2.0-0`, already needed
  by `opencv-python-headless`) to the Dockerfile's `apt-get install`.
- **frontend** (`frontend/Dockerfile`): multi-stage build, `node:20-alpine`
  → `nginx:1.27-alpine` serving the static `dist/`. `VITE_API_BASE_URL` is
  passed as a build-arg (Vite's env vars are compile-time) with the URL
  the *browser* should use — the host's port, not the container-internal
  one.

Points that change between native and Docker (both via env, no code
differs):

- `COMFYUI_BASE_URL`: `127.0.0.1:8188` natively → `http://comfyui:8188` in
  Docker by default (the service's name on Compose's network, not
  `host.docker.internal`: ComfyUI now runs in its own container, not on the
  host). Still overridable to `host.docker.internal:8188` if you'd rather
  keep using a native ComfyUI install (e.g. with your own custom nodes).
- YOLO weights: native Windows paths → an optional `COMFYUI_MODELS_DIR`
  from the host, mounted read-only at `/comfyui_models` inside the backend
  container — just a shortcut to reuse already-downloaded weights; if it's
  not set or the file isn't there, the backend downloads them itself from
  Hugging Face (see the previous section).
- Persistence: native `backend/data/` → named volumes (`backend_data`,
  `models_cache`, `comfyui_data`) so they survive `docker compose down`.
- Ports: `8420`/`5180`/`8188` across the three services — ComfyUI's `8188`
  is the same as its native default (free again in Docker since there's no
  native install running at the same time), and gives direct access to
  ComfyUI's own UI at `http://localhost:8188` to inspect the graph/queue by
  hand. All configurable via the root `.env`.

## Next steps (not implemented yet)

1. **Whole-body and face operations**: BODY and FACE are detected but still
   have no operations — a whole-body or whole-face edit is a much larger,
   riskier change than a gesture or a garment (identity drift, pose
   changes). `identity_preservation` now exists to catch shape drift, but
   a whole-face edit would mask out most of the mesh it compares, so it
   would need an appearance check too.
2. **Appearance-level identity check**: `identity_preservation` compares
   face shape only. A face-recognition embedding with a license that
   allows commercial use would let it compare appearance as well.
3. **Grow the golden dataset**: it currently has one case per kind of edit
   (gesture, expression, garment, legs, accessory) on two photos. More
   varied photos (lighting, skin tones, poses, occlusions) would make it a
   stronger regression net.
4. **Reference image per gesture**: the `ImageEditor.edit()` Port already
   accepts `reference_image_png_bytes` and the workflow already has
   `TextEncodeQwenImageEditPlus`'s `image2`/`image3` fields available —
   unused today because the text-only prompt already gives good results.
5. **Thin eyes box on small faces**: `EYES`'s padding is proportional to the
   raw landmark box, so on a photo with a face of only a few pixels (see
   the MediaPipe section above) the resulting box can end up too thin for a
   convincing open/close edit. Fixing this would need a minimum pixel
   height on top of the proportional padding, or requiring a minimum input
   resolution — not implemented, a pending trade-off to decide.
