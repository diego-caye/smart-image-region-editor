from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.adapters.http.dependencies import get_image_storage
from app.domain.ports.image_storage import ImageStorage

router = APIRouter(tags=["static"])


# Goes through ImageStorage.load() rather than a raw StaticFiles mount, on
# purpose: it keeps every path back to image bytes going through the same
# port (swap ImageStorage for S3 later and this still works, or gets
# replaced by a redirect to a signed URL — either way Domain/Application
# don't change), and it makes this endpoint testable/overridable exactly
# like every other route via dependency_overrides.
#
# The "/static" prefix mirrors Settings.static_url_prefix's default; both
# are expected to stay in sync (FastAPI route paths can't read Settings at
# decoration time).
@router.get("/static/{storage_ref:path}")
def get_static_file(
    storage_ref: str, storage: ImageStorage = Depends(get_image_storage)
) -> Response:
    try:
        data = storage.load(storage_ref)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    content_type = mimetypes.guess_type(storage_ref)[0] or "application/octet-stream"
    return Response(content=data, media_type=content_type)
