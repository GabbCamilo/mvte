"""Linguistic hierarchy domain models for MVTE (Phase 2)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mvte.domain.models.page import BoundingBox


class TextOrientation(str, Enum):
    """Dominant writing orientation of a text region or line."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    UNKNOWN = "unknown"


@dataclass
class Token:
    """Smallest linguistic unit preserving source coordinates and OCR review flags."""

    id: str
    text: str
    bbox: BoundingBox
    confidence: float
    needs_review: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "bbox": self.bbox.to_dict(),
            "confidence": round(float(self.confidence), 4),
            "needs_review": self.needs_review,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Token:
        return cls(
            id=str(data["id"]),
            text=str(data["text"]),
            bbox=BoundingBox.from_dict(data["bbox"]),
            confidence=float(data["confidence"]),
            needs_review=bool(data.get("needs_review", False)),
        )


@dataclass
class Sentence:
    """Reconstructed complete sentence grouped from one or more OCR lines."""

    id: str
    text: str
    tokens: list[Token] = field(default_factory=list)
    bbox: BoundingBox | None = None
    reading_order: int = 0
    language: str = "unknown"
    confidence: float = 1.0
    needs_review: bool = False
    manual_override: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "tokens": [t.to_dict() for t in self.tokens],
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "reading_order": self.reading_order,
            "language": self.language,
            "confidence": round(float(self.confidence), 4),
            "needs_review": self.needs_review,
            "manual_override": self.manual_override,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Sentence:
        bbox_data = data.get("bbox")
        return cls(
            id=str(data["id"]),
            text=str(data["text"]),
            tokens=[Token.from_dict(t) for t in data.get("tokens", [])],
            bbox=BoundingBox.from_dict(bbox_data) if bbox_data else None,
            reading_order=int(data.get("reading_order", 0)),
            language=str(data.get("language", "unknown")),
            confidence=float(data.get("confidence", 1.0)),
            needs_review=bool(data.get("needs_review", False)),
            manual_override=bool(data.get("manual_override", False)),
        )


@dataclass
class TextBlock:
    """Linguistic container linked to a VisualRegion and Panel."""

    id: str
    region_id: str
    panel_id: str | None
    orientation: TextOrientation = TextOrientation.HORIZONTAL
    language: str = "unknown"
    reading_order: int = 0
    sentences: list[Sentence] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        region_id: str,
        panel_id: str | None,
        orientation: TextOrientation = TextOrientation.HORIZONTAL,
        language: str = "unknown",
        reading_order: int = 0,
        sentences: list[Sentence] | None = None,
    ) -> TextBlock:
        return cls(
            id=str(uuid.uuid4()),
            region_id=region_id,
            panel_id=panel_id,
            orientation=orientation,
            language=language,
            reading_order=reading_order,
            sentences=sentences or [],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "region_id": self.region_id,
            "panel_id": self.panel_id,
            "orientation": self.orientation.value,
            "language": self.language,
            "reading_order": self.reading_order,
            "sentences": [s.to_dict() for s in self.sentences],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TextBlock:
        return cls(
            id=str(data["id"]),
            region_id=str(data["region_id"]),
            panel_id=data.get("panel_id"),
            orientation=TextOrientation(data.get("orientation", "horizontal")),
            language=str(data.get("language", "unknown")),
            reading_order=int(data.get("reading_order", 0)),
            sentences=[Sentence.from_dict(s) for s in data.get("sentences", [])],
        )
