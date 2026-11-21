"""Hierarchical visual document domain models for MVTE (Phase 1)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import numpy as np


class RegionKind(str, Enum):
    """Visual structure categories on a manga/comic page."""

    SPEECH_BALLOON = "speech_balloon"
    THOUGHT_BALLOON = "thought_balloon"
    NARRATION_BOX = "narration_box"
    SFX = "sfx"
    FREE_TEXT = "free_text"
    UNKNOWN = "unknown"


class ReadingDirection(str, Enum):
    """Global page reading order."""

    RTL = "rtl"
    LTR = "ltr"


class MaskKind(str, Enum):
    """Distinguishes structural container masks from character/text masks."""

    STRUCTURE = "structure"
    CHARACTER = "character"


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned integer bounding box [x1, y1, x2, y2]."""

    x1: int
    y1: int
    x2: int
    y2: int

    def __post_init__(self) -> None:
        if self.x2 < self.x1 or self.y2 < self.y1:
            raise ValueError(f"Invalid bounding box coordinates: {(self.x1, self.y1, self.x2, self.y2)}")

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def intersection_area(self, other: BoundingBox) -> int:
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0
        return (ix2 - ix1) * (iy2 - iy1)

    def iou(self, other: BoundingBox) -> float:
        inter = self.intersection_area(other)
        if inter == 0:
            return 0.0
        union = self.area + other.area - inter
        return inter / union if union > 0 else 0.0

    def containment_ratio(self, container: BoundingBox) -> float:
        """Fraction of this box's area contained inside `container`."""
        if self.area == 0:
            return 0.0
        return self.intersection_area(container) / self.area

    def to_dict(self) -> dict[str, int]:
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BoundingBox:
        return cls(
            x1=int(data["x1"]),
            y1=int(data["y1"]),
            x2=int(data["x2"]),
            y2=int(data["y2"]),
        )


@dataclass
class MaskLayer:
    """Pixel-level mask layer (binary uint8 0/255) stored separately from original image."""

    id: str
    kind: MaskKind
    width: int
    height: int
    path: str | None = None
    data: np.ndarray | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "width": self.width,
            "height": self.height,
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MaskLayer:
        return cls(
            id=str(data["id"]),
            kind=MaskKind(data["kind"]),
            width=int(data["width"]),
            height=int(data["height"]),
            path=data.get("path"),
        )


@dataclass
class RevisionEntry:
    """Audit record for manual or automated edits on a PageDocument."""

    timestamp: str
    action: str
    target_id: str
    field: str
    old_value: Any
    new_value: Any
    note: str = ""

    @classmethod
    def create(
        cls,
        action: str,
        target_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        note: str = "",
    ) -> RevisionEntry:
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            target_id=target_id,
            field=field_name,
            old_value=old_value,
            new_value=new_value,
            note=note,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "target_id": self.target_id,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RevisionEntry:
        return cls(
            timestamp=str(data["timestamp"]),
            action=str(data["action"]),
            target_id=str(data["target_id"]),
            field=str(data["field"]),
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            note=str(data.get("note", "")),
        )


@dataclass
class Panel:
    """Detected comic/manga panel with reading order index."""

    id: str
    bbox: BoundingBox
    reading_order: int
    polygon: list[tuple[int, int]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "bbox": self.bbox.to_dict(),
            "reading_order": self.reading_order,
            "polygon": [list(pt) for pt in self.polygon],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Panel:
        return cls(
            id=str(data["id"]),
            bbox=BoundingBox.from_dict(data["bbox"]),
            reading_order=int(data["reading_order"]),
            polygon=[(int(p[0]), int(p[1])) for p in data.get("polygon", [])],
        )


@dataclass
class VisualRegion:
    """Detected and segmented visual structure (balloon, narration box, SFX, free text)."""

    id: str
    kind: RegionKind
    bbox: BoundingBox
    confidence: float
    polygon: list[tuple[int, int]] = field(default_factory=list)
    panel_id: str | None = None
    structure_mask: MaskLayer | None = None
    character_mask: MaskLayer | None = None
    source: str = "auto"
    manual_override: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "bbox": self.bbox.to_dict(),
            "confidence": round(float(self.confidence), 4),
            "polygon": [list(pt) for pt in self.polygon],
            "panel_id": self.panel_id,
            "structure_mask": self.structure_mask.to_dict() if self.structure_mask else None,
            "character_mask": self.character_mask.to_dict() if self.character_mask else None,
            "source": self.source,
            "manual_override": self.manual_override,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VisualRegion:
        sm = data.get("structure_mask")
        cm = data.get("character_mask")
        return cls(
            id=str(data["id"]),
            kind=RegionKind(data["kind"]),
            bbox=BoundingBox.from_dict(data["bbox"]),
            confidence=float(data["confidence"]),
            polygon=[(int(p[0]), int(p[1])) for p in data.get("polygon", [])],
            panel_id=data.get("panel_id"),
            structure_mask=MaskLayer.from_dict(sm) if sm else None,
            character_mask=MaskLayer.from_dict(cm) if cm else None,
            source=str(data.get("source", "auto")),
            manual_override=bool(data.get("manual_override", False)),
        )


@dataclass
class TextRegionAssociation:
    """Spatial relationship between a text region and its enclosing visual container/panel."""

    id: str
    text_region_id: str
    container_region_id: str | None
    panel_id: str | None
    is_free_text: bool
    confidence: float
    manual_override: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text_region_id": self.text_region_id,
            "container_region_id": self.container_region_id,
            "panel_id": self.panel_id,
            "is_free_text": self.is_free_text,
            "confidence": round(float(self.confidence), 4),
            "manual_override": self.manual_override,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TextRegionAssociation:
        return cls(
            id=str(data["id"]),
            text_region_id=str(data["text_region_id"]),
            container_region_id=data.get("container_region_id"),
            panel_id=data.get("panel_id"),
            is_free_text=bool(data["is_free_text"]),
            confidence=float(data["confidence"]),
            manual_override=bool(data.get("manual_override", False)),
        )


@dataclass
class PageDocument:
    """Root structured visual document preserving original page metadata and revision history."""

    id: str
    source_path: str
    width: int
    height: int
    reading_direction: ReadingDirection = ReadingDirection.RTL
    panels: list[Panel] = field(default_factory=list)
    regions: list[VisualRegion] = field(default_factory=list)
    associations: list[TextRegionAssociation] = field(default_factory=list)
    revisions: list[RevisionEntry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        source_path: str,
        width: int,
        height: int,
        reading_direction: ReadingDirection = ReadingDirection.RTL,
        metadata: dict[str, Any] | None = None,
    ) -> PageDocument:
        return cls(
            id=str(uuid.uuid4()),
            source_path=source_path,
            width=width,
            height=height,
            reading_direction=reading_direction,
            metadata=metadata or {},
        )

    def find_region(self, region_id: str) -> VisualRegion | None:
        for region in self.regions:
            if region.id == region_id:
                return region
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_path": self.source_path,
            "width": self.width,
            "height": self.height,
            "reading_direction": self.reading_direction.value,
            "panels": [p.to_dict() for p in self.panels],
            "regions": [r.to_dict() for r in self.regions],
            "associations": [a.to_dict() for a in self.associations],
            "revisions": [rev.to_dict() for rev in self.revisions],
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PageDocument:
        return cls(
            id=str(data["id"]),
            source_path=str(data["source_path"]),
            width=int(data["width"]),
            height=int(data["height"]),
            reading_direction=ReadingDirection(data.get("reading_direction", "rtl")),
            panels=[Panel.from_dict(p) for p in data.get("panels", [])],
            regions=[VisualRegion.from_dict(r) for r in data.get("regions", [])],
            associations=[TextRegionAssociation.from_dict(a) for a in data.get("associations", [])],
            revisions=[RevisionEntry.from_dict(rev) for rev in data.get("revisions", [])],
            metadata=dict(data.get("metadata", {})),
        )

    @classmethod
    def from_json(cls, raw_json: str) -> PageDocument:
        return cls.from_dict(json.loads(raw_json))
