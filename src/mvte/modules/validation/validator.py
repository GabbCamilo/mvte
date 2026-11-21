"""Global validation engine for OCR, translation, masks, and typography integrity."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mvte.domain.models.page import PageDocument
from mvte.domain.models.rendering import ReconstructionResult


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    code: str
    target_id: str
    severity: ValidationSeverity
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "target_id": self.target_id,
            "severity": self.severity.value,
            "message": self.message,
        }


@dataclass
class ValidationReport:
    document_id: str
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "passed": self.passed,
            "issues": [i.to_dict() for i in self.issues],
            "metrics": self.metrics,
        }


class PageValidationEngine:
    """Evaluates end-to-end quality and integrity of a processed PageDocument."""

    def validate(
        self,
        document: PageDocument,
        reconstruction: ReconstructionResult | None = None,
    ) -> ValidationReport:
        issues: list[ValidationIssue] = []

        # 1. Mask integrity checks
        for region in document.regions:
            if region.structure_mask is None or region.character_mask is None:
                issues.append(
                    ValidationIssue(
                        code="missing_masks",
                        target_id=region.id,
                        severity=ValidationSeverity.ERROR,
                        message="Region is missing structural or character mask.",
                    )
                )

        # 2. OCR & Translation checks
        total_sentences = 0
        ocr_review_count = 0
        translation_omissions = 0
        translation_review_count = 0

        for block in document.text_blocks:
            for sent in block.sentences:
                total_sentences += 1
                if sent.needs_review:
                    ocr_review_count += 1
                    issues.append(
                        ValidationIssue(
                            code="ocr_needs_review",
                            target_id=sent.id,
                            severity=ValidationSeverity.WARNING,
                            message="OCR flagged sentence for manual review.",
                        )
                    )
                if sent.text.strip() and not sent.translation.strip():
                    translation_omissions += 1
                    issues.append(
                        ValidationIssue(
                            code="translation_omission",
                            target_id=sent.id,
                            severity=ValidationSeverity.ERROR,
                            message="Source sentence has empty translation.",
                        )
                    )
                if sent.translation_needs_review:
                    translation_review_count += 1
                    issues.append(
                        ValidationIssue(
                            code="translation_needs_review",
                            target_id=sent.id,
                            severity=ValidationSeverity.WARNING,
                            message="Translation flagged for glossary/contextual review.",
                        )
                    )

        # 3. Typography overflow & overlap checks
        overflow_count = 0
        overlap_count = 0
        if reconstruction is not None:
            for plan in reconstruction.plans:
                if plan.needs_manual_review:
                    overflow_count += 1
                    issues.append(
                        ValidationIssue(
                            code="typography_overflow",
                            target_id=plan.region_id,
                            severity=ValidationSeverity.WARNING,
                            message=f"Typography requires manual review: {plan.overflow_reason}",
                        )
                    )
            for idx, p1 in enumerate(reconstruction.plans):
                for p2 in reconstruction.plans[idx + 1 :]:
                    if p1.usable_bbox.iou(p2.usable_bbox) > 0.15:
                        overlap_count += 1
                        issues.append(
                            ValidationIssue(
                                code="typography_overlap",
                                target_id=f"{p1.region_id}:{p2.region_id}",
                                severity=ValidationSeverity.WARNING,
                                message="Rendered text regions overlap significantly.",
                            )
                        )

        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)
        metrics = {
            "panels": len(document.panels),
            "regions": len(document.regions),
            "sentences": total_sentences,
            "ocr_review_count": ocr_review_count,
            "translation_omissions": translation_omissions,
            "translation_review_count": translation_review_count,
            "typography_overflow_count": overflow_count,
            "typography_overlap_count": overlap_count,
        }
        return ValidationReport(document_id=document.id, passed=not has_errors, issues=issues, metrics=metrics)
