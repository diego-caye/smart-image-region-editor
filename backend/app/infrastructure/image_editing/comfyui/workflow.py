"""Loads the Qwen Image Edit workflow template (API-format graph, verified
node-by-node against the real local ComfyUI — see docs/architecture.md) and
substitutes its parameters. The template is a plain JSON file precisely so
it can be replaced/reconfigured (a different graph entirely, if needed)
without touching this module's callers — Application never sees any of
this.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_TEMPLATE_PATH = Path(__file__).parent / "workflows" / "qwen_edit.json"
OUTPUT_NODE_ID = "save_image"


@dataclass(slots=True)
class QwenEditParams:
    image_filename: str
    prompt_text: str
    seed: int
    unet_name: str
    clip_name: str
    vae_name: str
    lora_name: str
    lora_strength: float
    model_shift: float
    cfg_norm_strength: float
    steps: int
    cfg: float
    sampler_name: str
    scheduler: str


def build_qwen_edit_prompt(params: QwenEditParams) -> dict:
    template_text = _TEMPLATE_PATH.read_text(encoding="utf-8")

    substitutions = {
        "__IMAGE_FILENAME__": params.image_filename,
        "__UNET_NAME__": params.unet_name,
        "__CLIP_NAME__": params.clip_name,
        "__VAE_NAME__": params.vae_name,
        "__LORA_NAME__": params.lora_name,
        "__LORA_STRENGTH__": params.lora_strength,
        "__MODEL_SHIFT__": params.model_shift,
        "__CFG_NORM_STRENGTH__": params.cfg_norm_strength,
        "__PROMPT_TEXT__": params.prompt_text,
        "__SEED__": params.seed,
        "__STEPS__": params.steps,
        "__CFG__": params.cfg,
        "__SAMPLER_NAME__": params.sampler_name,
        "__SCHEDULER__": params.scheduler,
    }
    for token, value in substitutions.items():
        # Replace the *quoted* placeholder with the value's own JSON
        # encoding — this is what correctly turns a string placeholder into
        # a bare number (e.g. "__SEED__" -> 42) while still safely
        # escaping string values (quotes, newlines) in the prompt text.
        template_text = template_text.replace(f'"{token}"', json.dumps(value))

    return json.loads(template_text)
