from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, verify_agent_secret
from app.db.models import Application, HiringOutcome

router = APIRouter()
logger = logging.getLogger(__name__)


class DetectBiasRequest(BaseModel):
    job_id: str
    all_scorecards: list[dict[str, Any]]


@router.post("/detect-bias")
async def detect_bias(
    body: DetectBiasRequest,
    _: bool = Depends(verify_agent_secret),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    logger.info(
        "detect-bias called: job_id=%s candidates=%s",
        body.job_id,
        len(body.all_scorecards),
    )

    scorecards = body.all_scorecards

    if len(scorecards) < 2:
        return {
            "bias_detected": False,
            "bias_flags": [],
            "note": "insufficient candidates for bias analysis",
        }

    bias_flags: list[dict[str, str]] = []

    try:
        result = await db.execute(
            select(Application, HiringOutcome)
            .join(
                HiringOutcome,
                HiringOutcome.application_id == Application.id,
                isouter=True,
            )
            .where(Application.job_id == int(body.job_id))
        )
        rows = result.fetchall()
        historical = {
            str(row.Application.candidate_id): row.HiringOutcome
            for row in rows
            if row.HiringOutcome is not None
        }
    except Exception:
        historical = {}

    try:
        overall_scores = [
            float(score)
            for card in scorecards
            for score in [card.get("overall_score")]
            if score is not None
        ]
        if len(overall_scores) >= 2:
            score_range = max(overall_scores) - min(overall_scores)
            if score_range > 3.0:
                bias_flags.append(
                    {
                        "flag_type": "score_variance",
                        "description": (
                            f"Score range of {score_range:.1f} points "
                            f"across candidates. Review whether gap "
                            f"is justified by evidence quality."
                        ),
                        "severity": "LOW",
                        "recommendation": (
                            "Compare evidence quality between top and bottom ranked candidates."
                        ),
                    }
                )
    except Exception:
        pass

    try:
        low_conf = [
            str(card.get("candidate_anon_id", "unknown"))
            for card in scorecards
            if card.get("low_confidence", False)
        ]
        if low_conf:
            bias_flags.append(
                {
                    "flag_type": "low_confidence_scoring",
                    "description": (
                        f"Candidates {low_conf} have low confidence "
                        f"scores due to sparse resume evidence."
                    ),
                    "severity": "MEDIUM",
                    "recommendation": (
                        "Request additional information or conduct screening call before ranking."
                    ),
                }
            )
    except Exception:
        pass

    try:
        if historical and scorecards:
            top = max(scorecards, key=lambda card: float(card.get("overall_score", 0) or 0))
            top_score = float(top.get("overall_score", 0) or 0)
            hist_scores = [
                float(outcome.performance_score)
                for outcome in historical.values()
                if outcome and outcome.performance_score is not None
            ]
            if hist_scores:
                hist_avg = sum(hist_scores) / len(hist_scores)
                if top_score < hist_avg - 1.5:
                    bias_flags.append(
                        {
                            "flag_type": "below_historical_baseline",
                            "description": (
                                f"Top candidate score {top_score:.1f} "
                                f"is below historical hire average "
                                f"{hist_avg:.1f}."
                            ),
                            "severity": "LOW",
                            "recommendation": (
                                "Consider whether job requirements "
                                "have changed since historical hires."
                            ),
                        }
                    )
    except Exception:
        pass

    return {
        "bias_detected": len(bias_flags) > 0,
        "bias_flags": bias_flags,
    }
