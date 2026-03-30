from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, verify_agent_secret
from app.db.models import Application, Candidate, InterviewFeedback, Job

router = APIRouter()


class CandidateProfilesRequest(BaseModel):
    job_id: str


async def _resolve_job_id(db: AsyncSession, raw_job_id: str) -> int:
    raw = (raw_job_id or "").strip()
    if raw.isdigit():
        return int(raw)

    alias_map = {
        "job_senior_ml_engineer": "Senior ML Engineer",
        "job_backend_engineer": "Backend Software Engineer",
    }
    target_title = alias_map.get(raw, raw)
    job_result = await db.execute(select(Job).where(Job.title == target_title))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Invalid job_id: {raw_job_id}")
    return job.id


@router.post("/candidate-profiles")
async def candidate_profiles(
    body: CandidateProfilesRequest,
    _: bool = Depends(verify_agent_secret),
    db: AsyncSession = Depends(db_session),
) -> dict[str, object]:
    job_id_int = await _resolve_job_id(db, body.job_id)

    apps_result = await db.execute(
        select(Application).where(
            Application.job_id == job_id_int,
            Application.status.in_(["applied", "screening", "interview"]),
        )
    )
    applications = apps_result.scalars().all()

    if not applications:
        return {"candidates": []}

    candidates: list[dict[str, object]] = []
    for app in applications:
        cand_result = await db.execute(select(Candidate).where(Candidate.id == app.candidate_id))
        candidate = cand_result.scalar_one_or_none()
        if not candidate:
            continue

        feedback_result = await db.execute(
            select(InterviewFeedback).where(InterviewFeedback.application_id == app.id)
        )
        feedback = feedback_result.scalar_one_or_none()

        interview_feedback = None
        if feedback:
            interview_feedback = {
                "overall_score": feedback.overall_score,
                "feedback": feedback.feedback or {},
                "interviewer_notes": feedback.interviewer_notes or "",
            }

        doc_path = candidate.resume_path or ""
        sections = [
            "section_01_experience.md",
            "section_02_skills_projects.md",
            "section_03_education_certs.md",
        ]

        candidates.append(
            {
                "anon_id": candidate.anon_id,
                "document_path": doc_path,
                "sections": sections,
                "application_status": app.status or "applied",
                "interview_feedback": interview_feedback,
            }
        )

    return {"candidates": candidates}
