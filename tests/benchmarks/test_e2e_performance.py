"""End-to-end performance benchmark across all 5 MVTE phases."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from mvte.domain.models.translation import TranslationContextPacket, TranslationResult
from mvte.interfaces.contracts.service_contract import TranslationJobRequest, execute_job


def test_e2e_pipeline_performance_under_budget(tmp_path: Path) -> None:
    page_path = tmp_path / "bench_page.png"
    img = np.full((800, 600, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (580, 780), (20, 20, 20), 4)
    cv2.rectangle(img, (24, 24), (576, 776), (60, 60, 60), -1)
    cv2.ellipse(img, (300, 220), (150, 70), 0, 0, 360, (255, 255, 255), -1)
    cv2.putText(img, "WAIT!", (240, 230), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)
    cv2.imwrite(str(page_path), img)

    class FastStubTranslator:
        name = "fast_stub"

        def translate(self, text: str, packet: TranslationContextPacket) -> TranslationResult:
            return TranslationResult("ESPERE!", 0.96)

        def unload(self) -> None:
            return None

    req = TranslationJobRequest(
        image_paths=[str(page_path)],
        work_id="bench",
        chapter_id="ch1",
        source_lang="en",
        target_lang="pt-BR",
        workspace_dir=str(tmp_path / "ws"),
        context_db_path=str(tmp_path / "ctx.sqlite"),
    )
    resp = execute_job(req, translator_backend=FastStubTranslator())
    assert resp.succeeded == 1
    assert resp.items[0]["elapsed_ms"] < 15000.0
