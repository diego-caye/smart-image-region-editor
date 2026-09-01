from __future__ import annotations

import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image as PILImage

from app.adapters.http.dependencies import (
    get_analyze_image_use_case,
    get_get_detected_regions_use_case,
    get_upload_image_use_case,
)
from app.adapters.http.schemas.images import AnalyzeImageResponse, UploadImageResponse
from app.application.dto.upload_image import UploadImageRequest
from app.application.use_cases.analyze_image import AnalyzeImageUseCase, ImageNotFound
from app.application.use_cases.get_detected_regions import GetDetectedRegionsUseCase
from app.application.use_cases.upload_image import UploadImageUseCase

router = APIRouter(prefix="/images", tags=["images"])


@router.post("", response_model=UploadImageResponse, status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    use_case: UploadImageUseCase = Depends(get_upload_image_use_case),
) -> UploadImageResponse:
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Pillow lives here (an HTTP adapter), never in Application — the use
    # case only ever receives already-known width/height.
    try:
        with PILImage.open(io.BytesIO(raw_bytes)) as pil_image:
            width, height = pil_image.size
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image") from exc

    result = use_case.execute(
        UploadImageRequest(
            file_bytes=raw_bytes,
            original_filename=file.filename or "upload.png",
            content_type=file.content_type or "image/png",
            width=width,
            height=height,
        )
    )
    return UploadImageResponse(
        image_id=result.image_id, width=result.width, height=result.height, url=result.url
    )


@router.post("/{image_id}/analyze", response_model=AnalyzeImageResponse)
def analyze_image(
    image_id: UUID,
    use_case: AnalyzeImageUseCase = Depends(get_analyze_image_use_case),
) -> AnalyzeImageResponse:
    try:
        result = use_case.execute(image_id)
    except ImageNotFound as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc
    return AnalyzeImageResponse.from_result(result)


@router.get("/{image_id}/regions", response_model=AnalyzeImageResponse)
def get_regions(
    image_id: UUID,
    use_case: GetDetectedRegionsUseCase = Depends(get_get_detected_regions_use_case),
) -> AnalyzeImageResponse:
    return AnalyzeImageResponse.from_result(use_case.execute(image_id))
