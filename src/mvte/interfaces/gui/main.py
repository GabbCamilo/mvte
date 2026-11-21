"""Decoupled PySide6 GUI for Phase 1 mask visualization and manual region review."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mvte.application.use_cases.analyze_page import AnalyzePageUseCase
from mvte.application.use_cases.review_regions import ReviewRegionsUseCase
from mvte.domain.models.page import PageDocument, ReadingDirection, RegionKind
from mvte.infrastructure.storage.document_store import DocumentStore, load_image_lossless
from mvte.interfaces.cli.main import render_debug_overlay
from mvte.modules.page_analysis.analyzer import ContourPageAnalyzer
from mvte.modules.segmentation.segmenter import MaskSegmenter
from mvte.modules.text_association.associator import SpatialRegionAssociator
from mvte.modules.visual_detection.detector import MorphologicalBalloonDetector


def default_gui_workspace_dir() -> Path:
    """Resolve a writable workspace directory regardless of current working directory."""
    env_dir = os.environ.get("MVTE_WORKSPACE_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".mvte" / "gui_runs"


class PageReviewWindow(QMainWindow):
    """Lightweight review window decoupled from domain/pipeline internals."""

    def __init__(self, workspace_dir: Path | str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("MVTE — Leitor Global de Páginas (Fase 1)")
        self.resize(1180, 820)

        resolved_dir = Path(workspace_dir) if workspace_dir is not None else default_gui_workspace_dir()
        self.store = DocumentStore(resolved_dir)
        self.analyze_uc = AnalyzePageUseCase(
            page_analyzer=ContourPageAnalyzer(),
            detector=MorphologicalBalloonDetector(),
            segmenter=MaskSegmenter(),
            associator=SpatialRegionAssociator(),
            store=self.store,
        )
        self.review_uc = ReviewRegionsUseCase()
        self.current_doc: PageDocument | None = None
        self.current_image_bgr = None

        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)

        self.image_label = QLabel("Abra uma página para iniciar a análise.")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.image_label, stretch=3)

        side_panel = QVBoxLayout()
        open_btn = QPushButton("Abrir Página...")
        open_btn.clicked.connect(self._open_page)
        side_panel.addWidget(open_btn)

        self.region_list = QListWidget()
        self.region_list.currentRowChanged.connect(self._on_region_selected)
        side_panel.addWidget(self.region_list, stretch=1)

        self.kind_combo = QComboBox()
        for kind in RegionKind:
            self.kind_combo.addItem(kind.value, kind)
        side_panel.addWidget(self.kind_combo)

        apply_btn = QPushButton("Aplicar Classe (Manual)")
        apply_btn.clicked.connect(self._apply_kind_override)
        side_panel.addWidget(apply_btn)

        undo_btn = QPushButton("Desfazer Última Revisão")
        undo_btn.clicked.connect(self._undo_revision)
        side_panel.addWidget(undo_btn)

        main_layout.addLayout(side_panel, stretch=1)

    def _open_page(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Página", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)"
        )
        if not file_path:
            return
        try:
            self.current_doc = self.analyze_uc.execute(
                Path(file_path), reading_direction=ReadingDirection.RTL, persist=True
            )
            self.current_image_bgr, _, _ = load_image_lossless(file_path)
            self._refresh_view()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erro ao abrir página",
                f"Não foi possível analisar a página:\n{type(exc).__name__}: {exc}",
            )

    def _refresh_view(self) -> None:
        if self.current_doc is None or self.current_image_bgr is None:
            return
        overlay = render_debug_overlay(self.current_image_bgr, self.current_doc)
        rgb = overlay[:, :, ::-1].copy()
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(pixmap)

        self.region_list.clear()
        for idx, reg in enumerate(self.current_doc.regions):
            tag = " [MANUAL]" if reg.manual_override else ""
            self.region_list.addItem(f"#{idx} {reg.kind.value} ({reg.confidence:.2f}){tag}")

    def _on_region_selected(self, row: int) -> None:
        if self.current_doc is None or row < 0 or row >= len(self.current_doc.regions):
            return
        reg = self.current_doc.regions[row]
        idx = self.kind_combo.findData(reg.kind)
        if idx >= 0:
            self.kind_combo.setCurrentIndex(idx)

    def _apply_kind_override(self) -> None:
        if self.current_doc is None:
            return
        row = self.region_list.currentRow()
        if row < 0 or row >= len(self.current_doc.regions):
            return
        reg = self.current_doc.regions[row]
        new_kind: RegionKind = self.kind_combo.currentData()
        self.review_uc.update_region_kind(
            self.current_doc, reg.id, new_kind, note="GUI manual review"
        )
        self.store.save(self.current_doc)
        self._refresh_view()

    def _undo_revision(self) -> None:
        if self.current_doc is None:
            return
        if self.review_uc.revert_last_revision(self.current_doc) is not None:
            self.store.save(self.current_doc)
            self._refresh_view()


def main() -> int:
    app = QApplication(sys.argv)
    win = PageReviewWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
