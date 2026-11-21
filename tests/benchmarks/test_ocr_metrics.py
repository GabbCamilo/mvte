"""OCR quality benchmarks (CER and WER) and real RapidOCR ONNX smoke check."""

from __future__ import annotations

import cv2
import numpy as np

from mvte.modules.ocr.backends import RapidOcrAdapter


def levenshtein_distance(seq_a: list[str] | str, seq_b: list[str] | str) -> int:
    m, n = len(seq_a), len(seq_b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            cost = 0 if seq_a[i - 1] == seq_b[j - 1] else 1
            prev, dp[j] = dp[j], min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
    return dp[n]


def compute_cer(reference: str, hypothesis: str) -> float:
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return levenshtein_distance(reference, hypothesis) / len(reference)


def compute_wer(reference: str, hypothesis: str) -> float:
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return levenshtein_distance(ref_words, hyp_words) / len(ref_words)


def test_cer_wer_and_rapidocr_onnx_inference() -> None:
    assert compute_cer("HELLO", "HELLO") == 0.0
    assert compute_wer("WAIT FOR ME", "WAIT FOR ME") == 0.0
    assert 0.0 < compute_cer("HELLO", "HELO") <= 0.25

    # Real ONNX inference with RapidOCR on a clean rendered balloon crop
    crop = np.full((120, 320, 3), 255, dtype=np.uint8)
    cv2.putText(crop, "HELLO WORLD", (35, 72), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 3)

    adapter = RapidOcrAdapter()
    try:
        lines = adapter.recognize(crop)
    finally:
        adapter.unload()

    recognized = " ".join(l.text for l in lines).upper()
    assert compute_cer("HELLO WORLD", recognized) <= 0.25
