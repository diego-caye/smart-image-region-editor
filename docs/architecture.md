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
    vision/              (Fase 3) traduce salida cruda de YOLO/SAM2 a
                       DetectedRegion/Mask
    image_editing/        (Fase 5) ComfyUIImageEditor — traduce EditOperation
                       a un workflow de ComfyUI
    imaging/              (Fase 5) PillowImageCompositor
  infrastructure/
    vision/               (Fase 3) wrappers crudos de Ultralytics/SAM2
    image_editing/comfyui/ (Fase 5) cliente HTTP/WS real de ComfyUI +
                       plantillas de workflow + tabla operación→prompt
    storage/              FilesystemImageStorage
    database/             engine, modelos SQLModel, init_db
    config/               settings.py — única fuente de variables de entorno
  main.py                composition root: construye adapters, los inyecta
                       en los casos de uso, monta los routers
```

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
`qwen_image_vae`. Nodos relevantes verificados vía `/object_info`:
`TextEncodeQwenImageEditPlus`, `InpaintModelConditioning`,
`VAEEncodeForInpaint`, `GrowMask`, `FeatherMask`, `ImageCropByMaskAndResize`,
`ImageCompositeMasked`.

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
                  los enums del backend)
  application/     use-cases (uploadImage, listOperationsForRegion, …) +
                  ports (ImageApiPort — sin fetch)
  adapters/        http/HttpImageApi (implementa ImageApiPort, el único
                  módulo que conoce el JSON snake_case del backend) +
                  ui/ (mappers de presentación, p. ej. región → color)
  infrastructure/  api/httpClient (el único lugar que conoce la URL base y
                  maneja errores HTTP) + state/EditSessionContext (Context +
                  reducer — suficiente para un flujo lineal, sin Redux)
  presentation/    components/ (ImageUploader, …) + pages/ (EditorPage) +
                  hooks/useEditSession (lo único que los componentes llaman)
```

Regla reforzada por la estructura: componente → hook → caso de uso →
port → adapter (`adapters/http`, usando `infrastructure/api`). Ningún
componente importa `fetch` ni conoce una ruta del backend directamente.

## Testing

- `backend/tests/unit/domain/` — BoundingBox, reglas región↔operación,
  transiciones de `Edit`. Sin mocks, lógica pura.
- `backend/tests/unit/application/` — casos de uso contra
  `tests/unit/application/fakes.py` (implementaciones en memoria de cada
  Port). Sirven además como documentación viva de cada contrato.
- `backend/tests/integration/` — `SqlAlchemyImageRepository` contra SQLite
  real (tmp file) y la API completa vía `TestClient` con
  `dependency_overrides` para aislar storage/DB por test.
- `frontend/src/**/*.test.{ts,tsx}` — `HttpImageApi` con `fetch` mockeado,
  `EditorPage` con un `FakeImageApiPort` inyectado en el Context.

## Próximos pasos (no implementados todavía)

1. **Detección** (`adapters/vision`, `infrastructure/vision`): YOLOv8 cara/mano
   + SAM2 para máscaras precisas. Requiere instalar `torch` con un índice
   compatible con RTX 5080 (Blackwell, `sm_120`) — un `pip install torch`
   normal puede resolver una build sin soporte para esta GPU.
2. **Edición localizada** (`infrastructure/image_editing/comfyui`,
   `adapters/image_editing`, `adapters/imaging`): cliente ComfyUI real,
   plantilla de workflow API-format basada en `TextEncodeQwenImageEditPlus`
   + `InpaintModelConditioning`, y `PillowImageCompositor`.
3. **Boca/Ojos**: `RegionType` y el catálogo de operaciones ya los
   contemplan; falta conectar un detector (candidato:
   `MediaPipeFaceLandmarker`, ya instalado en ComfyUI, o su equivalente en
   `mediapipe` directamente en el backend).
4. **Golden dataset**: `tests/evaluation/{datasets,evaluators}` con
   `region_preservation.py` real (diff numpy/PIL fuera de la máscara);
   `edit_quality`/`identity_preservation` como interfaces documentadas.
