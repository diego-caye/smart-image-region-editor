from app.infrastructure.image_editing.comfyui.workflow import (
    OUTPUT_NODE_ID,
    QwenEditParams,
    build_qwen_edit_prompt,
)

_PARAMS = QwenEditParams(
    image_filename="crop_123.png",
    prompt_text='Change the hand to a "peace sign".',
    seed=42,
    unet_name="qwen_image_edit_2511_fp8mixed.safetensors",
    clip_name="qwen_2.5_vl_7b_fp8_scaled.safetensors",
    vae_name="qwen_image_vae.safetensors",
    lora_name="Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors",
    lora_strength=1.0,
    model_shift=3.1,
    cfg_norm_strength=1.0,
    steps=4,
    cfg=1.0,
    sampler_name="euler",
    scheduler="simple",
)


def test_output_node_id_matches_the_save_image_node_in_the_template():
    prompt = build_qwen_edit_prompt(_PARAMS)
    assert OUTPUT_NODE_ID in prompt
    assert prompt[OUTPUT_NODE_ID]["class_type"] == "SaveImage"


def test_numeric_params_are_substituted_as_json_numbers_not_strings():
    prompt = build_qwen_edit_prompt(_PARAMS)
    assert prompt["sampler"]["inputs"]["seed"] == 42
    assert isinstance(prompt["sampler"]["inputs"]["seed"], int)
    assert prompt["sampler"]["inputs"]["steps"] == 4
    assert prompt["sampler"]["inputs"]["cfg"] == 1.0
    assert isinstance(prompt["sampler"]["inputs"]["cfg"], float)


def test_prompt_text_with_special_characters_is_safely_escaped():
    prompt = build_qwen_edit_prompt(_PARAMS)
    assert prompt["positive_cond"]["inputs"]["prompt"] == 'Change the hand to a "peace sign".'
    # the negative branch always stays empty regardless of the positive prompt
    assert prompt["negative_cond"]["inputs"]["prompt"] == ""


def test_model_filenames_flow_through_to_their_loader_nodes():
    prompt = build_qwen_edit_prompt(_PARAMS)
    assert prompt["unet_loader"]["inputs"]["unet_name"] == _PARAMS.unet_name
    assert prompt["clip_loader"]["inputs"]["clip_name"] == _PARAMS.clip_name
    assert prompt["vae_loader"]["inputs"]["vae_name"] == _PARAMS.vae_name
    assert prompt["lora"]["inputs"]["lora_name"] == _PARAMS.lora_name


def test_image_filename_flows_to_the_load_image_node():
    prompt = build_qwen_edit_prompt(_PARAMS)
    assert prompt["load_image"]["inputs"]["image"] == "crop_123.png"


def test_every_node_reference_points_at_a_node_that_exists_in_the_graph():
    """A link like ["scale", 0] must reference a node id that's actually a
    key in the graph — a stale/renamed node id here is exactly the kind of
    mistake that would only surface as a cryptic ComfyUI validation error."""
    prompt = build_qwen_edit_prompt(_PARAMS)
    node_ids = set(prompt.keys())
    for node in prompt.values():
        for value in node["inputs"].values():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                assert value[0] in node_ids, f"dangling reference to node '{value[0]}'"
