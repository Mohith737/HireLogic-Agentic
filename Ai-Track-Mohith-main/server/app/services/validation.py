from __future__ import annotations

from typing import Any


def validate_resume_analysis(
    evidence: dict[str, str],
    source_sections: list[str],
    known_pii_patterns: list[str],
) -> dict[str, Any]:
    results: dict[str, Any] = {
        "grounding_pass": True,
        "pii_pass": True,
        "coverage": {},
        "low_confidence_fields": [],
    }
    for competency, quote in evidence.items():
        if not quote:
            results["coverage"][competency] = "empty"
            results["low_confidence_fields"].append(competency)
            continue
        found = any(quote[:50] in section for section in source_sections if section)
        if not found:
            results["grounding_pass"] = False
        for pattern in known_pii_patterns:
            if pattern and pattern.lower() in quote.lower():
                results["pii_pass"] = False
    return results


def compress_evidence(
    evidence_by_competency: dict[str, str],
    max_tokens_per_competency: int = 200,
) -> dict[str, str]:
    compressed: dict[str, str] = {}
    for competency, text in evidence_by_competency.items():
        words = text.split()
        if len(words) > max_tokens_per_competency:
            truncated = " ".join(words[:max_tokens_per_competency])
            last_period = truncated.rfind(".")
            if last_period > max_tokens_per_competency * 3:
                truncated = truncated[: last_period + 1]
            compressed[competency] = truncated + "..."
        else:
            compressed[competency] = text
    return compressed
