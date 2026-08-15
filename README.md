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
| 3 | Detección de cara/manos (YOLOv8 + SAM2 en el backend) | ⏳ próximo |
| 4 | Catálogo visual de operaciones | ✅ backend listo · frontend pendiente de UI de selección |
| 5 | Edición localizada vía ComfyUI + composición | ⏳ pendiente |
| 6 | Golden dataset / evaluación | ⏳ pendiente |

Todo lo que está "✅" tiene tests (unitarios + integración) en verde y fue
verificado además contra un servidor real (`uvicorn` + `curl`, y `vite build`).

## Requisitos

- **Backend**: Python 3.12 (ya instalado en
  `C:\Users\diego\AppData\Local\Programs\Python\Python312`). El proyecto usa
  un venv propio en `backend/.venv`, no el Python 3.14 por defecto del
  sistema (mejor compatibilidad con las librerías de ML que llegarán en la
  Fase 3).
- **Frontend**: Node.js (v24 ya instalado) + npm.
- **ComfyUI**: tu instalación local en `http://127.0.0.1:8188` — necesaria a
  partir de la Fase 5 (edición). No hace falta para lo que ya está construido.

## Backend

```powershell
cd backend
py -3.12 -m venv .venv          # solo la primera vez
./.venv/Scripts/pip install -e ".[dev]"
./.venv/Scripts/uvicorn app.main:app --reload --port 8000
```

- API en `http://127.0.0.1:8000`, docs interactivas en `/docs`.
- Base de datos SQLite en `backend/data/app.db` (se crea sola). Imágenes en
  `backend/data/images/{original,mask,preview,final}/`.
- Tests: `./.venv/Scripts/pytest` (todos son rápidos y no requieren ComfyUI
  ni GPU; el único test marcado `live_comfyui` — aún no añadido — se saltará
  por defecto cuando llegue).

Endpoints disponibles hoy:

- `POST /images` — sube una imagen (multipart `file`), devuelve
  `{image_id, width, height, url}`.
- `GET /static/{storage_ref}` — sirve los bytes de una imagen guardada.
- `GET /regions/{region_type}/operations` — catálogo de operaciones válidas
  para un tipo de región (p. ej. `right_hand` → saludar/paz/pulgar/puño).

## Frontend

```powershell
cd frontend
npm install
npm run dev      # http://localhost:5173
npm test         # vitest
npm run build    # type-check + build de producción
```

Por defecto apunta a `http://127.0.0.1:8000` (backend). Para cambiarlo, copia
`.env.example` a `.env.local` y ajusta `VITE_API_BASE_URL`.

Hoy el flujo cubre: subir una imagen → verla renderizada. La detección de
regiones, el overlay seleccionable y la galería de operaciones se activan en
las próximas fases (el backend de operaciones ya existe; falta la pantalla
que lo consuma).

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
