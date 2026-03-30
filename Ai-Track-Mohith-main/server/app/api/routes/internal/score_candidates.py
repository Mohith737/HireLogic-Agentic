from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, verify_agent_secret
from app.db.models import Application, Candidate, HiringOutcome

router = APIRouter()


class ScoreCandidatesRequest(BaseModel):
    job_id: str
    candidate_anon_id: str
    evidence_by_competency: dict[str, Any] = {}
    competency_framework: list[dict[str, Any]] = []
    interview_feedback: Any = None
    blend_ratio: list[float] = [0.6, 0.4]


def _score_from_evidence(evidence: str, competency_name: str) -> float:
    if not evidence or len(str(evidence).strip()) < 10:
        return 2.0
    text = str(evidence)
    length = len(text)
    has_metric = any(char.isdigit() for char in text)
    has_scale = any(
        word in text.lower()
        for word in [
            "million",
            "thousand",
            "users",
            "requests",
            "latency",
            "accuracy",
            "production",
            "deployed",
            "scale",
            "reduced",
            "improved",
            "led",
            "built",
            "published",
            "expert",
            "strong",
            "senior",
        ]
    )
    if length < 80:
        base = 3.5
    elif length < 160:
        base = 5.0
    elif length < 300:
        base = 6.5
    else:
        base = 7.5
    if has_metric:
        base += 0.75
    if has_scale:
        base += 0.75
    return round(min(base, 9.5), 2)


@router.post("/score-candidates")
async def score_candidates(
    body: ScoreCandidatesRequest,
    _: bool = Depends(verify_agent_secret),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    try:
        job_id_int = int(body.job_id)
    except (ValueError, TypeError):
        job_id_map = {
            "job_senior_ml_engineer": 1,
            "job_backend_engineer": 2,
        }
        job_id_int = job_id_map.get(body.job_id, 1)

    historical_score = None
    try:
        cand_result = await db.execute(
            select(Candidate).where(Candidate.anon_id == body.candidate_anon_id)
        )
        candidate = cand_result.scalar_one_or_none()
        if candidate:
            app_result = await db.execute(
                select(Application).where(
                    Application.candidate_id == candidate.id,
                    Application.job_id == job_id_int,
                )
            )
            app = app_result.scalar_one_or_none()
            if app:
                outcome_result = await db.execute(
                    select(HiringOutcome).where(HiringOutcome.application_id == app.id)
                )
                outcome = outcome_result.scalar_one_or_none()
                if outcome and outcome.performance_score:
                    historical_score = float(outcome.performance_score)
    except Exception:
        pass

    competency_scores: dict[str, Any] = {}
    weighted_total = 0.0
    total_weight = 0.0

    framework = body.competency_framework
    if not framework:
        framework = (
            [
                {"name": key, "weight": 1.0 / len(body.evidence_by_competency)}
                for key in body.evidence_by_competency
            ]
            if body.evidence_by_competency
            else []
        )

    for comp in framework:
        name = comp.get("name", "")
        weight = float(comp.get("weight", 0.1))
        evidence = str(body.evidence_by_competency.get(name, ""))

        resume_score = _score_from_evidence(evidence, name)

        interview_used = False
        final_score = resume_score

        if body.interview_feedback and isinstance(body.interview_feedback, dict):
            feedback_scores = body.interview_feedback.get("feedback", {})
            if isinstance(feedback_scores, dict):
                interview_score = feedback_scores.get(name)
                if interview_score is not None:
                    try:
                        interview_score = float(interview_score)
                        ratio = body.blend_ratio
                        weight_resume = ratio[0] if len(ratio) > 0 else 0.6
                        weight_interview = ratio[1] if len(ratio) > 1 else 0.4
                        final_score = round(
                            weight_resume * resume_score + weight_interview * interview_score,
                            2,
                        )
                        interview_used = True
                    except (TypeError, ValueError):
                        pass

        if historical_score and not interview_used:
            final_score = round(0.85 * final_score + 0.15 * historical_score, 2)

        competency_scores[name] = {
            "score": final_score,
            "weight": weight,
            "evidence": evidence,
            "explanation": (
                f"Score reflects "
                f"{'strong' if final_score >= 7 else 'moderate' if final_score >= 5 else 'limited'}"
                f" evidence for {name.lower()}."
            ),
            "interview_feedback_used": interview_used,
        }

        weighted_total += final_score * weight
        total_weight += weight

    overall = round(weighted_total / total_weight if total_weight > 0 else 0.0, 2)

    evidence_lengths = [
        len(str(body.evidence_by_competency.get(comp.get("name", ""), ""))) for comp in framework
    ]
    avg_evidence_len = sum(evidence_lengths) / len(evidence_lengths) if evidence_lengths else 0
    low_confidence = avg_evidence_len < 50

    interview_overall = None
    if body.interview_feedback and isinstance(body.interview_feedback, dict):
        interview_overall = body.interview_feedback.get("overall_score")

    return {
        "candidate_anon_id": body.candidate_anon_id,
        "overall_score": overall,
        "competency_scores": competency_scores,
        "low_confidence": low_confidence,
        "interview_feedback_score": interview_overall,
        "application_status": None,
    }
