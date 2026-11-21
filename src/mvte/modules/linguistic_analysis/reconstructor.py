"""Linguistic reconstruction: line grouping, sentence assembly, tokenization, and OCR error flags."""

from __future__ import annotations

import re
import uuid

from mvte.domain.models.linguistic import (
    Sentence,
    TextBlock,
    TextOrientation,
    Token,
)
from mvte.domain.models.page import BoundingBox, ReadingDirection, VisualRegion
from mvte.domain.ports.ocr import OcrLine

SENTENCE_ENDINGS = (".", "!", "?", "。", "！", "？", "…")
TOKEN_PATTERN = re.compile(r"\w+(?:[-']\w+)*|[^\w\s]", re.UNICODE)
ANOMALY_PATTERN = re.compile(r"[|]{2,}|[_]{3,}|\uFFFD")


class SentenceReconstructor:
    """Groups OCR lines into coherent sentences and tokens while flagging suspicious OCR."""

    def __init__(self, low_confidence_threshold: float = 0.72) -> None:
        self.low_confidence_threshold = low_confidence_threshold

    def reconstruct(
        self,
        region: VisualRegion,
        ocr_lines: list[OcrLine],
        direction: ReadingDirection,
        reading_order: int = 0,
    ) -> TextBlock:
        if not ocr_lines:
            return TextBlock.create(
                region_id=region.id,
                panel_id=region.panel_id,
                orientation=TextOrientation.UNKNOWN,
                reading_order=reading_order,
            )

        dominant_orientation = self._dominant_orientation(ocr_lines)
        ordered_lines = self._sort_lines(ocr_lines, dominant_orientation, direction)
        grouped_lines = self._group_into_sentences(ordered_lines)

        sentences: list[Sentence] = []
        for s_idx, group in enumerate(grouped_lines):
            joined_text = self._join_group_text(group, dominant_orientation)
            merged_bbox = self._merge_bboxes([line.bbox for line in group])
            avg_conf = sum(line.confidence for line in group) / len(group)
            tokens = self._tokenize(joined_text, merged_bbox, avg_conf)
            needs_review = any(t.needs_review for t in tokens) or avg_conf < self.low_confidence_threshold
            lang = next((line.language for line in group if line.language != "unknown"), "unknown")

            sentences.append(
                Sentence(
                    id=str(uuid.uuid4()),
                    text=joined_text,
                    tokens=tokens,
                    bbox=merged_bbox,
                    reading_order=s_idx,
                    language=lang,
                    confidence=avg_conf,
                    needs_review=needs_review,
                )
            )

        block_lang = next((s.language for s in sentences if s.language != "unknown"), "unknown")
        return TextBlock.create(
            region_id=region.id,
            panel_id=region.panel_id,
            orientation=dominant_orientation,
            language=block_lang,
            reading_order=reading_order,
            sentences=sentences,
        )

    @staticmethod
    def _dominant_orientation(lines: list[OcrLine]) -> TextOrientation:
        vertical_count = sum(1 for l in lines if l.orientation == TextOrientation.VERTICAL)
        horizontal_count = sum(1 for l in lines if l.orientation == TextOrientation.HORIZONTAL)
        if vertical_count > horizontal_count:
            return TextOrientation.VERTICAL
        if horizontal_count > 0:
            return TextOrientation.HORIZONTAL
        return TextOrientation.UNKNOWN

    @staticmethod
    def _sort_lines(
        lines: list[OcrLine],
        orientation: TextOrientation,
        direction: ReadingDirection,
    ) -> list[OcrLine]:
        if orientation == TextOrientation.VERTICAL:
            # Vertical manga text reads right-to-left columns, top-to-bottom within column.
            reverse_col = direction == ReadingDirection.RTL
            return sorted(lines, key=lambda l: (l.bbox.x1 if not reverse_col else -l.bbox.x1, l.bbox.y1))
        return sorted(lines, key=lambda l: (l.bbox.y1, l.bbox.x1))

    @staticmethod
    def _group_into_sentences(lines: list[OcrLine]) -> list[list[OcrLine]]:
        groups: list[list[OcrLine]] = []
        current: list[OcrLine] = []
        for line in lines:
            text = line.text.strip()
            if not text:
                continue
            current.append(line)
            if text.endswith(SENTENCE_ENDINGS):
                groups.append(current)
                current = []
        if current:
            groups.append(current)
        return groups

    @staticmethod
    def _join_group_text(group: list[OcrLine], orientation: TextOrientation) -> str:
        parts: list[str] = []
        for line in group:
            part = line.text.strip()
            if parts and parts[-1].endswith("-") and orientation == TextOrientation.HORIZONTAL:
                parts[-1] = parts[-1][:-1] + part
            else:
                parts.append(part)
        separator = "" if orientation == TextOrientation.VERTICAL else " "
        return separator.join(parts).strip()

    @staticmethod
    def _merge_bboxes(bboxes: list[BoundingBox]) -> BoundingBox:
        return BoundingBox(
            x1=min(b.x1 for b in bboxes),
            y1=min(b.y1 for b in bboxes),
            x2=max(b.x2 for b in bboxes),
            y2=max(b.y2 for b in bboxes),
        )

    def _tokenize(
        self, text: str, bbox: BoundingBox, confidence: float
    ) -> list[Token]:
        raw_tokens = TOKEN_PATTERN.findall(text)
        tokens: list[Token] = []
        for tok in raw_tokens:
            flagged = confidence < self.low_confidence_threshold or bool(ANOMALY_PATTERN.search(tok))
            tokens.append(
                Token(
                    id=str(uuid.uuid4()),
                    text=tok,
                    bbox=bbox,
                    confidence=confidence,
                    needs_review=flagged,
                )
            )
        return tokens
