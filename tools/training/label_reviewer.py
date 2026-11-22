"""Interactive PySide6 YOLO label reviewer & annotator for MVTE training batches."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

CLASS_SPECS = {
    0: ("speech_balloon", QColor(34, 197, 94), "1 - Balao (Verde): contorno do balao"),
    1: ("text_bubble", QColor(59, 130, 246), "2 - Texto no Balao (Azul): texto interno"),
    2: ("text_free", QColor(250, 204, 21), "3 - Texto Livre / SFX (Amarelo): fora de balao"),
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


@dataclass
class YoloBox:
    class_id: int
    x1: float
    y1: float
    x2: float
    y2: float


def load_yolo_boxes(label_path: Path, img_w: int, img_h: int) -> list[YoloBox]:
    if not label_path.exists() or img_w <= 0 or img_h <= 0:
        return []
    boxes: list[YoloBox] = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) != 5:
            continue
        cls_id = int(parts[0])
        cx, cy, w, h = (
            float(parts[1]) * img_w,
            float(parts[2]) * img_h,
            float(parts[3]) * img_w,
            float(parts[4]) * img_h,
        )
        boxes.append(YoloBox(cls_id, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
    return boxes


def save_yolo_boxes(label_path: Path, boxes: list[YoloBox], img_w: int, img_h: int) -> None:
    label_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for b in boxes:
        x1 = max(0.0, min(float(img_w), min(b.x1, b.x2)))
        x2 = max(0.0, min(float(img_w), max(b.x1, b.x2)))
        y1 = max(0.0, min(float(img_h), min(b.y1, b.y2)))
        y2 = max(0.0, min(float(img_h), max(b.y1, b.y2)))
        bw = x2 - x1
        bh = y2 - y1
        if bw < 3 or bh < 3:
            continue
        cx = (x1 + bw / 2.0) / float(img_w)
        cy = (y1 + bh / 2.0) / float(img_h)
        lines.append(f"{b.class_id} {cx:.6f} {cy:.6f} {bw / img_w:.6f} {bh / img_h:.6f}")
    label_path.write_text("\n".join(lines), encoding="utf-8")


class AnnotationCanvas(QWidget):
    """Image canvas supporting drag-to-draw boxes and click-to-select/delete."""

    def __init__(self, on_changed) -> None:
        super().__init__()
        self.on_changed = on_changed
        self.pixmap: QPixmap | None = None
        self.boxes: list[YoloBox] = []
        self.selected_idx: int = -1
        self.active_class: int = 2  # Default yellow text_free/SFX
        self._dragging = False
        self._drag_start = QPointF()
        self._drag_end = QPointF()
        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self.setMouseTracking(True)

    def set_image_and_boxes(self, pixmap: QPixmap, boxes: list[YoloBox]) -> None:
        self.pixmap = pixmap
        self.boxes = boxes
        self.selected_idx = -1
        self.update()

    def _compute_transform(self) -> None:
        if self.pixmap is None or self.pixmap.isNull():
            self._scale = 1.0
            self._offset_x = 0.0
            self._offset_y = 0.0
            return
        pw, ph = self.pixmap.width(), self.pixmap.height()
        ww, wh = max(1, self.width()), max(1, self.height())
        self._scale = min(ww / pw, wh / ph)
        self._offset_x = (ww - pw * self._scale) / 2.0
        self._offset_y = (wh - ph * self._scale) / 2.0

    def _to_img(self, pt: QPointF) -> QPointF:
        return QPointF(
            (pt.x() - self._offset_x) / self._scale,
            (pt.y() - self._offset_y) / self._scale,
        )

    def _to_widget(self, x: float, y: float) -> QPointF:
        return QPointF(x * self._scale + self._offset_x, y * self._scale + self._offset_y)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(24, 24, 27))
        if self.pixmap is None or self.pixmap.isNull():
            return
        self._compute_transform()
        target = QRectF(
            self._offset_x,
            self._offset_y,
            self.pixmap.width() * self._scale,
            self.pixmap.height() * self._scale,
        )
        painter.drawPixmap(target, self.pixmap, QRectF(self.pixmap.rect()))

        for idx, box in enumerate(self.boxes):
            name, color, _ = CLASS_SPECS.get(box.class_id, ("unknown", QColor(200, 200, 200), ""))
            p1 = self._to_widget(box.x1, box.y1)
            p2 = self._to_widget(box.x2, box.y2)
            rect = QRectF(p1, p2).normalized()

            fill = QColor(color)
            fill.setAlpha(45 if idx != self.selected_idx else 85)
            painter.fillRect(rect, fill)

            pen_color = QColor(255, 255, 255) if idx == self.selected_idx else color
            pen = QPen(pen_color, 3 if idx == self.selected_idx else 2)
            painter.setPen(pen)
            painter.drawRect(rect)
            painter.drawText(rect.topLeft() + QPointF(3, -4), f"[{box.class_id + 1}] {name}")

        if self._dragging:
            _, color, _ = CLASS_SPECS[self.active_class]
            painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
            painter.drawRect(QRectF(self._drag_start, self._drag_end).normalized())

    def mousePressEvent(self, event) -> None:
        if self.pixmap is None or event.button() != Qt.MouseButton.LeftButton:
            return
        self._dragging = True
        self._drag_start = event.position()
        self._drag_end = event.position()
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            self._drag_end = event.position()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if not self._dragging or event.button() != Qt.MouseButton.LeftButton or self.pixmap is None:
            return
        self._dragging = False
        p1 = self._to_img(self._drag_start)
        p2 = self._to_img(event.position())
        dx = abs(p2.x() - p1.x())
        dy = abs(p2.y() - p1.y())

        if dx < 6 and dy < 6:
            # Click: select existing box under cursor
            ix, iy = p2.x(), p2.y()
            self.selected_idx = -1
            for idx in range(len(self.boxes) - 1, -1, -1):
                b = self.boxes[idx]
                if b.x1 <= ix <= b.x2 and b.y1 <= iy <= b.y2:
                    self.selected_idx = idx
                    break
        else:
            pw, ph = float(self.pixmap.width()), float(self.pixmap.height())
            new_box = YoloBox(
                class_id=self.active_class,
                x1=max(0.0, min(pw, min(p1.x(), p2.x()))),
                y1=max(0.0, min(ph, min(p1.y(), p2.y()))),
                x2=max(0.0, min(pw, max(p1.x(), p2.x()))),
                y2=max(0.0, min(ph, max(p1.y(), p2.y()))),
            )
            self.boxes.append(new_box)
            self.selected_idx = len(self.boxes) - 1

        self.on_changed()
        self.update()


class LabelReviewerWindow(QMainWindow):
    """Main window for reviewing and correcting YOLO dataset labels."""

    def __init__(self, dataset_dir: Path, split: str = "train", start_index: int = 0) -> None:
        super().__init__()
        self.dataset_dir = dataset_dir
        self.split = split
        self.images: list[Path] = []
        self.index = start_index
        self.undo_stack: list[list[YoloBox]] = []

        self.setWindowTitle("MVTE — Revisor de Rótulos YOLO (1/2/3 + Mouse)")
        self.resize(1320, 860)
        self._build_ui()
        self._load_split(split, start_index=start_index)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        self.canvas = AnnotationCanvas(self._sync_list)
        layout.addWidget(self.canvas, stretch=4)

        side = QVBoxLayout()

        self.split_combo = QComboBox()
        self.split_combo.addItems(["train", "val"])
        self.split_combo.setCurrentText(self.split)
        self.split_combo.currentTextChanged.connect(self._load_split)
        side.addWidget(self.split_combo)

        self.status_label = QLabel("")
        side.addWidget(self.status_label)

        legend = QLabel(
            "<b>Classes (use teclas 1, 2 ou 3):</b><br>"
            "<span style='color:#22C55E'>■ [1] speech_balloon</span>: contorno do balão<br>"
            "<span style='color:#3B82F6'>■ [2] text_bubble</span>: texto dentro do balão<br>"
            "<span style='color:#FACC15'>■ [3] text_free</span>: SFX, texto livre e caixa escura<br><br>"
            "<b>Atalhos:</b> Arraste = nova caixa | Clique+Del = apagar | "
            "S = salvar | A/D = anterior/próxima"
        )
        legend.setWordWrap(True)
        side.addWidget(legend)

        self.class_combo = QComboBox()
        for cid, (_, _, desc) in CLASS_SPECS.items():
            self.class_combo.addItem(desc, cid)
        self.class_combo.setCurrentIndex(2)
        self.class_combo.currentIndexChanged.connect(self._on_class_combo)
        side.addWidget(self.class_combo)

        self.box_list = QListWidget()
        self.box_list.currentRowChanged.connect(self._on_list_selected)
        side.addWidget(self.box_list, stretch=1)

        del_btn = QPushButton("Apagar Selecionada (Del)")
        del_btn.clicked.connect(self._delete_selected)
        side.addWidget(del_btn)

        clear_btn = QPushButton("Limpar Todas da Página")
        clear_btn.clicked.connect(self._clear_all)
        side.addWidget(clear_btn)

        nav = QHBoxLayout()
        prev_btn = QPushButton("← Anterior (A)")
        prev_btn.clicked.connect(self._prev_image)
        next_btn = QPushButton("Salvar & Próxima (D) →")
        next_btn.clicked.connect(self._save_and_next)
        nav.addWidget(prev_btn)
        nav.addWidget(next_btn)
        side.addLayout(nav)

        layout.addLayout(side, stretch=1)

    def _load_split(self, split: str, start_index: int = 0) -> None:
        self.split = split
        img_dir = self.dataset_dir / "images" / split
        self.images = (
            sorted(p for p in img_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS)
            if img_dir.exists()
            else []
        )
        self.index = max(0, min(start_index, len(self.images) - 1)) if self.images else 0
        self._load_current()

    def _label_path_for(self, img_path: Path) -> Path:
        return self.dataset_dir / "labels" / self.split / f"{img_path.stem}.txt"

    def _load_current(self) -> None:
        if not self.images:
            self.status_label.setText("Nenhuma imagem encontrada.")
            return
        img_path = self.images[self.index]
        pix = QPixmap(str(img_path))
        boxes = load_yolo_boxes(self._label_path_for(img_path), pix.width(), pix.height())
        self.canvas.set_image_and_boxes(pix, boxes)
        self.status_label.setText(f"[{self.split}] {self.index + 1}/{len(self.images)} — {img_path.name}")
        self._sync_list()

    def _sync_list(self) -> None:
        self.box_list.blockSignals(True)
        self.box_list.clear()
        for idx, b in enumerate(self.canvas.boxes):
            name = CLASS_SPECS.get(b.class_id, ("?",))[0]
            self.box_list.addItem(f"#{idx} [{b.class_id + 1}] {name} ({int(b.x1)},{int(b.y1)})")
        if 0 <= self.canvas.selected_idx < len(self.canvas.boxes):
            self.box_list.setCurrentRow(self.canvas.selected_idx)
        self.box_list.blockSignals(False)

    def _on_list_selected(self, row: int) -> None:
        self.canvas.selected_idx = row
        self.canvas.update()

    def _on_class_combo(self) -> None:
        cid = int(self.class_combo.currentData())
        self.canvas.active_class = cid
        if 0 <= self.canvas.selected_idx < len(self.canvas.boxes):
            self.canvas.boxes[self.canvas.selected_idx].class_id = cid
            self._sync_list()
        self.canvas.update()

    def _set_class_by_key(self, cid: int) -> None:
        self.class_combo.setCurrentIndex(cid)
        self._on_class_combo()

    def _delete_selected(self) -> None:
        idx = self.canvas.selected_idx
        if 0 <= idx < len(self.canvas.boxes):
            self.canvas.boxes.pop(idx)
            self.canvas.selected_idx = -1
            self._sync_list()
            self.canvas.update()

    def _clear_all(self) -> None:
        self.canvas.boxes.clear()
        self.canvas.selected_idx = -1
        self._sync_list()
        self.canvas.update()

    def _save_current(self) -> None:
        if not self.images or self.canvas.pixmap is None:
            return
        img_path = self.images[self.index]
        save_yolo_boxes(
            self._label_path_for(img_path),
            self.canvas.boxes,
            self.canvas.pixmap.width(),
            self.canvas.pixmap.height(),
        )

    def _prev_image(self) -> None:
        if self.index > 0:
            self._save_current()
            self.index -= 1
            self._load_current()

    def _save_and_next(self) -> None:
        self._save_current()
        if self.index + 1 < len(self.images):
            self.index += 1
            self._load_current()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key.Key_1:
            self._set_class_by_key(0)
        elif key == Qt.Key.Key_2:
            self._set_class_by_key(1)
        elif key == Qt.Key.Key_3:
            self._set_class_by_key(2)
        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._delete_selected()
        elif key == Qt.Key.Key_S:
            self._save_current()
        elif key in (Qt.Key.Key_D, Qt.Key.Key_Right):
            self._save_and_next()
        elif key in (Qt.Key.Key_A, Qt.Key.Key_Left):
            self._prev_image()
        else:
            super().keyPressEvent(event)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MVTE Interactive YOLO Label Reviewer")
    parser.add_argument("--dataset-dir", type=Path, default=Path("datasets/custom"))
    parser.add_argument("--split", choices=["train", "val"], default="train")
    parser.add_argument("--start-index", type=int, default=0, help="0-based image index to start from")
    args = parser.parse_args(argv)

    app = QApplication(sys.argv)
    win = LabelReviewerWindow(args.dataset_dir, split=args.split, start_index=args.start_index)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
