"""Translation quality benchmarks: omission rate and glossary consistency."""

from __future__ import annotations

from mvte.domain.models.linguistic import Sentence


def compute_omission_rate(sentences: list[Sentence]) -> float:
    non_empty_src = [s for s in sentences if s.text.strip()]
    if not non_empty_src:
        return 0.0
    omitted = sum(1 for s in non_empty_src if not s.translation.strip())
    return omitted / len(non_empty_src)


def test_translation_omission_rate_metric() -> None:
    sentences = [
        Sentence(id="1", text="Hello", translation="Olá"),
        Sentence(id="2", text="Run!", translation="Corra!"),
        Sentence(id="3", text="Wait", translation=""),
    ]
    assert compute_omission_rate(sentences[:2]) == 0.0
    assert abs(compute_omission_rate(sentences) - (1 / 3)) < 1e-6
