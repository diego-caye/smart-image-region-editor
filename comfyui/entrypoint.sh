#!/bin/sh
set -e

/opt/comfyui/download_models.sh

# main.py's prestartup step does a bare os.listdir() on this directory
# (folder_paths.get_folder_paths("custom_nodes")) with no existence check —
# confirmed by the real crash without it: "FileNotFoundError: [Errno 2] No
# such file or directory: '/data/custom_nodes'". Every other directory
# under --base-directory (models/input/output/user/temp) is created lazily
# via os.makedirs(..., exist_ok=True) elsewhere, so only this one needs to
# be pre-created — vanilla ComfyUI simply assumes a fresh --base-directory
# already has an (even empty) custom_nodes folder, which a brand-new named
# volume like comfyui_data does not.
mkdir -p /data/custom_nodes

# --base-directory puts models/input/output/user/temp all under the one
# persistent /data volume (docker-compose.yml's comfyui_data), so a
# `docker compose down`/`up` doesn't lose downloaded models or generated
# images. --listen 0.0.0.0 is what makes ComfyUI's own UI reachable from
# the host, not just from other containers.
exec python main.py --listen 0.0.0.0 --port 8188 --base-directory /data
