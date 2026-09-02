# Smart Image Region Editor

Sube una foto, el sistema detecta regiones (cara, manos — boca/ojos preparados
para más adelante), seleccionas visualmente una región y una transformación
predefinida ("✌️ Señal de paz"), y solo esa región cambia — el resto de la
imagen se conserva. Arquitectura hexagonal (Ports & Adapters) en backend y
frontend. Ver [docs/architecture.md](docs/architecture.md) para las
decisiones de diseño y su porqué.

## Estado actual

| Fase | Qué incluye | Estado |
|---|---|---|
| 0 | Scaffolding, estructura hexagonal, git | ✅ |
| 1–2 | Domain + Application completos, subida de imagen, persistencia (SQLite) | ✅ |
| 3 | Detección de cara/manos (YOLOv8) + máscara precisa (SAM2), en el backend | ✅ |
| 3b | Frontend: overlay de regiones seleccionables + galería visual de operaciones (shadcn/ui) | ✅ |
| 4 | Catálogo visual de operaciones | ✅ |
| 5 | Edición localizada vía ComfyUI + composición, extremo a extremo (backend + frontend) | ✅ |
| 6 | Golden dataset / evaluación | ✅ andamiaje + `region_preservation` real · `edit_quality`/`identity_preservation` son stubs documentados |
| — | Despliegue en Docker (backend + frontend, GPU) | ✅ |
| — | Extender a boca/ojos/cuerpo | ⏳ pendiente (siguiente paso natural) |

Todo lo que está "✅" tiene tests (unitarios + integración) en verde y fue
verificado además contra procesos reales corriendo (`uvicorn`/`docker
compose` + `curl`, detección real sobre una foto real, y `vite build`).

**Puertos**: este proyecto usa `8420` (backend) y `5180` (frontend) en vez de
los típicos `8000`/`5173`, porque esos ya están en uso por otro proyecto en
esta máquina. ComfyUI sigue en su puerto habitual, `8188`.

## Requisitos

- **Backend**: Python 3.12 (ya instalado en
  `C:\Users\diego\AppData\Local\Programs\Python\Python312`). El proyecto usa
  un venv propio en `backend/.venv`, no el Python 3.14 por defecto del
  sistema (mejor compatibilidad con torch/ultralytics/sam2).
- **Frontend**: Node.js (v24 ya instalado) + npm.
- **ComfyUI**: tu instalación local en `http://127.0.0.1:8188` — necesaria a
  partir de la Fase 5 (edición). No hace falta para detección/subida.
- **GPU**: RTX 5080 (Blackwell). El backend usa exactamente el mismo build de
  PyTorch que ComfyUI (`torch==2.10.0+cu130`) — instalarlo desde el índice
  normal de PyPI instalaría una build sin soporte para esta GPU.
- **Docker** (opcional, para el despliegue): Docker Desktop con el runtime
  `nvidia` habilitado — ya verificado en esta máquina
  (`docker run --gpus all ... nvidia-smi` funciona).

## Backend (nativo)

```powershell
cd backend
py -3.12 -m venv .venv          # solo la primera vez
copy .env.example .env          # y ajusta si hace falta

./.venv/Scripts/pip install -e ".[dev]"
# Detección/segmentación (Fase 3) — build de PyTorch pineada para RTX 5080:
./.venv/Scripts/pip install "torch==2.10.0+cu130" "torchvision==0.25.0+cu130" --index-url https://download.pytorch.org/whl/cu130
./.venv/Scripts/pip install -e ".[ml]"

./.venv/Scripts/uvicorn app.main:app --reload --port 8420
```

- API en `http://127.0.0.1:8420`, docs interactivas en `/docs`.
- Base de datos SQLite en `backend/data/app.db` (se crea sola). Imágenes en
  `backend/data/images/{original,mask,preview,final}/`. Checkpoint de SAM2
  cacheado en `backend/models_cache/` (se descarga solo la primera vez,
  ~300MB, desde Hugging Face — el `.safetensors` de ComfyUI no sirve aquí
  porque su nodo lo carga con un loader distinto al paquete oficial `sam2`).
- Tests: `./.venv/Scripts/pytest` — rápidos, no requieren GPU/modelos/ComfyUI
  por defecto. Para correr también los que sí los requieren:
  `./.venv/Scripts/pytest -m live_models` (YOLO+SAM2 reales) o
  `./.venv/Scripts/pytest -m live_comfyui` (Qwen Image Edit real).

Endpoints disponibles hoy:

- `POST /images` — sube una imagen (multipart `file`), devuelve
  `{image_id, width, height, url}`.
- `POST /images/{id}/analyze` — corre detección real (YOLOv8 cara+manos) y
  persiste las regiones encontradas.
- `GET /images/{id}/regions` — relee las regiones ya detectadas.
- `GET /regions/{region_type}/operations` — catálogo de operaciones válidas
  para un tipo de región (p. ej. `right_hand` → saludar/paz/pulgar/puño).
- `POST /images/{id}/edits` — `{region_id, operation}` → edición localizada
  real (SAM2 + Qwen Image Edit vía ComfyUI + composición), devuelve un
  preview sin tocar la imagen "oficial" todavía. ~25-30s por edición.
- `POST /edits/{id}/confirm` — el preview pasa a ser la imagen actual de la
  sesión; la siguiente edición se aplica sobre este resultado, no sobre el
  original.
- `POST /edits/{id}/discard` — descarta el preview, la sesión no cambia.
- `GET /static/{storage_ref}` — sirve los bytes de una imagen guardada.

### Golden dataset / evaluación

`backend/tests/evaluation/`:

- `evaluators/region_preservation.py` — real: mide en píxeles si todo lo de
  fuera de la máscara quedó igual entre el original y el final. Tiene sus
  propios tests unitarios (sintéticos, sin GPU) y el runner del golden
  dataset lo usa contra ediciones reales.
- `evaluators/edit_quality.py`, `evaluators/identity_preservation.py` —
  stubs documentados (`NotImplementedError` con el enfoque previsto en el
  docstring), no bloquean el MVP.
- `datasets/golden_{hand,face,mouth}_edits.json` — vacíos a propósito: el
  esquema y el runner (`test_golden_dataset.py`, opt-in vía
  `pytest -m live_comfyui`) están listos, pero las fotos reales para
  poblarlos no se suben al repo sin consentimiento — ver
  `datasets/README.md` para el esquema y cómo añadir las tuyas localmente
  (`datasets/images/`, ya en `.gitignore`).

## Frontend (nativo)

```powershell
cd frontend
npm install
npm run dev      # http://localhost:5180
npm test         # vitest
npm run build    # type-check + build de producción
```

Por defecto apunta a `http://127.0.0.1:8420` (backend). Para cambiarlo, copia
`.env.example` a `.env.local` y ajusta `VITE_API_BASE_URL`.

UI construida con [shadcn/ui](https://ui.shadcn.com) (Radix + Tailwind v4) —
componentes generados en `src/presentation/components/ui/` vía
`npx shadcn@latest add <componente>` (el `components.json` de la raíz ya
apunta los alias `@/presentation/...` a la estructura hexagonal del
proyecto, no a las rutas por defecto de shadcn).

El flujo completo funciona extremo a extremo: subir imagen → **Analizar
imagen** (detección real YOLOv8) → overlay de cajas seleccionables sobre la
imagen (cara/mano izq./mano der., coloreadas) → click en una región →
galería visual de operaciones (emoji + etiqueta, nunca texto plano) →
seleccionar una → **Generar vista previa** (SAM2 + Qwen Image Edit real vía
ComfyUI, ~25-30s) → comparación Antes/Después → **Aceptar** (la imagen de la
sesión avanza; una segunda edición se aplica sobre este resultado, no sobre
el original — mano derecha→paz y mano izquierda→pulgar arriba conviven en la
misma foto) o **Descartar** (sin cambios).

## Docker

```powershell
copy .env.example .env          # ajusta COMFYUI_MODELS_DIR si tu ComfyUI no está en C:\ComfyUI
docker compose up --build
```

- Frontend en `http://localhost:5180`, backend en `http://localhost:8420`.
- El backend corre con acceso a la GPU (`deploy.resources.reservations` en
  `docker-compose.yml`) para SAM2; si tu máquina no tiene el runtime
  `nvidia` de Docker configurado, quita ese bloque y pon
  `SEGMENTATION_DEVICE=cpu` en `.env`.
- `COMFYUI_BASE_URL` dentro del contenedor apunta a
  `http://host.docker.internal:8188` (no a `127.0.0.1`, que dentro de un
  contenedor se referiría a sí mismo) — ya configurado en `.env.example`.
- Los pesos de YOLO se reutilizan montando `COMFYUI_MODELS_DIR` como
  volumen de solo lectura; no se descargan de nuevo dentro del contenedor.
- Datos (SQLite + imágenes) y el cache de SAM2 persisten en volúmenes con
  nombre (`backend_data`, `models_cache`) — sobreviven a
  `docker compose down` (no a `docker compose down -v`).

## Estructura

Ver el árbol completo y el razonamiento de cada carpeta en
[docs/architecture.md](docs/architecture.md). Resumen:

```
backend/app/{domain,application,adapters,infrastructure}/
frontend/src/{domain,application,adapters,infrastructure,presentation}/
```

Domain y Application no importan FastAPI, SQLAlchemy, PyTorch, ComfyUI, React
ni `fetch` — solo Adapters/Infrastructure (backend) y
Adapters/Infrastructure (frontend) lo hacen.
