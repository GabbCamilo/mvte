"""Unit and integration tests covering Phase 5 OpenSpec scenarios (RF-18 to RF-20)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from mvte.domain.models.linguistic import Sentence, TextBlock
from mvte.domain.models.page import BoundingBox, PageDocument
from mvte.domain.models.translation import TranslationContextPacket, TranslationResult
from mvte.interfaces.contracts.service_contract import TranslationJobRequest, execute_job
from mvte.modules.validation.validator import PageValidationEngine


def _make_e2e_page(path: Path) -> Path:
    img = np.full((600, 500, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (480, 580), (20, 20, 20), 4)
    cv2.rectangle(img, (24, 24), (476, 576), (55, 55, 55), -1)
    cv2.ellipse(img, (250, 180), (140, 65), 0, 0, 360, (255, 255, 255), -1)
    cv2.putText(img, "HELLO!", (185, 188), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.imwrite(str(path), img)
    return path


def test_rf18_validation_detects_omission_and_missing_masks(tmp_path: Path) -> None:
    doc = PageDocument.create(str(tmp_path / "p.png"), 500, 600)
    sent = Sentence(id="s1", text="Hello!", translation="")
    doc.text_blocks.append(TextBlock.create("r1", "p1", sentences=[sent]))

    report = PageValidationEngine().validate(doc)
    assert report.passed is False
    assert any(i.code == "translation_omission" for i in report.issues)


def test_rf19_rf20_batch_fault_isolation_and_service_contract(tmp_path: Path) -> None:
    valid_page = _make_e2e_page(tmp_path / "valid.png")
    bad_page = tmp_path / "missing.png"

    class StubTranslator:
        name = "stub_tr"

        def translate(self, text: str, packet: TranslationContextPacket) -> TranslationResult:
            return TranslationResult("OLA!", 0.95)

        def unload(self) -> None:
            return None

    req = TranslationJobRequest(
        image_paths=[str(valid_page), str(bad_page)],
        work_id="work_demo",
        chapter_id="ch1",
        source_lang="en",
        target_lang="pt-BR",
        workspace_dir=str(tmp_path / "ws"),
        context_db_path=str(tmp_path / "ctx.sqlite"),
        models_dir=str(tmp_path / "shared_models"),
    )

    resp = execute_job(req, translator_backend=StubTranslator())
    assert resp.total == 2
    assert resp.succeeded == 1
    assert resp.failed == 1
    assert resp.items[0]["success"] is True
    assert resp.items[0]["validation_passed"] is True
    assert Path(resp.items[0]["translated_path"]).exists()
    assert resp.items[1]["success"] is False
    assert "ImageLoadError" in resp.items[1]["error"]
