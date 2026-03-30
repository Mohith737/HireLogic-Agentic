from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.routes import agent, auth, health, hirelogic
from app.api.routes.internal import (
    candidate_profiles,
    detect_bias,
    finalize_response,
    job_context,
    resume_analysis,
    score_candidates,
)
from app.auth.deps import require_user

public_router = APIRouter()
public_router.include_router(health.router)
public_router.include_router(auth.router)

api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_user)])
api_router.include_router(agent.router)
api_router.include_router(hirelogic.router)

internal_router = APIRouter(prefix="/internal/hirelogic")
internal_router.include_router(job_context.router)
internal_router.include_router(candidate_profiles.router)
internal_router.include_router(resume_analysis.router)
internal_router.include_router(score_candidates.router)
internal_router.include_router(detect_bias.router)
internal_router.include_router(finalize_response.router)

root_router = APIRouter()
root_router.include_router(public_router)
root_router.include_router(api_router)
root_router.include_router(internal_router)
