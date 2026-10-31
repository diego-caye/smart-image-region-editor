"""Implements ImageEditor via a local ComfyUI server running Qwen Image
Edit. Crops the region with extra context, sends the WHOLE crop to Qwen (no
mask baked into the ComfyUI graph — Qwen Image Edit is an instruction-based
editor, not a mask-aware inpainting UNet), and resizes the result back to
the crop's exact pixel size so the compositor never needs to know about the
model's own output resolution. Localization to the mask is enforced
entirely by ImageCompositor, not by this adapter — see
docs/architecture.md.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from io import BytesIO

from PIL import Image as PILImage

from app.domain.ports.image_editor import EditorProgress, EditorStage, EditResult, ImageEditor
from app.domain.value_objects.bounding_box import BoundingBox
from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.garment_color import GarmentColor
from app.infrastructure.image_editing.comfyui.client import ComfyUIClient, NodeEvent
from app.infrastructure.image_editing.comfyui.operation_prompts import prompt_for
from app.infrastructure.image_editing.comfyui.workflow import (
    OUTPUT_NODE_ID,
    QwenEditParams,
    build_qwen_edit_prompt,
)


class ComfyUIImageEditor(ImageEditor):
    def __init__(
        self,
        client: ComfyUIClient,
        *,
        crop_context_margin_px: int,
        unet_name: str,
        clip_name: str,
        vae_name: str,
        lora_name: str,
        lora_strength: float,
        model_shift: float,
        cfg_norm_strength: float,
        steps: int,
        cfg: float,
        sampler_name: str,
        scheduler: str,
    ) -> None:
        self._client = client
        self._crop_context_margin_px = crop_context_margin_px
        self._unet_name = unet_name
        self._clip_name = clip_name
        self._vae_name = vae_name
        self._lora_name = lora_name
        self._lora_strength = lora_strength
        self._model_shift = model_shift
        self._cfg_norm_strength = cfg_norm_strength
        self._steps = steps
        self._cfg = cfg
        self._sampler_name = sampler_name
        self._scheduler = scheduler

    def edit(
        self,
        *,
        image_png_bytes: bytes,
        mask_png_bytes: bytes,
        region_box: BoundingBox,
        operation: EditOperation,
        color: GarmentColor | None = None,
        reference_image_png_bytes: bytes | None = None,
        on_progress: Callable[[EditorProgress], None] | None = None,
    ) -> EditResult:
        # reference_image_png_bytes (a future gesture/expression reference
        # photo) isn't wired into the workflow yet — it would map to the
        # TextEncodeQwenImageEditPlus node's image2 input; the prompt-only
        # path already produces good results (see docs/architecture.md).
        image = PILImage.open(BytesIO(image_png_bytes)).convert("RGB")
        crop_box = region_box.expanded(
            self._crop_context_margin_px, image_width=image.width, image_height=image.height
        )
        crop = image.crop(crop_box.as_xyxy())

        uploaded_filename = self._client.upload_image(
            _to_png_bytes(crop), filename="region_crop.png"
        )

        seed = random.randint(0, 2**32 - 1)
        prompt_text = prompt_for(operation, color)
        prompt_graph = build_qwen_edit_prompt(
            QwenEditParams(
                image_filename=uploaded_filename,
                prompt_text=prompt_text,
                seed=seed,
                unet_name=self._unet_name,
                clip_name=self._clip_name,
                vae_name=self._vae_name,
                lora_name=self._lora_name,
                lora_strength=self._lora_strength,
                model_shift=self._model_shift,
                cfg_norm_strength=self._cfg_norm_strength,
                steps=self._steps,
                cfg=self._cfg,
                sampler_name=self._sampler_name,
                scheduler=self._scheduler,
            )
        )

        result_bytes = self._client.run_prompt(
            prompt_graph,
            output_node_id=OUTPUT_NODE_ID,
            on_event=_progress_translator(on_progress) if on_progress else None,
        )

        # Qwen Image Edit outputs at its own preferred resolution, not
        # necessarily the crop's — resize back so the compositor can treat
        # edited_region_png_bytes as exactly crop_box-sized.
        result_image = PILImage.open(BytesIO(result_bytes)).convert("RGB")
        if result_image.size != crop.size:
            result_image = result_image.resize(crop.size, PILImage.LANCZOS)

        return EditResult(
            edited_region_png_bytes=_to_png_bytes(result_image),
            region_box_used=crop_box,
            seed=seed,
            model_metadata={
                "unet_name": self._unet_name,
                "lora_name": self._lora_name,
                "steps": self._steps,
                "cfg": self._cfg,
                "prompt": prompt_text,
                "color": color.value if color else None,
            },
        )


# Node classes of workflows/qwen_edit.json that mark a user-visible stage;
# the rest (LoadImage, scaling, VAEEncode, reference latents) take well
# under a second and aren't worth a label. The loader nodes are absent on
# purpose: measured on a real run they come back cached in ~0.3s, while the
# actual weight loading happens lazily inside the node that first uses a
# model — ~10s across the two text encoders, then ~30s inside KSampler
# before its first sampling step. Hence KSampler *starting* means
# "loading the model", and only its progress events mean "generating".
_STAGE_BY_NODE_CLASS = {
    "TextEncodeQwenImageEditPlus": EditorStage.READING_INSTRUCTION,
    "KSampler": EditorStage.LOADING_MODEL,
    "VAEDecode": EditorStage.DECODING,
}


def _progress_translator(
    on_progress: Callable[[EditorProgress], None],
) -> Callable[[NodeEvent], None]:
    def translate(event: NodeEvent) -> None:
        if event.step is not None:
            on_progress(EditorProgress(EditorStage.GENERATING, event.step, event.steps))
        elif (stage := _STAGE_BY_NODE_CLASS.get(event.class_type)) is not None:
            on_progress(EditorProgress(stage))

    return translate


def _to_png_bytes(image: PILImage.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
