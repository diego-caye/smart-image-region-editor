from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.http.dependencies import (
    get_confirm_edit_use_case,
    get_discard_edit_use_case,
    get_edit_progress_tracker,
    get_edit_region_use_case,
)
from app.adapters.http.schemas.edits import (
    ConfirmEditResponse,
    DiscardEditResponse,
    EditProgressResponse,
    EditRegionRequestBody,
    EditRegionResponse,
)
from app.application.dto.edit_region import EditRegionRequest
from app.application.ports.edit_progress_tracker import EditProgressTracker
from app.application.use_cases.confirm_edit import ConfirmEditUseCase
from app.application.use_cases.confirm_edit import EditNotFound as ConfirmEditNotFound
from app.application.use_cases.discard_edit import DiscardEditUseCase
from app.application.use_cases.discard_edit import EditNotFound as DiscardEditNotFound
from app.application.use_cases.edit_region import (
    EditRegionUseCase,
    EditSessionNotFound,
    ImageNotFound,
    RegionNotFound,
)
from app.domain.entities.edit import InvalidEditTransition
from app.domain.services.operation_options import InvalidOperationOptions
from app.domain.services.region_operation_rules import OperationNotAllowedForRegion

# Two routers, no shared prefix: creating an edit is scoped under the image
# it belongs to (/images/{id}/edits); confirming/discarding acts on the
# edit itself (/edits/{id}/...).
images_edits_router = APIRouter(prefix="/images", tags=["edits"])
edits_router = APIRouter(prefix="/edits", tags=["edits"])


@images_edits_router.post("/{image_id}/edits", response_model=EditRegionResponse, status_code=201)
def create_edit(
    image_id: UUID,
    body: EditRegionRequestBody,
    use_case: EditRegionUseCase = Depends(get_edit_region_use_case),
) -> EditRegionResponse:
    try:
        result = use_case.execute(
            EditRegionRequest(
                image_id=image_id,
                region_id=body.region_id,
                operation=body.operation,
                color=body.color,
                progress_id=body.progress_id,
            )
        )
    except (ImageNotFound, RegionNotFound, EditSessionNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (OperationNotAllowedForRegion, InvalidOperationOptions) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return EditRegionResponse(
        edit_id=result.edit_id,
        status=result.status,
        preview_url=result.preview_url,
        error_message=result.error_message,
    )


@edits_router.get("/progress/{progress_id}", response_model=EditProgressResponse)
def get_edit_progress(
    progress_id: str, tracker: EditProgressTracker = Depends(get_edit_progress_tracker)
) -> EditProgressResponse:
    progress = tracker.get(progress_id)
    if progress is None:
        # Also the normal answer for the first poll or two, before the edit
        # request has reported anything — clients should keep polling.
        raise HTTPException(status_code=404, detail="No progress reported for this id yet")
    return EditProgressResponse(
        stage=progress.stage, fraction=progress.fraction, step=progress.step, steps=progress.steps
    )


@edits_router.post("/{edit_id}/confirm", response_model=ConfirmEditResponse)
def confirm_edit(
    edit_id: UUID, use_case: ConfirmEditUseCase = Depends(get_confirm_edit_use_case)
) -> ConfirmEditResponse:
    try:
        result = use_case.execute(edit_id)
    except ConfirmEditNotFound as exc:
        raise HTTPException(status_code=404, detail="Edit not found") from exc
    except InvalidEditTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ConfirmEditResponse(edit_id=result.edit_id, status=result.status, final_url=result.final_url)


@edits_router.post("/{edit_id}/discard", response_model=DiscardEditResponse)
def discard_edit(
    edit_id: UUID, use_case: DiscardEditUseCase = Depends(get_discard_edit_use_case)
) -> DiscardEditResponse:
    try:
        result = use_case.execute(edit_id)
    except DiscardEditNotFound as exc:
        raise HTTPException(status_code=404, detail="Edit not found") from exc
    except InvalidEditTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return DiscardEditResponse(edit_id=result.edit_id, status=result.status)
