from __future__ import annotations

import json
import os
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, verify_agent_secret
from app.db.models import CompetencyFramework, Job

router = APIRouter()


class JobContextRequest(BaseModel):
    job_id: str
    weight_overrides: dict[str, float] = {}


def get_resource_overview(documents_path: str) -> dict[str, Any]:
    index_path = os.path.join(documents_path, "resource_index.json")
    with open(index_path, encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


async def _resolve_job(db: AsyncSession, raw_job_id: str) -> Job | None:
    raw = (raw_job_id or "").strip()
    if not raw:
        return None

    if raw.isdigit():
        result = await db.execute(select(Job).where(Job.id == int(raw)))
        return result.scalar_one_or_none()

    alias_map = {
        "job_senior_ml_engineer": "Senior ML Engineer",
        "job_backend_engineer": "Backend Software Engineer",
    }
    target_title = alias_map.get(raw, raw)
    result = await db.execute(select(Job).where(Job.title == target_title))
    return result.scalar_one_or_none()


@router.post("/job-context")
async def job_context(
    body: JobContextRequest,
    _: bool = Depends(verify_agent_secret),
    db: AsyncSession = Depends(db_session),
) -> dict[str, Any]:
    documents_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "documents")
    )
    try:
        resource_index = get_resource_overview(documents_path)
    except FileNotFoundError:
        resource_index = {}

    job = await _resolve_job(db, body.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {body.job_id} not found")

    cf_result = await db.execute(
        select(CompetencyFramework)
        .where(CompetencyFramework.job_id == job.id)
        .order_by(CompetencyFramework.created_at.desc())
    )
    cf = cf_result.scalar_one_or_none()

    framework: list[dict[str, Any]]
    if cf and cf.framework:
        raw_framework: Any = cf.framework
        if isinstance(raw_framework, str):
            raw_framework = json.loads(raw_framework)
        if isinstance(raw_framework, dict):
            raw_framework = raw_framework.get("competencies", [])
        if isinstance(raw_framework, list):
            framework = [
                cast(dict[str, Any], item) for item in raw_framework if isinstance(item, dict)
            ]
        else:
            framework = []
    else:
        framework = [
            {"name": "Python", "weight": 0.30, "description": "Python proficiency for ML"},
            {
                "name": "Machine Learning",
                "weight": 0.25,
                "description": "ML model development",
            },
            {
                "name": "System Design",
                "weight": 0.20,
                "description": "Distributed system design",
            },
            {"name": "Communication", "weight": 0.15, "description": "Team collaboration"},
            {"name": "Research", "weight": 0.10, "description": "Research contributions"},
        ]

    if body.weight_overrides:
        override_keys = {key.lower(): float(value) for key, value in body.weight_overrides.items()}
        for comp in framework:
            name_lower = str(comp.get("name", "")).lower()
            if name_lower in override_keys:
                comp["weight"] = override_keys[name_lower]

        total = sum(float(comp.get("weight", 0)) for comp in framework)
        if total > 0:
            for comp in framework:
                comp["weight"] = round(float(comp.get("weight", 0)) / total, 4)

    return {
        "job_id": str(job.id),
        "title": job.title,
        "description": job.description or "",
        "competency_framework": framework,
        "document_path": job.document_path or "",
        "resource_overview": resource_index,
    }
