# Architecture

## Principle

- **Domain** — qué es verdad en el negocio (entidades, value objects, reglas
  puras). Cero imports de FastAPI, SQLAlchemy, PyTorch, ComfyUI, OpenCV, SAM,
  Hugging Face, LangGraph o cualquier SDK externo.
- **Application** — qué puede hacer la app (casos de uso orquestando Ports).
  Mismas restricciones que Domain.
- **Adapters** — cómo entra y sale información (HTTP, persistencia SQL,
  traducción de resultados de visión/edición a entidades de dominio).
- **Infrastructure** — cómo se implementa técnicamente cada cosa (clientes
  HTTP concretos, modelos de ML, engine de base de datos, configuración).

Las dependencias siempre apuntan hacia adentro: Infrastructure → Adapters →
Application → Domain, nunca al revés.

## Backend

```
app/
  domain/
    entities/        Image, DetectedRegion, Mask, Edit, EditSession
    value_objects/    BoundingBox, RegionType, EditOperation
    ports/            image_repository, image_storage, image_detector,
                       image_segmenter, image_editor, image_compositor
    services/          region_operation_rules.py — qué operaciones son
                       válidas para qué tipo de región (regla de negocio)
  application/
    use_cases/         upload_image, analyze_image, get_detected_regions,
                       list_operations_for_region, edit_region,
                       confirm_edit, discard_edit
    dto/               objetos planos de entrada/salida de cada caso de uso
    ports/              agent_orchestrator.py — puerto reservado, sin
                       implementación (ver "Agentes" más abajo)
  adapters/
    http/               controllers (FastAPI routers) + schemas (Pydantic)
    persistence/         SqlAlchemyImageRepository — traduce entidades de
                       dominio ↔ tablas SQLModel
    vision/              YoloImageDetector, Sam2ImageSegmenter — traducen
                       salida cruda de YOLO/SAM2 a DetectedRegion/Mask
    image_editing/         ComfyUIImageEditor — sube el crop, corre el
                       workflow, reescala la salida al tamaño del crop
    imaging/               PillowImageCompositor — crece/difumina la
                       máscara y compone; es quien garantiza "sin costuras"
  infrastructure/
    vision/               device.py, model_registry.py, YoloDetector,
                       Sam2MaskPredictor — wrappers crudos de
                       Ultralytics/SAM2, sin saber nada de Domain
    image_editing/comfyui/ client.py (HTTP real, sin WS — polling sobre
                       /history), workflow.py (carga la plantilla JSON y
                       sustituye parámetros), workflows/qwen_edit.json,
                       operation_prompts.py (EditOperation → instrucción)
    storage/              FilesystemImageStorage
    database/             engine, modelos SQLModel, init_db
    config/               settings.py — única fuente de variables de entorno
  main.py                composition root: construye adapters, los inyecta
                       en los casos de uso, monta los routers
```

`backend/Dockerfile`, `frontend/Dockerfile` y `docker-compose.yml` (raíz)
despliegan ambos servicios — ver la sección "Docker" más abajo.

### Por qué existe `ImageCompositor` (no estaba en el árbol original)

Componer píxeles requiere una librería de imágenes, y Domain/Application no
pueden depender de ninguna. La *regla* ("fuera de la máscara, todo debe
quedar igual, con un borde difuminado") es expresable en términos de
Application; la *implementación* (Pillow/numpy) vive detrás de este Port en
Adapters/Infrastructure — igual que `ImageEditor`. Este Port es lo que
garantiza "sin costuras" con código propio, no con la esperanza de que Qwen
preserve el resto de la imagen por sí solo.

### `EditSession` — por qué las ediciones no se destruyen entre sí

`EditSession.current_image_ref` empieza apuntando a la imagen original. Cada
`Edit` guarda `source_image_ref` (sobre qué imagen se aplicó) y, al
confirmarse, su `final_ref` se convierte en el nuevo `current_image_ref` de
la sesión. Así, "mano derecha → paz" seguido de "boca → sonrisa" aplica la
segunda edición sobre el resultado de la primera, no sobre el original.
Descartar una edición no toca la sesión en absoluto.

### Detección/segmentación: stack propio en el backend, no vía ComfyUI

Decisión explícita del usuario. Trade-off: backend y ComfyUI comparten una
sola GPU (RTX 5080, 16GB). Mitigación en `infrastructure/config/settings.py`:

- `detection_device` (YOLOv8n cara/mano) por defecto `cpu` — modelo diminuto,
  rápido, sin huella de VRAM.
- `segmentation_device` (SAM2) por defecto `cuda` por calidad, pero se libera
  (`torch.cuda.empty_cache()`) inmediatamente después de cada `analyze`, así
  hay VRAM libre cuando ComfyUI cargue Qwen Image Edit más adelante en el
  flujo.
- Los pesos YOLO se reutilizan directamente desde
  `C:\ComfyUI\models\ultralytics\bbox\{face,hand}_yolov8n.pt` (mismo
  formato, sin descarga duplicada). El checkpoint de SAM2 en ComfyUI está
  empaquetado en `.safetensors` para su propio nodo, incompatible con el
  paquete oficial `sam2` de pip — el backend descarga/cachea su propia copia
  vía Hugging Face Hub (`facebook/sam2-hiera-base-plus`) la primera vez.

**Verificado, no solo implementado**: `torch==2.10.0+cu130` (idéntico al
build que usa ComfyUI) reconoce la RTX 5080 (`compute capability (12, 0)`,
Blackwell). Contra una foto real: `YoloImageDetector` detectó cara + ambas
manos con confianzas 0.87/0.75/0.56 y la heurística izquierda/derecha las
asignó correctamente; `Sam2ImageSegmenter`, alimentado con la caja de la
cara detectada, produjo una máscara real recortada al contorno de pelo/cara
(no un rectángulo) en ~16s incluyendo la descarga del checkpoint. La API
real de `sam2` (no adivinada) se confirmó leyendo
`sam2/sam2_image_predictor.py` y `sam2/build_sam.py` del paquete instalado:
`SAM2ImagePredictor.from_pretrained(model_id, device=...)` →
`predictor.set_image(rgb_ndarray)` → `predictor.predict(box=xyxy_array,
multimask_output=False)`. El checkpoint se descarga vía
`huggingface_hub.hf_hub_download`, cuya ubicación de cache solo se controla
con la variable de entorno `HF_HOME` (no hay parámetro `cache_dir` en la
cadena de llamadas) — de ahí que `Sam2MaskPredictor` fije `HF_HOME` en vez
de pasar un kwarg.

**Heurística izquierda/derecha**: `hand_yolov8n.pt` detecta "una mano", sin
lateralidad. Con dos manos, la más a la izquierda en pantalla se asigna como
la derecha del sujeto (convención espejo) y viceversa; con una sola, se
compara su centro contra el punto medio horizontal de la imagen. Documentado
como limitación conocida en
`adapters/vision/yolo_sam2_image_detector.py::_assign_hand_sides` —
mejorarlo (p. ej. con un modelo de pose que dé lateralidad real por
muñeca/codo) es un cambio contenido a esa función.

### ComfyUI — API real (no inventada)

Confirmada leyendo el `server.py` real de la instalación local
(`C:\Users\diego\AppData\Local\Programs\ComfyUI\resources\ComfyUI\server.py`):

```
POST /prompt            encolar un workflow (API-format, no el formato UI
                         con subgrafos)
GET  /history/{id}      resultado + posibles node_errors
GET  /queue              estado de la cola
POST /upload/image        subir imagen de entrada
GET  /view?filename=…&subfolder=…&type=…   descargar un resultado
GET  /object_info[/{clase}]  esquema de cada nodo instalado
GET  /system_stats        info de GPU/VRAM
POST /interrupt            cancelar la ejecución en curso
GET  /ws?clientId=…        progreso en tiempo real (opcional; el cliente
                         MVP usa polling sobre /history)
```

Modelos ya instalados y confirmados en disco: `qwen_image_edit_2511_fp8mixed.safetensors`
+ LoRA Lightning de 4 pasos + `qwen_2.5_vl_7b_fp8_scaled` (encoder) +
`qwen_image_vae`.

### El grafo de edición — por qué NO usa nodos de inpainting

`infrastructure/image_editing/comfyui/workflows/qwen_edit.json` es el
workflow real (formato API, verificado nodo por nodo contra `/object_info`
y contra la ejecución real, no adivinado): `LoadImage` →
`FluxKontextImageScale` → (`TextEncodeQwenImageEditPlus` × 2,
positivo/negativo, cada uno seguido de `FluxKontextMultiReferenceLatentMethod`)
+ `VAEEncode` → `UNETLoader` → `ModelSamplingAuraFlow` → `CFGNorm` →
`LoraLoaderModelOnly` (LoRA Lightning 4 pasos) → `KSampler` → `VAEDecode` →
`SaveImage`. Es el mismo grafo que el workflow de referencia que trae el
propio checkpoint (`image_qwen_image_edit_2511.json`), sin las ramas de
imagen2/imagen3 (reservadas para una futura imagen de referencia por
gesto).

Deliberadamente **no** usa `InpaintModelConditioning`/`VAEEncodeForInpaint`
(nodos de inpainting clásico): Qwen Image Edit es un editor por
instrucciones, no una UNet con canal de máscara dedicado — la imagen de
referencia se inyecta vía el *text encoder* (`TextEncodeQwenImageEditPlus`),
no vía una máscara en el grafo. `ComfyUIImageEditor` le manda a ComfyUI el
**crop completo** (región + margen de contexto, sin máscara) con la
instrucción en texto, y dejar que Qwen edite todo el crop; la máscara nunca
entra al grafo de ComfyUI. Quien impone "solo cambia lo seleccionado" es
`PillowImageCompositor`, después, con la máscara real — exactamente la regla
que pedía el enunciado original ("no asumir que Qwen preservará el resto
por sí solo").

### Máscara: por qué hay que *crecer* la máscara antes de componer

Primer intento en vivo: mano cerrada → "señal de paz". Resultado: dedos
"fantasma", semitransparentes, en vez de un gesto limpio. Causa: la máscara
de SAM2 sigue el contorno del **puño original**; los dedos extendidos del
nuevo gesto caen fuera de ese contorno, así que la composición los recorta
(o los deja a medias por el difuminado del borde). `Mask.grow_px` ya existía
en la entidad pero no se aplicaba a ningún píxel — era metadata muerta.

Arreglo: `ImageCompositor.composite()` ahora recibe `grow_px` y
`PillowImageCompositor` dilata la máscara (`ImageFilter.MaxFilter`) antes de
difuminarla (`GaussianBlur`). `EditRegionUseCase` usa
`DEFAULT_MASK_GROW_PX = 40` (antes 8) — generoso a propósito, porque una
edición puede cambiar la silueta de la región (un puño abriéndose en mano
extendida ocupa más espacio que el puño). Verificado: el mismo caso (puño →
paz) con el fix da un gesto limpio, sin fantasmas; la mano izquierda, la
cara, el pelo y la ropa quedan intactos. Queda un ligero suavizado residual
donde la mano cruza mechones de pelo — aceptable para el MVP, ajustable
subiendo `grow_px` u otro enfoque (máscara consciente de bordes) si hace
falta más adelante.

### Resolución: la salida de Qwen no es del tamaño del crop

Qwen Image Edit devuelve la imagen en su propia resolución preferida, no
necesariamente la del crop enviado. `ComfyUIImageEditor` reescala el
resultado de vuelta al tamaño exacto de `region_box_used` (Lanczos) antes de
devolverlo — así `PillowImageCompositor` nunca necesita saber nada sobre la
resolución interna del modelo, solo trabaja con píxeles que ya coinciden
con la máscara recortada.

### Persistencia

SQLite para el MVP (`backend/data/app.db`), vía SQLModel. El Port
`ImageRepository` es el único contrato que Application conoce; migrar a
Postgres más adelante es cambiar `database_url` en `Settings` y la
construcción del engine en `infrastructure/database/engine.py` — ningún otro
archivo cambia.

### Agentes / LangGraph

`application/ports/agent_orchestrator.py` define el contrato
(`AgentOrchestrator.suggest_edit(...)`) pero **no tiene implementación ni
está conectado a nada**. El flujo determinista (upload → analyze → select
region → select operation → edit → composite) funciona sin ningún LLM. Si en
el futuro un agente aporta valor real, su implementación (LangGraph, Google
ADK, un loop propio) vive enteramente en Infrastructure detrás de este Port,
igual que cualquier otro adapter.

## Frontend

```
src/
  domain/         entities (UploadedImage, Region), value-objects
                  (BoundingBox), types (RegionType, EditOperation — reflejan
                  los enums del backend, sin metadata de presentación)
  application/     use-cases (uploadImage, analyzeImage,
                  listOperationsForRegion, …) + ports (ImageApiPort — sin
                  fetch)
  adapters/        http/HttpImageApi (implementa ImageApiPort, el único
                  módulo que conoce el JSON snake_case del backend) +
                  ui/regionPresentation.ts (región → label/color; separado
                  del type puro en domain/types)
  infrastructure/  api/httpClient (el único lugar que conoce la URL base y
                  maneja errores HTTP) + state/EditSessionContext (Context +
                  reducer — suficiente para un flujo lineal, sin Redux)
  presentation/    components/ (ImageUploader, RegionOverlay,
                  OperationGallery, ui/ — primitivas shadcn) + lib/utils.ts
                  (cn(), generado por shadcn) + pages/ (EditorPage) +
                  hooks/useEditSession (lo único que los componentes llaman)
```

Regla reforzada por la estructura: componente → hook → caso de uso →
port → adapter (`adapters/http`, usando `infrastructure/api`). Ningún
componente importa `fetch` ni conoce una ruta del backend directamente.

### shadcn/ui

Componentes generados con `npx shadcn@latest add <nombre>` (Radix +
Tailwind v4, estilo "Nova"). `components.json` (raíz de `frontend/`) tiene
sus `aliases` reconfigurados para que caigan dentro de la estructura
hexagonal en vez de las rutas por defecto de shadcn:

```json
"aliases": {
  "components": "@/presentation/components",
  "utils": "@/presentation/lib/utils",
  "ui": "@/presentation/components/ui",
  "lib": "@/presentation/lib",
  "hooks": "@/presentation/hooks"
}
```

`RegionOverlay` (cajas coloreadas y clicables sobre la imagen,
posicionadas en porcentaje respecto a `imageWidth`/`imageHeight` — se
mantienen alineadas a cualquier tamaño de render sin `ResizeObserver`) y
`OperationGallery` (grid de `Card` con emoji + etiqueta, nunca texto plano)
son componentes propios sobre las primitivas de `presentation/components/ui/`.
Verificados visualmente extremo a extremo (Playwright headless contra el
stack real en Docker: subir foto real → `Analizar imagen` → cajas de
región correctamente alineadas sobre cara/mano-izq./mano-der. → clic en una
región → galería con emoji reales del backend → clic en una operación →
tarjeta de confirmación).

## Testing

- `backend/tests/unit/domain/` — BoundingBox, reglas región↔operación,
  transiciones de `Edit`. Sin mocks, lógica pura.
- `backend/tests/unit/application/` — casos de uso contra
  `tests/unit/application/fakes.py` (implementaciones en memoria de cada
  Port). Sirven además como documentación viva de cada contrato.
- `backend/tests/integration/` — `SqlAlchemyImageRepository` contra SQLite
  real (tmp file) y la API completa vía `TestClient` con
  `dependency_overrides` para aislar storage/DB por test.
- `backend/tests/unit/adapters/` — `YoloImageDetector` (heurística
  izquierda/derecha, traducción a `DetectedRegion`) contra dobles de prueba
  con la misma interfaz que `YoloDetector`; nada de torch/ultralytics real,
  corre en milisegundos.
- `backend/tests/unit/adapters/test_pillow_image_compositor.py` — la
  garantía "fuera de la máscara, todo igual" a nivel de píxel (numpy), y el
  caso concreto que reprodujo el bug real de los "dedos fantasma"
  (máscara sin crecer vs. creciéndola).
- `backend/tests/unit/infrastructure/` — la plantilla del workflow Qwen
  (sustitución de placeholders, números vs strings, referencias de nodo
  válidas) y que cada `EditOperation` tiene un prompt.
- `backend/tests/integration/test_edits_api.py` — `/images/{id}/edits`,
  `/edits/{id}/confirm|discard` vía `TestClient`, con los mismos fakes de
  detector/segmentador/editor que los tests de aplicación más el
  `PillowImageCompositor` real (rápido, sin GPU) para cobertura genuina de
  la composición de píxeles.
- `backend/tests/integration/test_vision_live.py` — opt-in
  (`pytest -m live_models`), contra los modelos YOLO/SAM2 reales.
- `backend/tests/integration/test_comfyui_edit_live.py` — opt-in
  (`pytest -m live_comfyui`), contra el ComfyUI + Qwen Image Edit reales.
  Ninguno de los dos corre por defecto (`addopts` en `pyproject.toml` los
  excluye).
- `frontend/src/**/*.test.{ts,tsx}` — `HttpImageApi` con `fetch` mockeado
  (incluye `requestEdit`/`confirmEdit`/`discardEdit`), `EditorPage` con un
  `FakeImageApiPort` inyectado en el Context (cubre el flujo completo:
  subir → analizar → seleccionar región → seleccionar operación → generar
  vista previa → aceptar/descartar, incluyendo que cambiar de región u
  operación limpia cualquier vista previa anterior, y que aceptar actualiza
  la imagen mostrada y deja la región lista para una segunda edición).

## Docker

`docker-compose.yml` (raíz) construye dos imágenes:

- **backend** (`backend/Dockerfile`): `python:3.12-slim` — no una imagen
  `nvidia/cuda`, porque las wheels `cu130` de PyTorch traen su propio
  runtime CUDA como dependencias pip; solo hace falta que el host exponga la
  GPU al contenedor. `torch`/`torchvision` se instalan **antes** que el
  resto (mismo pin `cu130` que en nativo) para que el `torch` sin pinear que
  piden `ultralytics`/`sam2` como dependencia no lo reemplace por una build
  sin soporte para esta GPU. Acceso a GPU vía
  `deploy.resources.reservations.devices` (Compose Spec, funciona con
  `docker compose up` normal, sin swarm) — confirmado funcionando en esta
  máquina (`docker run --gpus all ... nvidia-smi` ve la RTX 5080).
- **frontend** (`frontend/Dockerfile`): build multi-stage, `node:20-alpine`
  → `nginx:1.27-alpine` sirviendo el `dist/` estático.
  `VITE_API_BASE_URL` se pasa como build-arg (las env vars de Vite son de
  compile-time) con la URL que el *navegador* debe usar — el puerto del
  host, no el interno del contenedor.

Puntos que cambian entre nativo y Docker (ambos vía env, ningún código
distinto):

- `COMFYUI_BASE_URL`: `127.0.0.1:8188` nativo →
  `host.docker.internal:8188` en Docker (dentro de un contenedor,
  `127.0.0.1` se refiere al propio contenedor).
- Pesos YOLO: rutas de Windows nativo → `COMFYUI_MODELS_DIR` del host
  montado de solo lectura en `/comfyui_models` dentro del contenedor.
- Persistencia: `backend/data/` nativo → volúmenes con nombre
  (`backend_data`, `models_cache`) para que sobrevivan a
  `docker compose down`.
- Puertos: `8420`/`5180` en ambos casos — elegidos porque `8000`/`5173`
  (los defaults de FastAPI/Vite) ya están en uso por otro proyecto en esta
  máquina; configurables en el `.env` de la raíz.

## Próximos pasos (no implementados todavía)

1. **Boca/Ojos**: `RegionType` y el catálogo de operaciones ya los
   contemplan; falta conectar un detector (candidato:
   `MediaPipeFaceLandmarker`, ya instalado en ComfyUI, o su equivalente en
   `mediapipe` directamente en el backend).
2. **Golden dataset**: `tests/evaluation/{datasets,evaluators}` con
   `region_preservation.py` real (diff numpy/PIL fuera de la máscara);
   `edit_quality`/`identity_preservation` como interfaces documentadas.
3. **Afinar la máscara crecida**: `DEFAULT_MASK_GROW_PX=40` es un valor
   único para todo tipo de región; un valor por `RegionType` (o por
   `EditOperation`, ya que "puño→paz" necesita más margen que "sonrisa
   cerrada→sonrisa") daría mejores bordes sin crecer de más regiones que no
   lo necesitan.
4. **Imagen de referencia por gesto**: el Port `ImageEditor.edit()` ya
   acepta `reference_image_png_bytes` y el workflow ya tiene los campos
   `image2`/`image3` de `TextEncodeQwenImageEditPlus` disponibles — hoy no
   se usan porque el prompt de texto solo ya da buenos resultados.
