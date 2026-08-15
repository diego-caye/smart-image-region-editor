from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.edit import Edit
from app.domain.entities.edit_session import EditSession
from app.domain.entities.image import Image
from app.domain.entities.mask import Mask
from app.domain.entities.region import DetectedRegion


class ImageRepository(ABC):
    """Persists the entities that make up an editing session. One port for
    several entity kinds because they are always read/written together
    within a use case, and a real (SQL) adapter will want them under one
    transactional boundary.
    """

    @abstractmethod
    def save_image(self, image: Image) -> None: ...

    @abstractmethod
    def get_image(self, image_id: UUID) -> Image | None: ...

    @abstractmethod
    def save_regions(self, regions: list[DetectedRegion]) -> None: ...

    @abstractmethod
    def get_regions_for_image(self, image_id: UUID) -> list[DetectedRegion]: ...

    @abstractmethod
    def get_region(self, region_id: UUID) -> DetectedRegion | None: ...

    @abstractmethod
    def update_region(self, region: DetectedRegion) -> None: ...

    @abstractmethod
    def save_mask(self, mask: Mask) -> None: ...

    @abstractmethod
    def get_mask(self, mask_id: UUID) -> Mask | None: ...

    @abstractmethod
    def save_edit_session(self, session: EditSession) -> None: ...

    @abstractmethod
    def get_edit_session(self, session_id: UUID) -> EditSession | None: ...

    @abstractmethod
    def get_edit_session_for_image(self, image_id: UUID) -> EditSession | None: ...

    @abstractmethod
    def save_edit(self, edit: Edit) -> None: ...

    @abstractmethod
    def get_edit(self, edit_id: UUID) -> Edit | None: ...

    @abstractmethod
    def get_edits_for_session(self, session_id: UUID) -> list[Edit]: ...
