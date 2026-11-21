"""Manual region review and traceable revision history use case."""

from __future__ import annotations

from mvte.domain.models.page import (
    BoundingBox,
    PageDocument,
    RegionKind,
    RevisionEntry,
    VisualRegion,
)


class ReviewRegionsUseCase:
    """Applies manual corrections to a PageDocument with full auditability and undo."""

    def update_region_kind(
        self, document: PageDocument, region_id: str, new_kind: RegionKind, note: str = ""
    ) -> VisualRegion:
        region = self._require_region(document, region_id)
        old_kind = region.kind.value
        region.kind = new_kind
        region.manual_override = True
        document.revisions.append(
            RevisionEntry.create(
                action="update_kind",
                target_id=region_id,
                field_name="kind",
                old_value=old_kind,
                new_value=new_kind.value,
                note=note,
            )
        )
        return region

    def update_region_bbox(
        self, document: PageDocument, region_id: str, new_bbox: BoundingBox, note: str = ""
    ) -> VisualRegion:
        region = self._require_region(document, region_id)
        old_bbox = region.bbox.to_dict()
        region.bbox = new_bbox
        region.polygon = [
            (new_bbox.x1, new_bbox.y1),
            (new_bbox.x2, new_bbox.y1),
            (new_bbox.x2, new_bbox.y2),
            (new_bbox.x1, new_bbox.y2),
        ]
        region.manual_override = True
        document.revisions.append(
            RevisionEntry.create(
                action="update_bbox",
                target_id=region_id,
                field_name="bbox",
                old_value=old_bbox,
                new_value=new_bbox.to_dict(),
                note=note,
            )
        )
        return region

    def reassign_container(
        self,
        document: PageDocument,
        text_region_id: str,
        container_region_id: str | None,
        note: str = "",
    ) -> None:
        self._require_region(document, text_region_id)
        if container_region_id is not None:
            self._require_region(document, container_region_id)

        for assoc in document.associations:
            if assoc.text_region_id == text_region_id:
                old_container = assoc.container_region_id
                assoc.container_region_id = container_region_id
                assoc.is_free_text = container_region_id is None
                assoc.manual_override = True
                document.revisions.append(
                    RevisionEntry.create(
                        action="reassign_container",
                        target_id=text_region_id,
                        field_name="container_region_id",
                        old_value=old_container,
                        new_value=container_region_id,
                        note=note,
                    )
                )
                return

        raise KeyError(f"Association for region '{text_region_id}' not found")

    def update_sentence_text(
        self, document: PageDocument, sentence_id: str, new_text: str, note: str = ""
    ) -> None:
        sentence = document.find_sentence(sentence_id)
        if sentence is None:
            raise KeyError(f"Sentence '{sentence_id}' not found in PageDocument '{document.id}'")
        old_text = sentence.text
        sentence.text = new_text
        sentence.needs_review = False
        sentence.manual_override = True
        document.revisions.append(
            RevisionEntry.create(
                action="update_sentence_text",
                target_id=sentence_id,
                field_name="text",
                old_value=old_text,
                new_value=new_text,
                note=note,
            )
        )

    def update_sentence_translation(
        self, document: PageDocument, sentence_id: str, new_translation: str, note: str = ""
    ) -> None:
        sentence = document.find_sentence(sentence_id)
        if sentence is None:
            raise KeyError(f"Sentence '{sentence_id}' not found in PageDocument '{document.id}'")
        old_translation = sentence.translation
        sentence.translation = new_translation
        sentence.translation_needs_review = False
        sentence.manual_override = True
        document.revisions.append(
            RevisionEntry.create(
                action="update_sentence_translation",
                target_id=sentence_id,
                field_name="translation",
                old_value=old_translation,
                new_value=new_translation,
                note=note,
            )
        )

    def revert_last_revision(self, document: PageDocument) -> RevisionEntry | None:
        """Undo the most recent manual revision on the PageDocument."""
        if not document.revisions:
            return None
        last = document.revisions.pop()
        if last.action == "update_kind":
            region = self._require_region(document, last.target_id)
            region.kind = RegionKind(last.old_value)
        elif last.action == "update_bbox":
            region = self._require_region(document, last.target_id)
            region.bbox = BoundingBox.from_dict(last.old_value)
        elif last.action == "reassign_container":
            for assoc in document.associations:
                if assoc.text_region_id == last.target_id:
                    assoc.container_region_id = last.old_value
                    assoc.is_free_text = last.old_value is None
                    break
        elif last.action == "update_sentence_text":
            sentence = document.find_sentence(last.target_id)
            if sentence is not None:
                sentence.text = str(last.old_value)
        elif last.action == "update_sentence_translation":
            sentence = document.find_sentence(last.target_id)
            if sentence is not None:
                sentence.translation = str(last.old_value)
        return last

    @staticmethod
    def _require_region(document: PageDocument, region_id: str) -> VisualRegion:
        region = document.find_region(region_id)
        if region is None:
            raise KeyError(f"Region '{region_id}' not found in PageDocument '{document.id}'")
        return region
