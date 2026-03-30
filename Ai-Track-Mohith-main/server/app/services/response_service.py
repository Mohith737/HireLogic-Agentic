from __future__ import annotations

from typing import Any


def assemble_scorecard(
    all_candidate_scores: list[dict[str, Any]],
    bias_flags: list[dict[str, Any]],
) -> dict[str, Any]:
    ranked = sorted(
        all_candidate_scores,
        key=lambda score: float(score.get("overall_score", 0)),
        reverse=True,
    )
    scorecard: dict[str, Any] = {}
    ranking: list[dict[str, Any]] = []
    for index, candidate in enumerate(ranked, 1):
        candidate["rank"] = index
        anon_id = str(
            candidate.get("anon_id") or candidate.get("candidate_anon_id") or f"candidate_{index}"
        )
        scorecard[anon_id] = {
            "competency_scores": candidate.get("competency_scores", {}),
            "overall_score": round(float(candidate.get("overall_score", 0)), 2),
            "rank": index,
            "interview_feedback_score": candidate.get("interview_feedback_score"),
            "application_status": candidate.get("application_status"),
            "low_confidence": candidate.get("low_confidence", False),
        }
        ranking.append(
            {
                "rank": index,
                "anon_id": anon_id,
                "overall_score": round(float(candidate.get("overall_score", 0)), 2),
            }
        )
    return {
        "scorecard": scorecard,
        "ranking": ranking,
        "bias_flags": bias_flags,
    }
