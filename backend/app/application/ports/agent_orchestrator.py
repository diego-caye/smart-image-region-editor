from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.domain.value_objects.edit_operation import EditOperation
from app.domain.value_objects.region_type import RegionType


@dataclass(slots=True)
class SuggestedEdit:
    region_type: RegionType
    operation: EditOperation
    confidence: float


class AgentOrchestrator(ABC):
    """Reserved extension point for an optional, non-deterministic planning
    layer — nothing in this codebase depends on it yet.

    The core flow (upload -> analyze -> select region -> select operation ->
    edit -> composite) is fully deterministic and works without any LLM. If
    an agent ever adds real value (e.g. mapping a free-text instruction to a
    region + operation), its implementation — LangGraph, Google ADK, a
    hand-rolled loop — lives entirely in Infrastructure and is wired in
    behind this port, exactly like every other adapter. Domain and
    Application do not change when that happens.
    """

    @abstractmethod
    def suggest_edit(self, instruction: str, *, image_id: UUID) -> SuggestedEdit | None: ...
