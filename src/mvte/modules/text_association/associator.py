"""Spatial association between text regions, visual containers, and panels."""

from __future__ import annotations

import uuid

from mvte.domain.models.page import Panel, RegionKind, TextRegionAssociation, VisualRegion

CONTAINER_KINDS = {
    RegionKind.SPEECH_BALLOON,
    RegionKind.THOUGHT_BALLOON,
    RegionKind.NARRATION_BOX,
}


class SpatialRegionAssociator:
    """Associates regions to panels and links text regions to enclosing containers."""

    def __init__(self, containment_threshold: float = 0.5) -> None:
        self.containment_threshold = containment_threshold

    def associate(
        self, panels: list[Panel], regions: list[VisualRegion]
    ) -> list[TextRegionAssociation]:
        containers = [r for r in regions if r.kind in CONTAINER_KINDS]
        associations: list[TextRegionAssociation] = []

        for region in regions:
            region.panel_id = self._find_best_panel(region, panels)

            if region.kind in CONTAINER_KINDS:
                associations.append(
                    TextRegionAssociation(
                        id=str(uuid.uuid4()),
                        text_region_id=region.id,
                        container_region_id=region.id,
                        panel_id=region.panel_id,
                        is_free_text=False,
                        confidence=region.confidence,
                    )
                )
                continue

            best_container: VisualRegion | None = None
            best_ratio = 0.0
            for container in containers:
                ratio = region.bbox.containment_ratio(container.bbox)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_container = container

            if best_container is not None and best_ratio >= self.containment_threshold:
                associations.append(
                    TextRegionAssociation(
                        id=str(uuid.uuid4()),
                        text_region_id=region.id,
                        container_region_id=best_container.id,
                        panel_id=region.panel_id or best_container.panel_id,
                        is_free_text=False,
                        confidence=best_ratio,
                    )
                )
            else:
                associations.append(
                    TextRegionAssociation(
                        id=str(uuid.uuid4()),
                        text_region_id=region.id,
                        container_region_id=None,
                        panel_id=region.panel_id,
                        is_free_text=True,
                        confidence=region.confidence,
                    )
                )

        return associations

    @staticmethod
    def _find_best_panel(region: VisualRegion, panels: list[Panel]) -> str | None:
        best_id: str | None = None
        best_ratio = 0.0
        for panel in panels:
            ratio = region.bbox.containment_ratio(panel.bbox)
            if ratio > best_ratio:
                best_ratio = ratio
                best_id = panel.id
        return best_id
