from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.application.dto.analyze_image import AnalyzeImageResult
from app.domain.value_objects.region_type import RegionType


class UploadImageResponse(BaseModel):
    image_id: UUID
    width: int
    height: int
    url: str


class RegionResponse(BaseModel):
    region_id: UUID
    region_type: RegionType
    x: int
    y: int
    width: int
    height: int
    confidence: float


class AnalyzeImageResponse(BaseModel):
    image_id: UUID
    regions: list[RegionResponse]

    @staticmethod
    def from_result(result: AnalyzeImageResult) -> AnalyzeImageResponse:
        return AnalyzeImageResponse(
            image_id=result.image_id,
            regions=[
                RegionResponse(
                    region_id=r.region_id,
                    region_type=r.region_type,
                    x=r.x,
                    y=r.y,
                    width=r.width,
                    height=r.height,
                    confidence=r.confidence,
                )
                for r in result.regions
            ],
        )
