from __future__ import annotations

import mimetypes
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from app.adapters.http.dependencies import (
    get_current_image_use_case,
    get_edit_history_use_case,
    get_undo_last_edit_use_case,
)
from app.adapters.http.schemas.history import EditHistoryResponse, UndoResponse
from app.application.use_cases.edit_region import EditSessionNotFound, ImageNotFound
from app.application.use_cases.get_current_image import GetCurrentImageUseCase
from app.application.use_cases.get_edit_history import GetEditHistoryUseCase
from app.application.use_cases.undo_last_edit import NothingToUndo, UndoLastEditUseCase

router = APIRouter(prefix="/images", tags=["history"])

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


@router.get("/{image_id}/history", response_model=EditHistoryResponse)
def get_history(
    image_id: UUID, use_case: GetEditHistoryUseCase = Depends(get_edit_history_use_case)
) -> EditHistoryResponse:
    try:
        return EditHistoryResponse.from_result(use_case.execute(image_id))
    except (ImageNotFound, EditSessionNotFound) as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc


@router.post("/{image_id}/undo", response_model=UndoResponse)
def undo_last_edit(
    image_id: UUID, use_case: UndoLastEditUseCase = Depends(get_undo_last_edit_use_case)
) -> UndoResponse:
    try:
        result = use_case.execute(image_id)
    except EditSessionNotFound as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc
    except NothingToUndo as exc:
        raise HTTPException(status_code=409, detail="No applied edit to undo") from exc
    return UndoResponse(reverted_edit_id=result.reverted_edit_id, current_url=result.current_url)


@router.get("/{image_id}/download")
def download_current_image(
    image_id: UUID, use_case: GetCurrentImageUseCase = Depends(get_current_image_use_case)
) -> Response:
    try:
        current = use_case.execute(image_id)
    except (ImageNotFound, EditSessionNotFound) as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc
    # The name comes from the user's upload: keep it to characters that are
    # safe inside a quoted header value.
    filename = _UNSAFE_FILENAME_CHARS.sub("_", current.filename)
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return Response(
        content=current.data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
