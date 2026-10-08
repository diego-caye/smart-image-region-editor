# Smart Image Region Editor

Upload a photo, the system detects regions (face, hands, mouth, eyes, body),
you visually select a region and a predefined transformation ("✌️ Peace
sign"), and only that region changes — the rest of the image is preserved.
Hexagonal architecture (Ports & Adapters) in both backend and frontend.
Includes a containerized ComfyUI, so cloning the repo and running
`docker compose up` is enough even if you don't have ComfyUI installed. See
[docs/architecture.md](docs/architecture.md) for the design decisions and
their reasoning.

## Current status

| Phase | What it includes | Status |
|---|---|---|
| 0 | Scaffolding, hexagonal structure, git | ✅ |
| 1–2 | Complete Domain + Application, image upload, persistence (SQLite) | ✅ |
| 3 | Face/hand detection (YOLOv8) + precise mask (SAM2), in the backend | ✅ |
| 3b | Frontend: selectable region overlay + visual operation gallery (shadcn/ui) | ✅ |
| 4 | Visual operation catalog | ✅ |
| 5 | Localized editing via ComfyUI + composition, end-to-end (backend + frontend) | ✅ |
| 6 | Golden dataset / evaluation | ✅ scaffolding + real `region_preservation` · `edit_quality`/`identity_preservation` are documented stubs |
| — | Docker deployment (backend + frontend, GPU) | ✅ |
| — | Extend to mouth/eyes/body/torso/limbs (detection) | ✅ MediaPipe — mouth/eyes are already editable; body, torso, arms, and legs are detected but have no operations yet |
| — | Containerized ComfyUI (self-contained repo, no native install required) | ✅ |

Everything marked "✅" has passing tests (unit + integration) and was also
verified against real running processes (`uvicorn`/`docker compose` +
`curl`, real detection on a real photo, and `vite build`).

**Ports**: this project uses `8420` (backend), `5180` (frontend), and `8188`
(ComfyUI) instead of the usual `8000`/`5173`, because the first two are
already in use by another project on this machine.

## Requirements

- **Backend**: Python 3.12 (already installed at
  `C:\Users\diego\AppData\Local\Programs\Python\Python312`). The project uses
  its own venv at `backend/.venv`, not the system's default Python 3.14
  (better compatibility with torch/ultralytics/sam2/mediapipe).
- **Frontend**: Node.js (v24 already installed) + npm.
- **ComfyUI**: only needed for a **native** run (outside Docker) — a local
  install at `http://127.0.0.1:8188`, required starting at Phase 5 (editing),
  not for detection/upload. **Not needed in Docker**: `docker compose up`
  spins up its own ComfyUI container (see the Docker section below).
- **GPU**: RTX 5080 (Blackwell). The backend uses the exact same PyTorch build
  as ComfyUI (`torch==2.10.0+cu130`) — installing it from PyPI's normal index
  would install a build without support for this GPU.
- **Docker** (optional, for deployment): Docker Desktop with the `nvidia`
  runtime enabled — already confirmed working on this machine
  (`docker run --gpus all ... nvidia-smi` works).

## Backend (native)

```powershell
cd backend
py -3.12 -m venv .venv          # first time only
copy .env.example .env          # adjust if needed

./.venv/Scripts/pip install -e ".[dev]"
# Detection/segmentation (Phase 3) — PyTorch build pinned for the RTX 5080:
./.venv/Scripts/pip install "torch==2.10.0+cu130" "torchvision==0.25.0+cu130" --index-url https://download.pytorch.org/whl/cu130
./.venv/Scripts/pip install -e ".[ml]"

./.venv/Scripts/uvicorn app.main:app --reload --port 8420
```

- API at `http://127.0.0.1:8420`, interactive docs at `/docs`.
- SQLite database at `backend/data/app.db` (created automatically). Images in
  `backend/data/images/{original,mask,preview,final}/`. SAM2 checkpoint
  cached in `backend/models_cache/` (downloaded only the first time,
  ~300MB, from Hugging Face — ComfyUI's `.safetensors` doesn't work here
  because its node loads it with a different loader than the official
  `sam2` package).
- Tests: `./.venv/Scripts/pytest` — fast, don't require GPU/models/ComfyUI by
  default. To also run the ones that do:
  `./.venv/Scripts/pytest -m live_models` (real YOLO+SAM2) or
  `./.venv/Scripts/pytest -m live_comfyui` (real Qwen Image Edit).

Endpoints available today:

- `POST /images` — uploads an image (multipart `file`), returns
  `{image_id, width, height, url}`.
- `POST /images/{id}/analyze` — runs real detection (YOLOv8 face+hands +
  MediaPipe mouth/eyes/body/torso/limbs) and persists the found regions.
- `GET /images/{id}/regions` — re-reads the already-detected regions.
- `GET /regions/{region_type}/operations` — catalog of operations valid for a
  region type (e.g. `right_hand` → wave/peace/thumbs-up/fist).
- `POST /images/{id}/edits` — `{region_id, operation}` → real localized
  editing (SAM2 + Qwen Image Edit via ComfyUI + composition), returns a
  preview without touching the "official" image yet. ~25-30s per edit.
- `POST /edits/{id}/confirm` — the preview becomes the session's current
  image; the next edit is applied on top of this result, not the original.
- `POST /edits/{id}/discard` — discards the preview, the session doesn't
  change.
- `GET /static/{storage_ref}` — serves the bytes of a saved image.

### Golden dataset / evaluation

`backend/tests/evaluation/`:

- `evaluators/region_preservation.py` — real: measures in pixels whether
  everything outside the mask stayed the same between the original and the
  final image. Has its own unit tests (synthetic, no GPU) and the golden
  dataset runner uses it against real edits.
- `evaluators/edit_quality.py`, `evaluators/identity_preservation.py` —
  documented stubs (`NotImplementedError` with the intended approach in the
  docstring), don't block the MVP.
- `datasets/golden_{hand,face,mouth}_edits.json` — empty on purpose: the
  schema and runner (`test_golden_dataset.py`, opt-in via
  `pytest -m live_comfyui`) are ready, but real photos to populate them
  aren't uploaded to the repo without consent — see `datasets/README.md`
  for the schema and how to add your own locally (`datasets/images/`,
  already in `.gitignore`).

## Frontend (native)

```powershell
cd frontend
npm install
npm run dev      # http://localhost:5180
npm test         # vitest
npm run build    # type-check + production build
```

Points at `http://127.0.0.1:8420` (backend) by default. To change it, copy
`.env.example` to `.env.local` and adjust `VITE_API_BASE_URL`.

UI built with [shadcn/ui](https://ui.shadcn.com) (Radix + Tailwind v4) —
components generated in `src/presentation/components/ui/` via
`npx shadcn@latest add <component>` (the root `components.json` already
points the `@/presentation/...` aliases at the project's hexagonal
structure, not shadcn's default paths).

The full flow works end-to-end: upload an image → **Analyze image** (real
YOLOv8 + MediaPipe detection, up to 11 region types: face, hands, mouth,
eyes, body, torso, arms, legs) → overlay of selectable, colored boxes over
the image, larger regions rendered first so smaller ones nested inside them
(e.g. a hand inside an arm) stay clickable → click a region → visual
operation gallery (emoji + label, never plain text) → select one →
**Generate preview** (real
SAM2 + Qwen Image Edit via ComfyUI, ~25-30s) → Before/After comparison →
**Accept** (the session's image advances; a second edit is applied on top of
this result, not the original — right hand→peace and left hand→thumbs-up
coexist in the same photo) or **Discard** (no changes).

## Docker

```powershell
copy .env.example .env
docker compose up --build
```

This spins up **three** containers — frontend, backend, and **ComfyUI
itself** (vanilla clone, no custom nodes — see
[docs/architecture.md](docs/architecture.md)). You don't need ComfyUI
installed on the host for this to work: that's precisely the point of
containerizing it, so cloning this repo and running one command is enough.

- Frontend at `http://localhost:5180`, backend at `http://localhost:8420`,
  **ComfyUI's own UI at `http://localhost:8188`** (useful for inspecting the
  graph/queue directly).
- First start: the `comfyui` container downloads ~15GB of models (Qwen Image
  Edit + LoRA + text encoder + VAE) into a named volume (`comfyui_data`) —
  takes several minutes depending on your bandwidth, but only the first
  time; subsequent starts are instant.
- The backend runs with GPU access (`deploy.resources.reservations` in
  `docker-compose.yml`) for SAM2; ComfyUI also requests it for Qwen Image
  Edit. If your machine doesn't have Docker's `nvidia` runtime configured,
  remove those `deploy` blocks from both services and set
  `SEGMENTATION_DEVICE=cpu` in `.env` (editing via ComfyUI will be much
  slower without a GPU).
- `COMFYUI_BASE_URL` inside the backend container points by default at
  `http://comfyui:8188` (the service's name on Compose's internal network).
  If you'd rather keep using a native ComfyUI install (e.g. with your own
  custom nodes), uncomment the `COMFYUI_BASE_URL=
  http://host.docker.internal:8188` line in `.env` — in that case the
  `comfyui` container still starts up, but the backend simply doesn't use
  it.
- YOLO weights are optionally reused by mounting `COMFYUI_MODELS_DIR` (from a
  native install, if you have one) as a read-only volume; if it's not
  configured or the file isn't there, the backend downloads them itself from
  Hugging Face — never a hard requirement.
- Data (SQLite + images), the SAM2/MediaPipe cache, and ComfyUI's models
  persist in named volumes (`backend_data`, `models_cache`, `comfyui_data`) —
  they survive `docker compose down` (not `docker compose down -v`).

## Structure

See the full tree and the reasoning behind each folder in
[docs/architecture.md](docs/architecture.md). Summary:

```
backend/app/{domain,application,adapters,infrastructure}/
frontend/src/{domain,application,adapters,infrastructure,presentation}/
```

Domain and Application don't import FastAPI, SQLAlchemy, PyTorch, ComfyUI,
React, or `fetch` — only Adapters/Infrastructure (backend) and
Adapters/Infrastructure (frontend) do.
